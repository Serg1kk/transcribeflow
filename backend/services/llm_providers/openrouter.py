# services/llm_providers/openrouter.py
"""OpenRouter API client."""
import httpx

from services.llm_providers.base import BaseLLMClient, LLMResponse


class OpenRouterClient(BaseLLMClient):
    """Client for OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to OpenRouter API."""
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

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=120.0,
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
