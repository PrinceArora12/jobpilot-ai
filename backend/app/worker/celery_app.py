"""
Celery application — spec section 5 ("Celery workers"). Redis is both the
broker and result backend, matching docker-compose.yml.

`task_always_eager` is driven by settings.CELERY_TASK_ALWAYS_EAGER so the
test suite (and `python -m app.worker.tasks` one-off runs) can execute
tasks synchronously in-process without a running worker, exactly like the
AI provider defaults to "mock" — no extra infrastructure required to prove
the code path works.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "jobpilot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)

# Watcher cadence (spec section 57: "poll frequently"). Only takes effect
# when a celery beat process is actually running (docker-compose's
# `worker` + `beat` services) — harmless to define otherwise.
celery_app.conf.beat_schedule = {
    "rapid-apply-watch-cycle": {
        "task": "rapid_apply.run_cycle",
        "schedule": crontab(minute="*/1"),
    },
}
