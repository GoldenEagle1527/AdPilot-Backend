from __future__ import annotations

from datetime import datetime, timezone


def iso8601_z(value: datetime) -> str:
    """对外时间：ISO-8601 UTC，带 `Z`。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")
