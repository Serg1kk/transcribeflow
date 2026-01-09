# services/llm_providers/base.py
"""Base LLM provider client."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM API."""
    text: str
    input_tokens: int
    output_tokens: int


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to the LLM."""
        pass
