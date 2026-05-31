import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anyio
import pytest

from app.services.analysis_cache import analysis_cache
from app.services.metrics import metrics


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    # The analysis cache and metrics service are process-local singletons.
    # Reset them before each test so cache hits and counters never leak
    # between tests.
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
    yield
    anyio.run(analysis_cache.clear)
    anyio.run(metrics.reset)
