from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_token_user, require_token
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
TokenDep = Annotated[str, Depends(require_token)]


def current_principal(token: TokenDep) -> dict[str, str]:
    user = get_token_user(token)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    return user


def require_menu(*menu_ids: str):
    """其它业务包只许调这个窄口。任一节点在有效菜单里即通过。"""
    if not menu_ids:
        raise ValueError("require_menu 至少要一个菜单节点 id")

    async def _check(
        session: SessionDep,
        principal: Annotated[dict[str, str], Depends(current_principal)],
    ) -> dict[str, str]:
        user = await user_by_login(session, principal["login_account"])
        if user is None or not user.enabled:
            raise ApiError(403, "FORBIDDEN", "已登录但无对应菜单或组件")
        granted = await effective_menu_ids(session, user)
        if not any(menu_id in granted for menu_id in menu_ids):
            raise ApiError(403, "FORBIDDEN", "已登录但无对应菜单或组件")
        return principal

    return _check


__all__ = [
    "MENU_DEPARTMENTS",
    "MENU_ROLE_QUERY",
    "MENU_ROLES",
    "MENU_USERS",
    "SessionDep",
    "TokenDep",
    "current_principal",
    "require_menu",
]
