from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError
from app.modules.system_admin.domain.access import (
    MENU_DEPARTMENTS,
    MENU_ROLE_QUERY,
    MENU_ROLES,
    MENU_USERS,
    effective_menu_ids,
    user_by_login,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


async def current_principal(principal: PrincipalDep) -> dict[str, Any]:
    return principal


def require_menu(*menu_ids: str):
    """其它业务包只许调这个窄口。任一节点在有效菜单里即通过。优先用会话里缓存的 menu_ids。"""
    if not menu_ids:
        raise ValueError("require_menu 至少要一个菜单节点 id")
    needed = frozenset(menu_ids)

    async def _check(
        session: SessionDep,
        principal: PrincipalDep,
    ) -> dict[str, Any]:
        granted = principal.get("menu_ids")
        enabled = principal.get("enabled")
        if not isinstance(granted, list) or enabled is None:
            user = await user_by_login(session, str(principal["login_account"]))
            if user is None or not user.enabled:
                raise ApiError(403, "已登录但无对应菜单或组件")
            granted = list(await effective_menu_ids(session, user))
            enabled = True
        if enabled is False:
            raise ApiError(403, "已登录但无对应菜单或组件")
        granted_set = granted if isinstance(granted, set) else set(granted)
        if needed.isdisjoint(granted_set):
            raise ApiError(403, "已登录但无对应菜单或组件")
        return principal

    return _check


__all__ = [
    "MENU_DEPARTMENTS",
    "MENU_ROLE_QUERY",
    "MENU_ROLES",
    "MENU_USERS",
    "PrincipalDep",
    "SessionDep",
    "current_principal",
    "require_menu",
]
