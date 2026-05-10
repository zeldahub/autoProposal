"""OpenAI ChatGPT 어댑터."""
from app.services.llm.base import LLMClient, LLMResult


class OpenAIClient(LLMClient):
    async def ping(self) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": "pong"}],
            max_tokens=2,
        )
        return resp.choices[0].message.content or ""

    async def complete(self, system: str, user: str, *, temperature: float = 0.4, max_tokens: int = 4096) -> LLMResult:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = resp.choices[0].message.content or ""
        usage = resp.usage
        return LLMResult(
            text=msg,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )
