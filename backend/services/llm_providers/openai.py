"""Direct OpenAI Responses API client (no OpenRouter dependency)."""
import asyncio
import logging
import re
from typing import Optional

import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse
from services.llm_providers.response_schemas import RESPONSE_SCHEMAS

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """Generate JSON for Cleanup, speaker identification and Insights."""

    BASE_URL = "https://api.openai.com/v1"
    TIMEOUT = 600.0  # Long transcripts and reasoning models can take minutes.
    MAX_RETRIES = 2
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
        reasoning_effort: Optional[str] = None,
        task: str = "cleanup",
    ) -> LLMResponse:
        if task not in RESPONSE_SCHEMAS:
            raise ValueError(f"Unknown OpenAI task: {task}")
        payload = {
            "model": model,
            "instructions": system_prompt + "\nReturn only a JSON object.",
            "input": user_message,
            # JSON mode (json_object) rejects transcripts without the word
            # "json" in input even when instructions already require JSON.
            # Strict task schemas avoid that fragile input requirement.
            "text": {"format": {
                "type": "json_schema", "name": f"transcribeflow_{task}",
                "strict": True, "schema": RESPONSE_SCHEMAS[task],
            }},
            "store": False,
        }
        if reasoning_effort not in (None, "default"):
            if reasoning_effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
                raise ValueError("Invalid OpenAI reasoning effort")
            if reasoning_effort == "none" and model.startswith(("gpt-6-astra", "gpt-6.1-sol")):
                raise ValueError(f"{model} does not support reasoning=none; select low or default")
            payload["reasoning"] = {"effort": reasoning_effort}
        # Reasoning models reject custom temperature. Keep template temperatures
        # for older, non-reasoning models added to the editable model catalog.
        if not model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")):
            payload["temperature"] = temperature

        async with httpx.AsyncClient() as client:
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        f"{self.BASE_URL}/responses",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                        timeout=self.TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.HTTPStatusError as exc:
                    if (exc.response.status_code not in self.RETRYABLE_STATUS_CODES
                            or attempt == self.MAX_RETRIES):
                        raise ValueError(self._format_api_error(exc.response)) from None
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == self.MAX_RETRIES:
                        raise
                logger.warning("OpenAI transient failure; retry %s/%s", attempt + 1, self.MAX_RETRIES)
                await asyncio.sleep(2 ** attempt)

        if data.get("status") != "completed":
            reason = (data.get("incomplete_details") or {}).get("reason", "unknown")
            raise ValueError(f"OpenAI response not completed ({reason})")

        # Reasoning items may precede the assistant message. Never assume the
        # first output item is text, and never save an incomplete/refused result.
        parts = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ValueError("OpenAI declined to process this transcript")
                if content.get("type") == "output_text":
                    parts.append(content["text"])
        if not parts or not "".join(parts).strip():
            raise ValueError("OpenAI returned no text")

        usage = data.get("usage") or {}
        return LLMResponse(
            text="".join(parts),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

    def _format_api_error(self, response: httpx.Response) -> str:
        """Expose the provider's useful error without leaking the API key."""
        try:
            error = response.json().get("error") or {}
            message = str(error.get("message") or response.reason_phrase)
            param = error.get("param")
        except (ValueError, AttributeError):
            message, param = response.reason_phrase, None
        if self.api_key:
            message = message.replace(self.api_key, "[REDACTED]")
        message = re.sub(r"sk-[A-Za-z0-9_*-]{6,}", "[REDACTED]", message)
        location = f" ({param})" if param else ""
        return f"OpenAI API {response.status_code}{location}: {message[:1000]}"
