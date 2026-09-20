from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.times import iso8601_z

BEIJING = ZoneInfo("Asia/Shanghai")
_NAIVE_FMT = "%Y-%m-%d %H:%M:%S"


def to_beijing_naive(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BEIJING).strftime(_NAIVE_FMT)


def parse_changdu_time(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, _NAIVE_FMT)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BEIJING)
    return parsed


def display_changdu_time(raw: str) -> str:
    parsed = parse_changdu_time(raw)
    if parsed is None:
        return raw or ""
    return iso8601_z(parsed)


def beijing_today_prefix(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(BEIJING).strftime("%Y-%m-%d")
