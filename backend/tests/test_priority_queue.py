"""Unit tests for the Redis-backed priority queue (Phase 7)."""
import uuid

import pytest

from app.core.redis_client import get_redis
from app.services.priority_queue import RedisPriorityQueue, score_to_priority


@pytest.mark.parametrize(
    "score,expected_priority",
    [(100, 0), (90, 0), (89, 1), (75, 1), (74, 2), (60, 2), (59, 3), (0, 3)],
)
def test_score_to_priority_buckets(score, expected_priority):
    assert score_to_priority(score) == expected_priority


@pytest.mark.asyncio
async def test_dequeue_drains_higher_priority_first():
    queue = RedisPriorityQueue(get_redis(), namespace=f"test-{uuid.uuid4()}")
    try:
        low_id, mid_id, high_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

        # Enqueue out of priority order to prove ordering is by priority,
        # not insertion time.
        await queue.enqueue(low_id, priority=3)
        await queue.enqueue(high_id, priority=0)
        await queue.enqueue(mid_id, priority=1)

        assert await queue.dequeue() == high_id
        assert await queue.dequeue() == mid_id
        assert await queue.dequeue() == low_id
        assert await queue.dequeue() is None
    finally:
        await queue.clear()


@pytest.mark.asyncio
async def test_queue_lengths_and_clear():
    queue = RedisPriorityQueue(get_redis(), namespace=f"test-{uuid.uuid4()}")
    try:
        await queue.enqueue(str(uuid.uuid4()), priority=0)
        await queue.enqueue(str(uuid.uuid4()), priority=0)
        await queue.enqueue(str(uuid.uuid4()), priority=2)

        lengths = await queue.queue_lengths()
        assert lengths[0] == 2
        assert lengths[2] == 1
        assert await queue.total_length() == 3

        await queue.clear()
        assert await queue.total_length() == 0
    finally:
        await queue.clear()


@pytest.mark.asyncio
async def test_priority_is_clamped_to_valid_range():
    queue = RedisPriorityQueue(get_redis(), namespace=f"test-{uuid.uuid4()}")
    try:
        entry_id = str(uuid.uuid4())
        await queue.enqueue(entry_id, priority=99)
        lengths = await queue.queue_lengths()
        assert lengths[3] == 1  # clamped down to P3
        assert await queue.dequeue() == entry_id
    finally:
        await queue.clear()
