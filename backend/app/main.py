"""
JobPilot AI — FastAPI application entrypoint.

Phase 1 scope: app wiring, CORS, structured logging, health check, and the
auth router. Later phases add profile/resume/jobs/matches/applications/
automation/analytics routers into the same api_router without touching this
file's structure.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security_headers import SecurityHeadersMiddleware

configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

#: Secrets that must never reach a production deployment unchanged — spec
#: section 12's security pass. Development and the test suite both run
#: with APP_ENV="development" (or unset), so this only ever fires for a
#: deployment that's explicitly declared itself "production" while still
#: carrying the placeholder values from .env.example.
_DEV_DEFAULT_SECRETS = {"change-me-dev-secret-key", "change-me-dev-jwt-secret"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV == "production" and (
        settings.SECRET_KEY in _DEV_DEFAULT_SECRETS or settings.JWT_SECRET in _DEV_DEFAULT_SECRETS
    ):
        raise RuntimeError(
            "Refusing to start with APP_ENV=production while SECRET_KEY/JWT_SECRET still hold "
            "their development placeholder values. Set real secrets via the environment."
        )
    logger.info("app_startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time AI-powered job discovery, matching, rapid-application, "
    "and application-tracking platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware, hsts=settings.APP_ENV == "production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "status": "running", "docs": "/docs"}
