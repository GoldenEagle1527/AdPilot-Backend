"""巨量广告自定义列。配置挂在用户打开的那个菜单上，不是按页面名字各存一行。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.ocean_ads.schema import MENU_COLUMNS
from app.modules.system_admin import read_menu_config, require_menu, save_menu_config


async def assert_menu(session: AsyncSession, principal: dict[str, Any], menu_id: int) -> None:
    """调用人要有这个菜单。账户、项目、广告、素材以外的菜单没有自定义列。"""
    if menu_id not in MENU_COLUMNS:
        raise ApiError(400, "这个菜单没有自定义列")
    await require_menu(str(menu_id))(session, principal)


def kept_fixed(raw: object, columns: list[str]) -> list[str]:
    """固定列必须是已选列，去重后最多 5 个。旧配置没有这一项时为空。"""
    if not isinstance(raw, list):
        return []
    chosen = set(columns)
    fixed: list[str] = []
    for name in raw:
        text = str(name)
        if text in chosen and text not in fixed:
            fixed.append(text)
        if len(fixed) == 5:
            break
    return fixed


async def read_columns(session: AsyncSession, user_id: int, menu_id: int) -> dict[str, Any]:
    """没有配置就返回该菜单的默认列和默认顺序。点表头排序不在这里。"""
    config = await read_menu_config(session, user_id, menu_id)
    saved = None if config is None else config.get("columns")
    if not isinstance(saved, list) or not saved:
        columns = list(MENU_COLUMNS[menu_id])
        fixed: list[str] = []
    else:
        columns = [str(name) for name in saved]
        fixed = kept_fixed(config.get("fixed_columns"), columns)
    return {"menu_id": menu_id, "columns": columns, "fixed_columns": fixed}


async def save_columns(
    session: AsyncSession, user_id: int, menu_id: int, columns: list[str], fixed_columns: list[str]
) -> dict[str, Any]:
    """替换这个用户在这个菜单上的勾选、顺序和固定列。"""
    stored = {"columns": list(columns), "fixed_columns": list(fixed_columns)}
    await save_menu_config(session, user_id, menu_id, stored)
    return {"menu_id": menu_id, "columns": stored["columns"], "fixed_columns": stored["fixed_columns"]}
