"""Anthropic Claude 어댑터."""
from app.services.llm.base import LLMClient, LLMResult


class AnthropicClient(LLMClient):
    async def ping(self) -> str:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=2,
            messages=[{"role": "user", "content": "pong"}],
        )
        return resp.content[0].text if resp.content else ""

    async def complete(self, system: str, user: str, *, temperature: float = 0.4, max_tokens: int = 4096) -> LLMResult:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        usage = resp.usage
        return LLMResult(
            text=text,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )
