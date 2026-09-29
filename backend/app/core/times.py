from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")
STAMP = "%Y-%m-%d %H:%M:%S"


def beijing_now() -> datetime:
    """当前北京时间。"""
    return datetime.now(BEIJING)


def beijing_iso(value: datetime) -> str:
    """把时间转成北京 ISO 串，带 +08:00。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING)
    else:
        value = value.astimezone(BEIJING)
    return value.replace(microsecond=0).isoformat()


def parse_beijing_stamp(value: str | None) -> datetime | None:
    """把 YYYY-MM-DD HH:MM:SS 北京时间串收成带时区时间。空为 None，格式不对抛 ValueError。"""
    return datetime.strptime(value, STAMP).replace(tzinfo=BEIJING) if value else None


def beijing_stamp(value: datetime | None) -> str:
    """时间收成北京 YYYY-MM-DD HH:MM:SS，空为空串。"""
    return "" if value is None else value.astimezone(BEIJING).strftime(STAMP)
