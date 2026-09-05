"""
OpenAI provider — used only when AI_PROVIDER=openai and AI_API_KEY is set.
Calls the Chat Completions API directly over httpx so this project has no
hard SDK dependency; swapping providers means adding a new small class
here, never touching a caller.
"""
import httpx

from app.ai.base import AIProvider
from app.core.config import settings

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, *, max_tokens: int = 300) -> str:
        if not self.api_key:
            raise RuntimeError("AI_PROVIDER=openai but AI_API_KEY is not set.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()
