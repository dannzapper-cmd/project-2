import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping


logger = logging.getLogger(__name__)

LANGFUSE_PROVIDER = "langfuse"
DISABLED_PROVIDER = "disabled"

SAFE_METADATA_KEYS = {
    "analysis_mode",
    "app_version",
    "average_latency_ms",
    "cache_hit",
    "chat_used",
    "citations_count",
    "citations_used_count",
    "compare_used",
    "diff_count",
    "edge_count",
    "environment",
    "error_type",
    "evidence_paths_count",
    "fallback_used",
    "fields_count",
    "graph_backend",
    "graph_enabled",
    "grounding_status",
    "has_product_context",
    "latency_ms",
    "live_configured",
    "live_enabled",
    "live_event",
    "message_count",
    "model_name",
    "node_count",
    "operation",
    "question_length",
    "requires_access_code",
    "route",
    "status",
    "status_code",
    "text_messages_count",
    "token_created",
    "warnings_count",
    "audio_enabled",
    "duration_seconds",
    "expires_in_seconds",
    "frames_sent_count",
    "max_frames_per_second",
    "max_session_seconds",
    "vision_enabled",
}

MAX_SAFE_STRING_LENGTH = 120


@dataclass(frozen=True)
class LLMOpsStatus:
    enabled: bool
    configured: bool
    provider: str
    environment: str | None

    def api_fields(self) -> dict[str, str | bool | None]:
        return {
            "llmops_enabled": self.enabled,
            "llmops_configured": self.configured,
            "llmops_provider": self.provider,
            "llmops_environment": self.environment,
        }


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _enabled_from_env() -> bool:
    return (_clean_optional(os.getenv("SNAPINSIGHT_LLMOPS_ENABLED")) or "").lower() == "true"


def _safe_string(value: str) -> str:
    return value[:MAX_SAFE_STRING_LENGTH]


def safe_metadata(metadata: Mapping[str, Any]) -> dict[str, str | int | float | bool | None]:
    """
    Keep Langfuse payloads intentionally small and allowlisted.

    Route code should already pass only aggregate, non-sensitive fields. This
    second gate prevents accidental prompt/media/secret metadata from leaving
    the process if future instrumentation is less careful.
    """
    safe: dict[str, str | int | float | bool | None] = {}
    for key, value in metadata.items():
        if key not in SAFE_METADATA_KEYS:
            continue
        if value is None or isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, int):
            safe[key] = value
        elif isinstance(value, float):
            safe[key] = round(value, 3)
        elif isinstance(value, str):
            safe[key] = _safe_string(value)
    return safe


class LLMOpsService:
    def __init__(self) -> None:
        self._client: Any | None = None
        self._status = LLMOpsStatus(
            enabled=False,
            configured=False,
            provider=DISABLED_PROVIDER,
            environment=None,
        )
        self.refresh_from_env()

    @property
    def status(self) -> LLMOpsStatus:
        return self._status

    def refresh_from_env(self) -> None:
        """
        Initialize once from environment/configuration.

        This method is intentionally side-effect limited to local SDK client
        construction. It performs no live Langfuse network validation.
        """
        enabled = _enabled_from_env()
        environment = _clean_optional(os.getenv("LANGFUSE_TRACING_ENVIRONMENT"))
        provider = LANGFUSE_PROVIDER if enabled else DISABLED_PROVIDER
        self._client = None

        if not enabled:
            self._status = LLMOpsStatus(
                enabled=False,
                configured=False,
                provider=DISABLED_PROVIDER,
                environment=environment,
            )
            return

        public_key = _clean_optional(os.getenv("LANGFUSE_PUBLIC_KEY"))
        secret_key = _clean_optional(os.getenv("LANGFUSE_SECRET_KEY"))
        base_url = _clean_optional(os.getenv("LANGFUSE_BASE_URL"))
        if not (public_key and secret_key and base_url):
            self._status = LLMOpsStatus(
                enabled=True,
                configured=False,
                provider=provider,
                environment=environment,
            )
            return

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=base_url,
            )
            configured = True
        except Exception as exc:  # noqa: BLE001
            configured = False
            self._client = None
            logger.warning(
                "Langfuse LLMOps disabled after local client initialization failed",
                extra={"error_type": exc.__class__.__name__},
            )

        self._status = LLMOpsStatus(
            enabled=True,
            configured=configured,
            provider=provider,
            environment=environment,
        )

    def trace_event(
        self,
        *,
        name: str,
        metadata: Mapping[str, Any],
    ) -> None:
        if self._client is None or not self._status.configured:
            return

        payload = safe_metadata(
            {
                **metadata,
                "environment": self._status.environment,
            }
        )
        try:
            trace_method = getattr(self._client, "trace", None)
            if callable(trace_method):
                trace = trace_method(name=name, metadata=payload)
                event_method = getattr(trace, "event", None)
                if callable(event_method):
                    event_method(name=name, metadata=payload)
                return

            event_method = getattr(self._client, "event", None)
            if callable(event_method):
                event_method(name=name, metadata=payload)
                return

            create_event_method = getattr(self._client, "create_event", None)
            if callable(create_event_method):
                create_event_method(name=name, metadata=payload)
        except Exception as exc:  # noqa: BLE001
            # Observability must never affect API request handling.
            logger.debug(
                "Langfuse event enqueue failed",
                extra={"error_type": exc.__class__.__name__},
            )

    def span(
        self,
        *,
        name: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.trace_event(name=name, metadata=metadata or {})

    @contextmanager
    def observe_context(
        self,
        *,
        name: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Iterator[None]:
        started_at = time.monotonic()
        try:
            yield
            status = "ok"
            error_type = None
        except Exception as exc:
            status = "error"
            error_type = exc.__class__.__name__
            raise
        finally:
            self.trace_event(
                name=name,
                metadata={
                    **(metadata or {}),
                    "status": status,
                    "error_type": error_type,
                    "latency_ms": int((time.monotonic() - started_at) * 1000),
                },
            )

    def shutdown(self) -> None:
        if self._client is None:
            return

        try:
            shutdown_method = getattr(self._client, "shutdown", None)
            if callable(shutdown_method):
                shutdown_method()
                return

            flush_method = getattr(self._client, "flush", None)
            if callable(flush_method):
                flush_method()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Langfuse shutdown/flush failed",
                extra={"error_type": exc.__class__.__name__},
            )


llmops = LLMOpsService()
