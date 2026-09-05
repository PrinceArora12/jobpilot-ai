"""
AI provider abstraction — spec section 43/71. Every place in JobPilot AI
that needs language generation goes through this interface, never a
provider SDK directly, so AI_PROVIDER can be swapped via environment
variable alone. Deterministic logic (matching math, eligibility, dedup)
never lives behind this interface — only genuinely generative steps do
(explanations, application-question answers, resume tailoring copy).
"""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, prompt: str, *, max_tokens: int = 300) -> str:
        """Returns generated text for the given prompt. Implementations must
        never be called for content that can be produced deterministically —
        see app/services/match_scorer.py and app/services/eligibility.py."""
        raise NotImplementedError
