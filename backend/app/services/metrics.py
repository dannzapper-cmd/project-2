import asyncio
import time

# Fixed counter names so the summary endpoint always reports a stable, complete
# set of operational counters (zeros included). These are operational metrics
# only: no user data, image data, prompts, chat messages, or product names.
COUNTER_NAMES: tuple[str, ...] = (
    "total_analysis_requests",
    "cache_hits",
    "cache_misses",
    "gemini_requests",
    "mock_requests",
    "mock_fallbacks",
    "analysis_errors",
    "grounding_grounded",
    "grounding_partial_match",
    "grounding_no_match",
    "grounding_unavailable",
    "chat_requests",
    "compare_requests",
)

GROUNDING_COUNTERS: dict[str, str] = {
    "grounded": "grounding_grounded",
    "partial_match": "grounding_partial_match",
    "no_match": "grounding_no_match",
    "grounding_unavailable": "grounding_unavailable",
}


class MetricsService:
    # asyncio.Lock required: FastAPI async tasks can interleave.
    # GIL does not protect asyncio coroutines.
    def __init__(self) -> None:
        self._counters: dict[str, int] = {name: 0 for name in COUNTER_NAMES}
        self._latency_sum_ms: int = 0
        self._latency_count: int = 0
        self._last_latency_ms: int | None = None
        self._started_at: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def increment(self, counter: str, amount: int = 1) -> None:
        async with self._lock:
            # Unknown counters are ignored to keep the contract stable.
            if counter in self._counters:
                self._counters[counter] += amount

    async def record_latency(self, latency_ms: int) -> None:
        async with self._lock:
            self._last_latency_ms = latency_ms
            self._latency_sum_ms += latency_ms
            self._latency_count += 1

    async def summary(self) -> dict:
        async with self._lock:
            average = (
                round(self._latency_sum_ms / self._latency_count)
                if self._latency_count
                else None
            )
            return {
                "counters": dict(self._counters),
                "last_latency_ms": self._last_latency_ms,
                "average_latency_ms": average,
                "uptime_seconds": int(time.monotonic() - self._started_at),
            }

    async def reset(self) -> None:
        # Test-only helper to isolate per-test process-local state.
        async with self._lock:
            self._counters = {name: 0 for name in COUNTER_NAMES}
            self._latency_sum_ms = 0
            self._latency_count = 0
            self._last_latency_ms = None
            self._started_at = time.monotonic()


# Process-local singleton. In-memory only: resets on backend restart and is not
# shared across multiple workers/instances. These are operational counters, not
# durable observability, and never hold product names, chat messages, prompts,
# image hashes, or other user-specific data.
metrics = MetricsService()
