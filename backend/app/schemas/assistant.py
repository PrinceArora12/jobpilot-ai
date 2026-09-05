import uuid

from pydantic import BaseModel


class AssistantQuestionRequest(BaseModel):
    application_id: uuid.UUID
    question: str


class AssistantAnswerResponse(BaseModel):
    status: str  # "answered" | "needs_user_input"
    answer: str | None = None
    confidence: float | None = None
    source: str | None = None
    reason: str | None = None


class TailorPreviewRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID


class TailorPreviewResponse(BaseModel):
    original_order: list[str]
    suggested_order: list[str]
    matched_keywords: list[str]
    changed: bool


class TailorApplyRequest(BaseModel):
    resume_id: uuid.UUID
    skill_order: list[str]
