"""Direct Anthropic Messages API client with structured JSON outputs."""
import asyncio
import logging
from typing import Optional

import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse
from services.llm_providers.response_schemas import RESPONSE_SCHEMAS

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Claude for Cleanup, speaker identification, Insights and Mindmap."""

    BASE_URL = "https://api.anthropic.com/v1"
    TIMEOUT = 600.0
    MAX_RETRIES = 2
    MAX_TOKENS = 128000  # Includes both thinking and the JSON answer.
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504, 529}

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
            raise ValueError(f"Unknown Anthropic task: {task}")
        payload = {
            "model": model,
            "max_tokens": self.MAX_TOKENS,
            "system": system_prompt + "\nReturn only the requested JSON object.",
            "messages": [{"role": "user", "content": user_message}],
            "output_config": {"format": {"type": "json_schema", "schema": RESPONSE_SCHEMAS[task]}},
        }
        # Current Claude models use adaptive thinking and do not accept custom
        # sampling parameters. Effort, not template temperature, controls work.
        if reasoning_effort == "none":
            if not model.startswith("claude-haiku-5-5"):
                raise ValueError(f"{model} does not support disabling reasoning here; select low or default")
            payload["thinking"] = {"type": "disabled"}
        elif reasoning_effort not in (None, "default"):
            if reasoning_effort not in {"low", "medium", "high", "xhigh", "max"}:
                raise ValueError("Invalid Anthropic reasoning effort")
            payload["thinking"] = {"type": "adaptive"}
            payload["output_config"]["effort"] = reasoning_effort

        async with httpx.AsyncClient() as client:
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        f"{self.BASE_URL}/messages",
                        headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                        json=payload,
                        timeout=self.TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.HTTPStatusError as exc:
                    if (exc.response.status_code not in self.RETRYABLE_STATUS_CODES
                            or attempt == self.MAX_RETRIES):
                        raise
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == self.MAX_RETRIES:
                        raise
                logger.warning("Anthropic transient failure; retry %s/%s", attempt + 1, self.MAX_RETRIES)
                await asyncio.sleep(2 ** attempt)

        if data.get("stop_reason") != "end_turn":
            raise ValueError(f"Anthropic response not completed ({data.get('stop_reason', 'unknown')})")
        # Thinking and redacted-thinking blocks are never transcript content.
        text = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
        if not text.strip():
            raise ValueError("Anthropic returned no text")
        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
