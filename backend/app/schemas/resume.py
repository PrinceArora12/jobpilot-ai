import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    original_filename: str
    file_type: str
    is_primary: bool
    parsed_data: dict[str, Any] | None
    created_at: datetime


class ResumeUpdate(BaseModel):
    label: str | None = None
    is_primary: bool | None = None
    parsed_data: dict[str, Any] | None = None
