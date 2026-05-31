import os
from dataclasses import dataclass


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
VALID_ANALYSIS_MODES = {"mock", "gemini"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    analysis_mode: str | None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def get_settings() -> Settings:
    raw_mode = _clean_optional(os.getenv("SNAPINSIGHT_ANALYSIS_MODE"))
    analysis_mode = raw_mode.lower() if raw_mode else None

    return Settings(
        gemini_api_key=_clean_optional(os.getenv("GEMINI_API_KEY")),
        gemini_model=_clean_optional(os.getenv("GEMINI_MODEL"))
        or DEFAULT_GEMINI_MODEL,
        analysis_mode=analysis_mode,
    )


def get_effective_analysis_mode(settings: Settings) -> str:
    if settings.analysis_mode in VALID_ANALYSIS_MODES:
        return settings.analysis_mode

    if settings.gemini_api_key:
        return "gemini"

    return "mock"
