import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.automation import AUTOMATION_STATES


class AutomationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: str
    max_applications_per_hour: int | None
    max_applications_per_day: int | None
    max_applications_per_company: int | None
    blocked_sources: list[str]
    blocked_companies: list[str]
    blocked_keywords: list[str]


class AutomationRuleUpdate(BaseModel):
    max_applications_per_hour: int | None = None
    max_applications_per_day: int | None = None
    max_applications_per_company: int | None = None
    blocked_sources: list[str] | None = None
    blocked_companies: list[str] | None = None
    blocked_keywords: list[str] | None = None

    @field_validator("max_applications_per_hour", "max_applications_per_day", "max_applications_per_company")
    @classmethod
    def positive_or_none(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("limit must be at least 1 (use null for unlimited)")
        return v


class AutomationStateResponse(BaseModel):
    state: str

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: str) -> str:
        if v not in AUTOMATION_STATES:
            raise ValueError(f"state must be one of {AUTOMATION_STATES}")
        return v


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    application_id: uuid.UUID | None
    created_at: datetime
