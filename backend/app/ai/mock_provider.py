"""
Mock AI provider — the default (AI_PROVIDER=mock). Returns the prompt back
through a clearly-labeled deterministic template rather than calling any
external API. This keeps local development, CI, and this project's own
tests free of network calls and API keys, and makes "never fabricate"
trivially auditable: nothing here can hallucinate because nothing here
calls a language model.
"""
from app.ai.base import AIProvider


class MockAIProvider(AIProvider):
    name = "mock"

    async def generate(self, prompt: str, *, max_tokens: int = 300) -> str:
        return prompt.strip()
