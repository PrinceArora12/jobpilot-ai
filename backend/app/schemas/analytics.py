from pydantic import BaseModel, ConfigDict


class FunnelStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    count: int


class FunnelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_applications: int
    stages: list[FunnelStageRead]
    submitted_rate: float | None
    response_rate: float | None
    interview_rate: float | None
    offer_rate: float | None


class ResumePerformanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    label: str
    total_applications: int
    submitted: int
    responses: int
    interviews: int
    offers: int
    avg_match_score: float | None
    response_rate: float | None


class TimelinePointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    discovered: int
    submitted: int


class AnalyticsSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_applications: int
    total_submitted: int
    total_interviews: int
    total_offers: int
    avg_match_score: float | None
    avg_days_to_submit: float | None
