import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Settings


# Conservative rough estimates for in-process guardrails only — not billing.
ESTIMATED_GEMINI_ANALYSIS_USD = 0.002
ESTIMATED_GEMINI_CHAT_USD = 0.0005

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
ANONYMOUS_SESSION_ID = "__anonymous__"


class UsageLimitError(Exception):
    def __init__(
        self,
        *,
        error: str,
        message: str,
        status_code: int = 429,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class UsageLimitSnapshot:
    storage: str
    session_analyses: int
    session_chats: int
    session_compares: int
    daily_analyses: int
    daily_estimated_cost_usd: float
    max_analyses_per_session: int
    max_chat_messages_per_session: int
    max_compare_per_session: int
    daily_analysis_limit: int
    daily_cost_limit_usd: float

    def api_fields(self) -> dict[str, str | int | float]:
        return {
            "usage_limits_storage": self.storage,
            "usage_limits_session_analyses": self.session_analyses,
            "usage_limits_session_chats": self.session_chats,
            "usage_limits_session_compares": self.session_compares,
            "usage_limits_daily_analyses": self.daily_analyses,
            "usage_limits_daily_estimated_cost_usd": round(
                self.daily_estimated_cost_usd, 6
            ),
            "usage_limits_max_analyses_per_session": self.max_analyses_per_session,
            "usage_limits_max_chat_messages_per_session": (
                self.max_chat_messages_per_session
            ),
            "usage_limits_max_compare_per_session": self.max_compare_per_session,
            "usage_limits_daily_analysis_limit": self.daily_analysis_limit,
            "usage_limits_daily_cost_limit_usd": self.daily_cost_limit_usd,
        }

    def metrics_api_fields(self) -> dict[str, str | int | float]:
        return {
            "usage_limits_storage": self.storage,
            "usage_limits_daily_analyses": self.daily_analyses,
            "usage_limits_daily_estimated_cost_usd": round(
                self.daily_estimated_cost_usd, 6
            ),
            "usage_limits_max_analyses_per_session": self.max_analyses_per_session,
            "usage_limits_max_chat_messages_per_session": (
                self.max_chat_messages_per_session
            ),
            "usage_limits_max_compare_per_session": self.max_compare_per_session,
            "usage_limits_daily_analysis_limit": self.daily_analysis_limit,
            "usage_limits_daily_cost_limit_usd": self.daily_cost_limit_usd,
        }


def normalize_session_id(raw_session_id: str | None) -> str:
    if not raw_session_id:
        return ANONYMOUS_SESSION_ID

    cleaned = raw_session_id.strip()
    if SESSION_ID_PATTERN.fullmatch(cleaned):
        return cleaned
    return ANONYMOUS_SESSION_ID


class UsageLimitService:
    """
    Process-local usage and cost guardrails.

    Session counters are keyed by the client-provided
    `X-SnapInsight-Session-Id` header. Daily counters are global to this
    backend process. State resets on restart and is not shared across workers.
    """

    def __init__(self) -> None:
        self._session_counts: dict[str, dict[str, int]] = {}
        self._daily_date: str | None = None
        self._daily_analyses = 0
        self._daily_estimated_cost_usd = 0.0
        self._lock = asyncio.Lock()

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def _reset_daily_if_needed_locked(self) -> None:
        today = self._today_utc()
        if self._daily_date != today:
            self._daily_date = today
            self._daily_analyses = 0
            self._daily_estimated_cost_usd = 0.0

    def _session_bucket(self, session_id: str) -> dict[str, int]:
        return self._session_counts.setdefault(
            session_id,
            {"analyses": 0, "chats": 0, "compares": 0},
        )

    async def reserve_analysis(self, session_id: str, settings: Settings) -> None:
        async with self._lock:
            await self._reset_daily_if_needed_locked()
            bucket = self._session_bucket(session_id)

            if bucket["analyses"] >= settings.max_analyses_per_session:
                raise UsageLimitError(
                    error="session_analysis_limit",
                    message=(
                        "You have reached the analysis limit for this session. "
                        "Refresh the page to start a new session or try again later."
                    ),
                )

            if self._daily_analyses >= settings.daily_analysis_limit:
                raise UsageLimitError(
                    error="daily_analysis_limit",
                    message=(
                        "The daily analysis limit has been reached for this "
                        "deployment. Please try again tomorrow."
                    ),
                )

            bucket["analyses"] += 1
            self._daily_analyses += 1

    async def reserve_chat(self, session_id: str, settings: Settings) -> None:
        async with self._lock:
            bucket = self._session_bucket(session_id)
            if bucket["chats"] >= settings.max_chat_messages_per_session:
                raise UsageLimitError(
                    error="session_chat_limit",
                    message=(
                        "You have reached the chat message limit for this session. "
                        "Refresh the page to start a new session."
                    ),
                )
            bucket["chats"] += 1

    async def reserve_compare(self, session_id: str, settings: Settings) -> None:
        async with self._lock:
            bucket = self._session_bucket(session_id)
            if bucket["compares"] >= settings.max_compare_per_session:
                raise UsageLimitError(
                    error="session_compare_limit",
                    message=(
                        "You have reached the compare limit for this session. "
                        "Refresh the page to start a new session."
                    ),
                )
            bucket["compares"] += 1

    async def check_gemini_cost_allowed(
        self, settings: Settings, *, estimated_usd: float
    ) -> None:
        async with self._lock:
            await self._reset_daily_if_needed_locked()
            projected = self._daily_estimated_cost_usd + estimated_usd
            if projected > settings.daily_cost_limit_usd:
                raise UsageLimitError(
                    error="daily_cost_limit",
                    message=(
                        "The daily estimated Gemini cost limit has been reached "
                        "for this deployment. Please try again tomorrow."
                    ),
                )

    async def record_gemini_cost(self, amount_usd: float) -> None:
        async with self._lock:
            await self._reset_daily_if_needed_locked()
            self._daily_estimated_cost_usd += amount_usd

    async def snapshot(
        self, session_id: str, settings: Settings
    ) -> UsageLimitSnapshot:
        async with self._lock:
            await self._reset_daily_if_needed_locked()
            bucket = self._session_bucket(session_id)
            return UsageLimitSnapshot(
                storage="in_memory",
                session_analyses=bucket["analyses"],
                session_chats=bucket["chats"],
                session_compares=bucket["compares"],
                daily_analyses=self._daily_analyses,
                daily_estimated_cost_usd=self._daily_estimated_cost_usd,
                max_analyses_per_session=settings.max_analyses_per_session,
                max_chat_messages_per_session=settings.max_chat_messages_per_session,
                max_compare_per_session=settings.max_compare_per_session,
                daily_analysis_limit=settings.daily_analysis_limit,
                daily_cost_limit_usd=settings.daily_cost_limit_usd,
            )

    async def global_snapshot(self, settings: Settings) -> UsageLimitSnapshot:
        async with self._lock:
            await self._reset_daily_if_needed_locked()
            return UsageLimitSnapshot(
                storage="in_memory",
                session_analyses=0,
                session_chats=0,
                session_compares=0,
                daily_analyses=self._daily_analyses,
                daily_estimated_cost_usd=self._daily_estimated_cost_usd,
                max_analyses_per_session=settings.max_analyses_per_session,
                max_chat_messages_per_session=settings.max_chat_messages_per_session,
                max_compare_per_session=settings.max_compare_per_session,
                daily_analysis_limit=settings.daily_analysis_limit,
                daily_cost_limit_usd=settings.daily_cost_limit_usd,
            )

    async def reset(self) -> None:
        async with self._lock:
            self._session_counts = {}
            self._daily_date = None
            self._daily_analyses = 0
            self._daily_estimated_cost_usd = 0.0


usage_limits = UsageLimitService()
