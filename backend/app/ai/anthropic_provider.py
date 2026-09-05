"""
Anthropic provider — used only when AI_PROVIDER=anthropic and AI_API_KEY is
set. Calls the Messages API directly over httpx, same rationale as
app/ai/openai_provider.py.
"""
import httpx

from app.ai.base import AIProvider

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, *, max_tokens: int = 300) -> str:
        if not self.api_key:
            raise RuntimeError("AI_PROVIDER=anthropic but AI_API_KEY is not set.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_MESSAGES_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
        return "".join(block.get("text", "") for block in data.get("content", [])).strip()
