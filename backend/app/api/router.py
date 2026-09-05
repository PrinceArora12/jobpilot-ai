from fastapi import APIRouter

from app.api import (
    analytics,
    applications,
    assistant,
    audit,
    auth,
    automation,
    health,
    jobs,
    matches,
    mock_forms,
    mock_jobs,
    notifications,
    profile,
    rapid_apply,
    resumes,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(mock_jobs.router)
api_router.include_router(matches.router)
api_router.include_router(applications.router)
api_router.include_router(rapid_apply.router)
api_router.include_router(mock_forms.router)
api_router.include_router(assistant.router)
api_router.include_router(automation.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
