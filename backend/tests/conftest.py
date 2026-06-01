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
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGIN_REGEX", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_GEMINI_LIVE_MODEL", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_ACCESS_CODE", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_AUDIO_ENABLED", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_VISION_ENABLED", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_LIVE_SYSTEM_INSTRUCTION", raising=False)
    from app.services.llmops import llmops
    from app.services.gemini_live import live_guardrail

    llmops.refresh_from_env()
    anyio.run(live_guardrail.reset)
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
    yield
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
    anyio.run(live_guardrail.reset)
    llmops.refresh_from_env()
