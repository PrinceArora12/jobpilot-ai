from functools import lru_cache

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.config import settings


@lru_cache
def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER == "openai":
        return OpenAIProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
    if settings.AI_PROVIDER == "anthropic":
        return AnthropicProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
    return MockAIProvider()
