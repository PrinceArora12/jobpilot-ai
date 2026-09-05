"""
Proves the Celery task skeleton (Phase 7) actually wires up and can run
synchronously ("eager mode") without a live worker process — `.apply()`
always executes a Celery task inline regardless of task_always_eager,
which is exactly the property that makes this testable at all. The task's
own DB/Redis setup is swapped out here so the test never touches the real
Postgres/Redis the task would use in production.
"""
import contextlib

from app.services.rapid_apply_service import CycleResult, DetectionResult
from app.worker import tasks


async def _fake_run_cycle(db, redis_client):
    return CycleResult(
        detection=DetectionResult(
            jobs_detected=2, evaluations=3, queued=1, skipped_ineligible=1, skipped_low_score=1, already_queued=0
        ),
        processed=1,
        completed=1,
        failed=0,
    )


@contextlib.asynccontextmanager
async def _fake_session_local():
    yield None


def test_run_rapid_apply_cycle_task_runs_synchronously_and_returns_summary(monkeypatch):
    monkeypatch.setattr(tasks, "AsyncSessionLocal", _fake_session_local)
    monkeypatch.setattr(tasks.rapid_apply_service, "run_cycle", _fake_run_cycle)
    monkeypatch.setattr(tasks, "get_redis", lambda: None)

    async_result = tasks.run_rapid_apply_cycle.apply()
    result = async_result.get()

    assert result == {
        "jobs_detected": 2,
        "evaluations": 3,
        "queued": 1,
        "skipped_ineligible": 1,
        "skipped_low_score": 1,
        "processed": 1,
        "completed": 1,
        "failed": 0,
    }
    assert async_result.successful()


def test_task_is_registered_under_expected_name():
    assert tasks.run_rapid_apply_cycle.name == "rapid_apply.run_cycle"
