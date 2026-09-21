from __future__ import annotations

DEPARTMENT_TAG_NAMES: tuple[str, ...] = ("投放部", "投放组", "素材部", "素材组")
USER_TAG_NAMES: tuple[str, ...] = ("投手", "素材手")

DEPARTMENT_TAG_SEED: list[dict[str, object]] = [
    {"id": 1, "name": "投放部"},
    {"id": 2, "name": "投放组"},
    {"id": 3, "name": "素材部"},
    {"id": 4, "name": "素材组"},
]

USER_TAG_SEED: list[dict[str, object]] = [
    {"id": 1, "name": "投手"},
    {"id": 2, "name": "素材手"},
]


def require_department_tag_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned not in DEPARTMENT_TAG_NAMES:
        raise ValueError("部门标签只允许：投放部、投放组、素材部、素材组")
    return cleaned


def require_user_tag_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned not in USER_TAG_NAMES:
        raise ValueError("用户标签只允许：投手、素材手")
    return cleaned
