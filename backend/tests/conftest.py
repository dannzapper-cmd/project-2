import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anyio
import pytest

from app.services.analysis_cache import analysis_cache
from app.services.metrics import metrics


os.environ.setdefault("SNAPINSIGHT_LLMOPS_ENABLED", "false")


@pytest.fixture(autouse=True)
def reset_in_memory_state(monkeypatch):
    # The analysis cache and metrics service are process-local singletons.
    # Reset them before each test so cache hits and counters never leak
    # between tests.
    monkeypatch.setenv("SNAPINSIGHT_LLMOPS_ENABLED", "false")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    from app.services.llmops import llmops

    llmops.refresh_from_env()
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
    yield
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
    llmops.refresh_from_env()
