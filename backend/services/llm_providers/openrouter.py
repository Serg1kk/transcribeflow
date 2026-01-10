# services/llm_providers/openrouter.py
"""OpenRouter API client."""
import asyncio
import logging
import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


class OpenRouterClient(BaseLLMClient):
    """Client for OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"
    TIMEOUT = 300.0  # 5 minutes for long transcripts
    MAX_RETRIES = 2

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to OpenRouter API with retry logic."""
        url = f"{self.BASE_URL}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://transcribeflow.local",
            "X-Title": "TranscribeFlow",
        }

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=self.TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()

                # Extract response text
                text = data["choices"][0]["message"]["content"]

                # Extract token counts
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                return LLMResponse(
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    wait_time = (attempt + 1) * 5  # 5s, 10s
                    logger.warning(f"OpenRouter timeout (attempt {attempt + 1}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"OpenRouter failed after {self.MAX_RETRIES + 1} attempts")
                    raise

        raise last_error  # Should not reach here
