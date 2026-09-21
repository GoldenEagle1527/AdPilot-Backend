from __future__ import annotations

from app.core.envelope import ApiError


def parse_int_id(raw: object) -> str | None:
    """十进制正整数（无前导零）。非法返回 None。"""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return str(raw) if raw >= 1 else None
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text.isdigit():
        return None
    value = int(text)
    if value < 1 or text != str(value):
        return None
    return str(value)


def require_int_id(raw: object, not_found: str) -> str:
    parsed = parse_int_id(raw)
    if parsed is None:
        raise ApiError(404, "NOT_FOUND", not_found)
    return parsed
