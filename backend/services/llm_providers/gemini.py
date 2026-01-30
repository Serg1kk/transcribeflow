# services/llm_providers/gemini.py
"""Google Gemini API client."""
import asyncio
import logging
import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    TIMEOUT = 900.0  # 15 minutes for very long transcripts (93K+ tokens)
    MAX_RETRIES = 2

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to Gemini API with retry logic."""
        url = f"{self.BASE_URL}/models/{model}:generateContent"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "maxOutputTokens": 100000,  # Required for full output, default ~8K cuts response
            }
        }

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        params={"key": self.api_key},
                        json=payload,
                        timeout=self.TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()

                # Extract response text
                text = data["candidates"][0]["content"]["parts"][0]["text"]

                # Extract token counts
                usage = data.get("usageMetadata", {})
                input_tokens = usage.get("promptTokenCount", 0)
                output_tokens = usage.get("candidatesTokenCount", 0)

                return LLMResponse(
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    wait_time = (attempt + 1) * 5  # 5s, 10s
                    logger.warning(f"Gemini timeout (attempt {attempt + 1}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Gemini failed after {self.MAX_RETRIES + 1} attempts")
                    raise

        raise last_error  # Should not reach here
