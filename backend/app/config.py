import os
from dataclasses import dataclass


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_LIVE_MODEL = "gemini-3.1-flash-live-preview"
DEFAULT_GEMINI_LIVE_SYSTEM_INSTRUCTION = (
    "You are SnapInsight's live product companion. Help the user understand "
    "visible packaged products from camera frames, microphone audio, and text. "
    "Be concise, cite uncertainty, avoid medical diagnosis, avoid absolute "
    "health claims, and remind users to verify the physical label."
)
VALID_ANALYSIS_MODES = {"mock", "gemini"}
VALID_BOOL_VALUES = {"true", "false"}

# In-memory cache + privacy safe defaults. These are operational knobs only;
# no database, Redis, or persistent storage is introduced.
DEFAULT_CACHE_ENABLED = True
DEFAULT_CACHE_TTL_SECONDS = 900
DEFAULT_CACHE_MAX_ENTRIES = 50
DEFAULT_MAX_IMAGE_MB = 8
DEFAULT_LIVE_MAX_SESSION_SECONDS = 120
DEFAULT_LIVE_MAX_FRAMES_PER_SECOND = 1


class ConfigurationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    analysis_mode: str
    mock_fallback_allowed: bool
    cache_enabled: bool
    cache_ttl_seconds: int
    cache_max_entries: int
    max_image_mb: int
    graph_enabled: bool
    neo4j_uri: str | None
    neo4j_username: str | None
    neo4j_password: str | None
    gemini_live_enabled: bool = False
    gemini_live_model: str = DEFAULT_GEMINI_LIVE_MODEL
    live_access_code: str | None = None
    live_max_session_seconds: int = DEFAULT_LIVE_MAX_SESSION_SECONDS
    live_max_frames_per_second: int = DEFAULT_LIVE_MAX_FRAMES_PER_SECOND
    live_audio_enabled: bool = True
    live_vision_enabled: bool = True
    live_system_instruction: str = DEFAULT_GEMINI_LIVE_SYSTEM_INSTRUCTION


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _parse_analysis_mode(value: str | None) -> str:
    # Default to mock so local development and CI do not require Gemini secrets.
    raw_mode = _clean_optional(value)
    if raw_mode is None:
        return "mock"

    analysis_mode = raw_mode.lower()
    if analysis_mode not in VALID_ANALYSIS_MODES:
        raise ConfigurationError(
            f"Invalid SNAPINSIGHT_ANALYSIS_MODE: {raw_mode}. "
            "Accepted: mock, gemini."
        )

    return analysis_mode


def _parse_bool_env(name: str, value: str | None, *, default: bool) -> bool:
    raw_value = _clean_optional(value)
    if raw_value is None:
        return default

    normalized = raw_value.lower()
    if normalized not in VALID_BOOL_VALUES:
        raise ConfigurationError(
            f"Invalid {name}: {raw_value}. Accepted: true, false."
        )

    return normalized == "true"


def _parse_positive_int_env(
    name: str, value: str | None, *, default: int, minimum: int = 1
) -> int:
    # Invalid or missing values fall back to the safe default so a malformed
    # env var can never disable analysis. Operational knob only.
    raw_value = _clean_optional(value)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError:
        return default

    return parsed if parsed >= minimum else default


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=_clean_optional(os.getenv("GEMINI_API_KEY")),
        gemini_model=_clean_optional(os.getenv("GEMINI_MODEL"))
        or DEFAULT_GEMINI_MODEL,
        analysis_mode=_parse_analysis_mode(
            os.getenv("SNAPINSIGHT_ANALYSIS_MODE")
        ),
        mock_fallback_allowed=_parse_bool_env(
            "SNAPINSIGHT_ALLOW_MOCK_FALLBACK",
            os.getenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK"),
            default=False,
        ),
        cache_enabled=_parse_bool_env(
            "SNAPINSIGHT_CACHE_ENABLED",
            os.getenv("SNAPINSIGHT_CACHE_ENABLED"),
            default=DEFAULT_CACHE_ENABLED,
        ),
        cache_ttl_seconds=_parse_positive_int_env(
            "SNAPINSIGHT_CACHE_TTL_SECONDS",
            os.getenv("SNAPINSIGHT_CACHE_TTL_SECONDS"),
            default=DEFAULT_CACHE_TTL_SECONDS,
        ),
        cache_max_entries=_parse_positive_int_env(
            "SNAPINSIGHT_CACHE_MAX_ENTRIES",
            os.getenv("SNAPINSIGHT_CACHE_MAX_ENTRIES"),
            default=DEFAULT_CACHE_MAX_ENTRIES,
        ),
        max_image_mb=_parse_positive_int_env(
            "SNAPINSIGHT_MAX_IMAGE_MB",
            os.getenv("SNAPINSIGHT_MAX_IMAGE_MB"),
            default=DEFAULT_MAX_IMAGE_MB,
        ),
        graph_enabled=_parse_bool_env(
            "SNAPINSIGHT_GRAPH_ENABLED",
            os.getenv("SNAPINSIGHT_GRAPH_ENABLED"),
            default=True,
        ),
        neo4j_uri=_clean_optional(os.getenv("NEO4J_URI")),
        neo4j_username=_clean_optional(os.getenv("NEO4J_USERNAME")),
        neo4j_password=_clean_optional(os.getenv("NEO4J_PASSWORD")),
        gemini_live_enabled=_parse_bool_env(
            "SNAPINSIGHT_GEMINI_LIVE_ENABLED",
            os.getenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED"),
            default=False,
        ),
        gemini_live_model=_clean_optional(os.getenv("SNAPINSIGHT_GEMINI_LIVE_MODEL"))
        or DEFAULT_GEMINI_LIVE_MODEL,
        live_access_code=_clean_optional(os.getenv("SNAPINSIGHT_LIVE_ACCESS_CODE")),
        live_max_session_seconds=_parse_positive_int_env(
            "SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS",
            os.getenv("SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS"),
            default=DEFAULT_LIVE_MAX_SESSION_SECONDS,
        ),
        live_max_frames_per_second=_parse_positive_int_env(
            "SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND",
            os.getenv("SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND"),
            default=DEFAULT_LIVE_MAX_FRAMES_PER_SECOND,
        ),
        live_audio_enabled=_parse_bool_env(
            "SNAPINSIGHT_LIVE_AUDIO_ENABLED",
            os.getenv("SNAPINSIGHT_LIVE_AUDIO_ENABLED"),
            default=True,
        ),
        live_vision_enabled=_parse_bool_env(
            "SNAPINSIGHT_LIVE_VISION_ENABLED",
            os.getenv("SNAPINSIGHT_LIVE_VISION_ENABLED"),
            default=True,
        ),
        live_system_instruction=_clean_optional(
            os.getenv("SNAPINSIGHT_LIVE_SYSTEM_INSTRUCTION")
        )
        or DEFAULT_GEMINI_LIVE_SYSTEM_INSTRUCTION,
    )


def is_neo4j_configured(settings: Settings) -> bool:
    return bool(
        settings.graph_enabled
        and settings.neo4j_uri
        and settings.neo4j_username
        and settings.neo4j_password
    )


def get_effective_analysis_mode(settings: Settings) -> str:
    return settings.analysis_mode
