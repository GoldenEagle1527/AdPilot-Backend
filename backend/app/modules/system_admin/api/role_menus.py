"""角色菜单勾选：查询已勾节点，整表替换。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import MENU_ROLES, SessionDep, require_menu
from app.modules.system_admin.domain.access import publish_acl_for_users, user_ids_holding_role
from app.modules.system_admin.domain.models import MenuNode, Role, RoleMenu
from app.modules.system_admin.schemas.common import MenuIds
from app.modules.system_admin.schemas.roles import SetRoleMenusBody

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_ROLES))]


async def _require_role(session: AsyncSession, role_id: str) -> Role:
    role = await session.get(Role, role_id)
    if role is None:
        raise ApiError(404, "NOT_FOUND", "角色不存在")
    return role


def _unique_keep_order(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


@router.get("/roles/{role_id}/menus", response_model=Envelope[MenuIds], summary="角色已勾菜单")
async def get_role_menus(
    role_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
):
    """返回该角色已勾选的菜单/组件节点 id。"""
    await _require_role(session, role_id)
    rows = (
        await session.execute(select(RoleMenu.menu_id).where(RoleMenu.role_id == role_id))
    ).scalars().all()
    return success({"menu_ids": list(rows)})


@router.put("/roles/{role_id}/menus", response_model=Envelope[MenuIds], summary="替换角色菜单勾选")
async def set_role_menus(
    role_id: str,
    body: SetRoleMenusBody,
    session: SessionDep,
    principal: PrincipalDep,
):
    """用 menu_ids 整表替换角色勾选，并刷新持有该角色的用户授权。"""
    role = await _require_role(session, role_id)
    menu_ids = _unique_keep_order(body.menu_ids)
    if menu_ids:
        found = set(
            (
                await session.execute(select(MenuNode.id).where(MenuNode.id.in_(menu_ids)))
            ).scalars().all()
        )
        if found != set(menu_ids):
            raise ApiError(404, "NOT_FOUND", "菜单节点不存在")
    await session.execute(delete(RoleMenu).where(RoleMenu.role_id == role_id))
    session.add_all([RoleMenu(role_id=role_id, menu_id=mid) for mid in menu_ids])
    role.updated_by = principal["login_account"]
    role.updated_at = datetime.now(timezone.utc)
    session.add(role)
    await session.commit()
    await publish_acl_for_users(session, await user_ids_holding_role(session, role_id))
    return success({"menu_ids": menu_ids})
