import os
from dataclasses import dataclass


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
VALID_ANALYSIS_MODES = {"mock", "gemini"}
VALID_BOOL_VALUES = {"true", "false"}

# In-memory cache + privacy safe defaults. These are operational knobs only;
# no database, Redis, or persistent storage is introduced.
DEFAULT_CACHE_ENABLED = True
DEFAULT_CACHE_TTL_SECONDS = 900
DEFAULT_CACHE_MAX_ENTRIES = 50
DEFAULT_MAX_IMAGE_MB = 8


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
    )


def get_effective_analysis_mode(settings: Settings) -> str:
    return settings.analysis_mode
