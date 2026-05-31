import asyncio
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass

from app.schemas import AnalyzeImageResponse


# Bump when the cached response shape or analysis contract changes so stale
# entries from an older deployment are never served.
CACHE_KEY_VERSION = "v1"


def compute_cache_key(
    image_bytes: bytes,
    *,
    analysis_mode: str,
    model_version: str,
) -> str:
    # Privacy: image bytes are hashed for cache keys but never logged or
    # persisted. The digest is one-way; raw bytes cannot be recovered from it.
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(b"|")
    digest.update(analysis_mode.encode("utf-8"))
    digest.update(b"|")
    digest.update(model_version.encode("utf-8"))
    digest.update(b"|")
    digest.update(CACHE_KEY_VERSION.encode("utf-8"))
    return digest.hexdigest()


@dataclass
class _CacheEntry:
    # Stores the analysis response object only. No image bytes, no base64.
    value: AnalyzeImageResponse
    expires_at: float


class AnalysisCache:
    # asyncio.Lock required: FastAPI async tasks can interleave.
    # GIL does not protect asyncio coroutines.
    def __init__(self) -> None:
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> AnalyzeImageResponse | None:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                # TTL expired: drop and treat as a miss.
                del self._cache[key]
                return None
            # LRU eviction: most recently accessed entries survive.
            # Favors repeated analysis of recently seen products.
            self._cache.move_to_end(key)
            # Return a copy so the caller can set a fresh request_id / latency
            # without mutating the cached object.
            return entry.value.model_copy(deep=True)

    async def set(
        self,
        key: str,
        value: AnalyzeImageResponse,
        *,
        ttl_seconds: int,
        max_entries: int,
    ) -> None:
        async with self._lock:
            expires_at = time.monotonic() + ttl_seconds
            # Deep copy on store so later mutation of the returned response
            # cannot leak back into the cache.
            self._cache[key] = _CacheEntry(
                value=value.model_copy(deep=True),
                expires_at=expires_at,
            )
            self._cache.move_to_end(key)
            # LRU eviction: most recently accessed entries survive.
            while len(self._cache) > max_entries:
                self._cache.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


# Process-local singleton. In-memory only: resets on backend restart and is not
# shared across multiple workers/instances. A shared cache (Redis/DB) is out of
# scope for this PR. Cache keys (image hashes) are never exposed to clients.
analysis_cache = AnalysisCache()
