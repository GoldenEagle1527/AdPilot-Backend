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


def require_int_id(raw: object, not_found: str) -> int:
    """校验后返回整型主键，供 SQL 比较；对外信封仍用 str(...)。"""
    parsed = parse_int_id(raw)
    if parsed is None:
        raise ApiError(404, not_found)
    return int(parsed)
