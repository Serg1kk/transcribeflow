# services/llm_providers/gemini.py
"""Google Gemini API client."""
import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to Gemini API."""
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
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=120.0,
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
