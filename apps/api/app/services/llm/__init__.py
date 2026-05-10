from app.services.llm.base import LLMClient
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.anthropic_client import AnthropicClient


def get_client(provider: str, api_key: str, model: str) -> LLMClient:
    p = provider.upper()
    if p == "OPENAI":
        return OpenAIClient(api_key=api_key, model=model)
    if p == "GEMINI":
        return GeminiClient(api_key=api_key, model=model)
    if p == "ANTHROPIC":
        return AnthropicClient(api_key=api_key, model=model)
    raise ValueError(f"unknown provider: {provider}")


__all__ = ["LLMClient", "get_client"]
