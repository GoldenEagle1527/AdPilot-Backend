"""用户在某个菜单上的一份 JSON 配置。不是角色能不能看见这个菜单。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.system_admin.domain.models import MenuNode, UserMenuConfig


async def read_menu_config(session: AsyncSession, user_id: int, menu_id: int) -> dict[str, Any] | None:
    """没有配置，或这一行已删，返回空。调用方再用该菜单的默认列。"""
    await _require_menu(session, menu_id)
    row = await _row(session, user_id, menu_id)
    if row is None or row.is_deleted:
        return None
    return dict(row.config)


async def save_menu_config(
    session: AsyncSession, user_id: int, menu_id: int, config: dict[str, Any]
) -> dict[str, Any]:
    """整份替换这个用户在这个菜单上的配置。"""
    await _require_menu(session, menu_id)
    row = await _row(session, user_id, menu_id)
    stored = dict(config)
    if row is None:
        session.add(UserMenuConfig(user_id=user_id, menu_id=menu_id, config=stored))
    else:
        row.config = stored
        row.is_deleted = 0
        row.deleted_at = None
    await session.flush()
    return stored


async def _require_menu(session: AsyncSession, menu_id: int) -> None:
    row = await session.get(MenuNode, menu_id)
    if row is None or row.is_deleted:
        raise ApiError(404, "菜单不存在")


async def _row(session: AsyncSession, user_id: int, menu_id: int) -> UserMenuConfig | None:
    return await session.scalar(
        select(UserMenuConfig).where(
            UserMenuConfig.user_id == user_id,
            UserMenuConfig.menu_id == menu_id,
        )
    )
