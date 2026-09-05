import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.job import JobRead


class RapidApplyQueueEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job: JobRead
    match_score: int
    priority: int
    status: str
    failure_reason: str | None
    application_id: uuid.UUID | None

    source_posted_at: datetime | None
    first_seen_at: datetime | None
    detected_at: datetime | None
    normalized_at: datetime | None
    matched_at: datetime | None
    queued_at: datetime | None
    application_started_at: datetime | None
    application_completed_at: datetime | None
    created_at: datetime


class DetectionResultRead(BaseModel):
    jobs_detected: int
    evaluations: int
    queued: int
    skipped_ineligible: int
    skipped_low_score: int
    skipped_by_automation_rules: int
    already_queued: int


class CycleResultRead(BaseModel):
    detection: DetectionResultRead
    processed: int
    completed: int
    failed: int


class LatencyStatsRead(BaseModel):
    count: int
    avg_detection_to_match_seconds: float | None
    avg_match_to_queue_seconds: float | None
    avg_application_seconds: float | None
    avg_total_seconds: float | None
    fastest_total_seconds: float | None


class RapidApplyStatsRead(BaseModel):
    total_queued: int
    queued: int
    processing: int
    completed: int
    skipped: int
    failed: int
    queue_depth_by_priority: dict[int, int]
    latency: LatencyStatsRead


class RapidApplySettingsRead(BaseModel):
    rapid_apply_enabled: bool
    min_match_score_to_apply: int


class RapidApplySettingsUpdate(BaseModel):
    rapid_apply_enabled: bool | None = None
    min_match_score_to_apply: int | None = None
