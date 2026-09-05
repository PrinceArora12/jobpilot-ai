"""
Mock job board — spec section 56. Lets development/testing simulate a
company publishing a new job so the full discovery pipeline can be
exercised without touching any real job portal. Not authenticated: it
plays the role of an external system posting to a webhook, not a
JobPilot AI user action.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.mock_job_posting import MockJobPosting
from app.schemas.job import MockJobCreate, MockJobPostingRead

router = APIRouter(prefix="/mock/jobs", tags=["mock"])


@router.post("", response_model=MockJobPostingRead, status_code=201)
async def publish_mock_job(payload: MockJobCreate, db: AsyncSession = Depends(get_db)):
    posted_at = payload.posted_at or datetime.now(timezone.utc)
    body = payload.model_dump(exclude={"posted_at"})
    body["external_id"] = body.get("external_id") or str(uuid.uuid4())
    if not body.get("url"):
        body["url"] = f"https://mock.jobpilot.ai/jobs/{body['external_id']}"

    posting = MockJobPosting(payload=body, source_posted_at=posted_at)
    db.add(posting)
    await db.commit()
    await db.refresh(posting)
    return posting
