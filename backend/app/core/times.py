from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")


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
