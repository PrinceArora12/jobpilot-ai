"""
Redis-backed priority queue for Rapid Apply — spec sections 57/58.

Four Redis lists, P0 (highest match score) through P3 (lowest), hold only
queue-entry UUIDs as strings. Redis is purely an ordering structure: the
`RapidApplyQueueEntry` row in Postgres (app/models/rapid_apply.py) is the
durable record, so a flushed/restarted Redis loses nothing except queue
*order* — `requeue_stale_entries` below can always rebuild it by scanning
for rows still in status="queued".

Kept as a small class (rather than free functions) so tests can point it
at a disposable namespace and `clear()` it between runs without touching
any other queue sharing the same Redis instance.
"""
from redis.asyncio import Redis

KEY_PREFIX = "jobpilot:rapid_apply:queue"
PRIORITY_LEVELS = (0, 1, 2, 3)  # P0 (highest) .. P3 (lowest)


def score_to_priority(match_score: int) -> int:
    """Bucket a 0-100 match score into a Rapid Apply priority (spec 57)."""
    if match_score >= 90:
        return 0  # P0
    if match_score >= 75:
        return 1  # P1
    if match_score >= 60:
        return 2  # P2
    return 3  # P3


class RedisPriorityQueue:
    def __init__(self, redis_client: Redis, namespace: str = "default"):
        self.redis = redis_client
        self.namespace = namespace

    def _key(self, priority: int) -> str:
        return f"{KEY_PREFIX}:{self.namespace}:p{priority}"

    async def enqueue(self, entry_id: str, priority: int) -> None:
        priority = max(0, min(3, priority))
        await self.redis.rpush(self._key(priority), entry_id)

    async def dequeue(self) -> str | None:
        """Pop the next entry id, always draining P0 fully before P1, etc."""
        for priority in PRIORITY_LEVELS:
            entry_id = await self.redis.lpop(self._key(priority))
            if entry_id is not None:
                return entry_id
        return None

    async def queue_lengths(self) -> dict[int, int]:
        return {p: await self.redis.llen(self._key(p)) for p in PRIORITY_LEVELS}

    async def total_length(self) -> int:
        lengths = await self.queue_lengths()
        return sum(lengths.values())

    async def clear(self) -> None:
        for p in PRIORITY_LEVELS:
            await self.redis.delete(self._key(p))
