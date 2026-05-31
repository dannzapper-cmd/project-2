import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.schemas import GeminiLiveConfigResponse, GeminiLiveTokenResponse


logger = logging.getLogger(__name__)

GEMINI_LIVE_PROVIDER = "gemini_live"
GEMINI_LIVE_WEBSOCKET_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1alpha.GenerativeService."
    "BidiGenerateContentConstrained"
)
NEW_SESSION_EXPIRE_SECONDS = 90
TOKEN_EXPIRY_BUFFER_SECONDS = 60
MAX_ACTIVE_LIVE_TOKENS = 3
TOKEN_COOLDOWN_SECONDS = 5


class GeminiLiveTokenError(Exception):
    def __init__(self, error_type: str) -> None:
        super().__init__(error_type)
        self.error_type = error_type


@dataclass(frozen=True)
class LiveStatus:
    enabled: bool
    configured: bool
    provider: str
    model: str

    def api_fields(self) -> dict[str, str | bool]:
        return {
            "gemini_live_enabled": self.enabled,
            "gemini_live_configured": self.configured,
            "gemini_live_provider": self.provider,
            "gemini_live_model": self.model,
        }


class LiveSessionGuardrail:
    """
    Small process-local cost guardrail.

    It tracks issued token windows, not durable users. This is intentionally
    in-memory only so Block 18E does not add auth, Redis, or a database.
    """

    def __init__(self) -> None:
        self._active_until: list[float] = []
        self._last_token_created_at: float | None = None
        self._lock = asyncio.Lock()

    async def reserve(self, *, active_seconds: int) -> bool:
        now = time.monotonic()
        async with self._lock:
            self._active_until = [
                expires_at for expires_at in self._active_until if expires_at > now
            ]
            if (
                self._last_token_created_at is not None
                and now - self._last_token_created_at < TOKEN_COOLDOWN_SECONDS
            ):
                return False
            if len(self._active_until) >= MAX_ACTIVE_LIVE_TOKENS:
                return False
            self._last_token_created_at = now
            self._active_until.append(now + active_seconds)
            return True

    async def reset(self) -> None:
        async with self._lock:
            self._active_until = []
            self._last_token_created_at = None


live_guardrail = LiveSessionGuardrail()


def get_live_status(settings: Settings) -> LiveStatus:
    return LiveStatus(
        enabled=settings.gemini_live_enabled,
        configured=bool(settings.gemini_live_enabled and settings.gemini_api_key),
        provider=GEMINI_LIVE_PROVIDER,
        model=settings.gemini_live_model,
    )


def build_live_config(settings: Settings) -> GeminiLiveConfigResponse:
    status = get_live_status(settings)
    if not status.enabled:
        state = "disabled"
    elif not status.configured:
        state = "not_configured"
    else:
        state = "ready"

    return GeminiLiveConfigResponse(
        enabled=status.enabled,
        configured=status.configured,
        provider=status.provider,
        model=settings.gemini_live_model,
        audio_enabled=settings.live_audio_enabled,
        vision_enabled=settings.live_vision_enabled,
        max_session_seconds=settings.live_max_session_seconds,
        max_frames_per_second=settings.live_max_frames_per_second,
        requires_access_code=bool(settings.live_access_code),
        status=state,
    )


def _base_token_response(
    *,
    settings: Settings,
    status: str,
    message: str | None = None,
    token: str | None = None,
    websocket_url: str | None = None,
    expires_in_seconds: int | None = None,
) -> GeminiLiveTokenResponse:
    live_status = get_live_status(settings)
    return GeminiLiveTokenResponse(
        status=status,  # type: ignore[arg-type]
        enabled=live_status.enabled,
        configured=live_status.configured,
        provider=live_status.provider,
        model=settings.gemini_live_model,
        token=token,
        websocket_url=websocket_url,
        expires_in_seconds=expires_in_seconds,
        audio_enabled=settings.live_audio_enabled,
        vision_enabled=settings.live_vision_enabled,
        max_session_seconds=settings.live_max_session_seconds,
        max_frames_per_second=settings.live_max_frames_per_second,
        requires_access_code=bool(settings.live_access_code),
        message=message,
    )


def disabled_token_response(settings: Settings) -> GeminiLiveTokenResponse:
    return _base_token_response(
        settings=settings,
        status="disabled",
        message="Gemini Live is disabled in this deployment configuration.",
    )


def not_configured_token_response(settings: Settings) -> GeminiLiveTokenResponse:
    return _base_token_response(
        settings=settings,
        status="not_configured",
        message="Gemini Live is enabled but GEMINI_API_KEY is not configured.",
    )


def access_denied_token_response(settings: Settings) -> GeminiLiveTokenResponse:
    return _base_token_response(
        settings=settings,
        status="access_denied",
        message="Valid Live access code is required.",
    )


def rate_limited_token_response(settings: Settings) -> GeminiLiveTokenResponse:
    return _base_token_response(
        settings=settings,
        status="rate_limited",
        message="Live session capacity is temporarily limited. Try again shortly.",
    )


def token_error_response(settings: Settings) -> GeminiLiveTokenResponse:
    return _base_token_response(
        settings=settings,
        status="token_error",
        message="Could not create a Gemini Live session token.",
    )


def access_code_matches(settings: Settings, provided: str | None) -> bool:
    if not settings.live_access_code:
        return True
    return provided == settings.live_access_code


def _create_auth_token_sync(settings: Settings):
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise GeminiLiveTokenError("google_genai_unavailable") from exc

    if not settings.gemini_api_key:
        raise GeminiLiveTokenError("missing_gemini_api_key")

    now = datetime.now(timezone.utc)
    new_session_expire_time = now + timedelta(seconds=NEW_SESSION_EXPIRE_SECONDS)
    expire_time = now + timedelta(
        seconds=settings.live_max_session_seconds + TOKEN_EXPIRY_BUFFER_SECONDS
    )

    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options={"api_version": "v1alpha"},
        )
        return client.auth_tokens.create(
            config=types.CreateAuthTokenConfig(
                http_options={"api_version": "v1alpha"},
                uses=1,
                new_session_expire_time=new_session_expire_time,
                expire_time=expire_time,
                live_connect_constraints=types.LiveConnectConstraints(
                    model=settings.gemini_live_model,
                    config=types.LiveConnectConfig(
                        response_modalities=["AUDIO"],
                        output_audio_transcription=types.AudioTranscriptionConfig(),
                        system_instruction=settings.live_system_instruction,
                    ),
                ),
            )
        )
    except GeminiLiveTokenError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GeminiLiveTokenError(exc.__class__.__name__) from exc


async def create_live_token(settings: Settings) -> GeminiLiveTokenResponse:
    token = await asyncio.to_thread(_create_auth_token_sync, settings)
    token_name = getattr(token, "name", None)
    if not isinstance(token_name, str) or not token_name:
        raise GeminiLiveTokenError("missing_token_name")

    return _base_token_response(
        settings=settings,
        status="ready",
        token=token_name,
        websocket_url=GEMINI_LIVE_WEBSOCKET_URL,
        expires_in_seconds=NEW_SESSION_EXPIRE_SECONDS,
    )
