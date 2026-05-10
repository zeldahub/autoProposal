"""LLMClient 추상 인터페이스."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    raw: dict


class LLMClient(ABC):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def ping(self) -> str:
        """1토큰 호출로 키 유효성 확인."""

    @abstractmethod
    async def complete(self, system: str, user: str, *, temperature: float = 0.4, max_tokens: int = 4096) -> LLMResult:
        ...
