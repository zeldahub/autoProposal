"""Google Gemini 어댑터 — httpx 직접 호출 (SDK 의존성 최소화)."""
import httpx

from app.services.llm.base import LLMClient, LLMResult

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiClient(LLMClient):
    async def ping(self) -> str:
        async with httpx.AsyncClient(timeout=20) as cli:
            resp = await cli.post(
                ENDPOINT.format(model=self.model),
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": "pong"}]}],
                    "generationConfig": {"maxOutputTokens": 2},
                },
            )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "pong"

    async def complete(self, system: str, user: str, *, temperature: float = 0.4, max_tokens: int = 4096) -> LLMResult:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        async with httpx.AsyncClient(timeout=60) as cli:
            resp = await cli.post(
                ENDPOINT.format(model=self.model),
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=body,
            )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            pass
        usage = data.get("usageMetadata", {})
        return LLMResult(
            text=text,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            raw=data,
        )
