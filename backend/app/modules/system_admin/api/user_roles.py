"""用户角色：查询已分配表（含只读部门角色），只替换用户角色。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError, Envelope, success
from app.core.times import iso8601_z
from app.modules.system_admin.api.users import department_roles_by_dept, get_user
from app.modules.system_admin.domain.ids import require_int_id
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.access import (
    assert_self_keeps_user_menu,
    assert_user_manager_remains,
    publish_acl_for_users,
)
from app.modules.system_admin.domain.models import Role, User, UserRole
from app.modules.system_admin.schemas.common import UserRolesData
from app.modules.system_admin.schemas.users import SetUserRolesRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


async def user_roles_payload(session: AsyncSession, user: User) -> dict:
    roles = list((await session.execute(select(Role).order_by(Role.id))).scalars().all())
    assigned_rows = (
        await session.execute(select(UserRole).where(UserRole.user_id == user.id))
    ).scalars().all()
    assigned_at = {row.role_id: row.assigned_at for row in assigned_rows}
    items = [
        {
            "id": str(role.id),
            "name": role.name,
            "assigned": role.id in assigned_at,
            "assigned_at": iso8601_z(assigned_at[role.id]) if role.id in assigned_at else None,
        }
        for role in roles
    ]
    dept_roles = (await department_roles_by_dept(session, [user.department_id])).get(
        user.department_id, []
    )
    return {
        "items": items,
        "department_roles": [{"id": str(role.id), "name": role.name} for role in dept_roles],
    }


@router.get("/users/{user_id}/roles", response_model=Envelope[UserRolesData], summary="用户角色已分配表")
async def list_user_roles(
    user_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """列出全部角色及该用户是否已分配；部门角色只读附带。"""
    user = await get_user(session, user_id)
    return success(await user_roles_payload(session, user))


@router.put("/users/{user_id}/roles", response_model=Envelope[UserRolesData], summary="替换用户角色")
async def set_user_roles(
    user_id: str,
    body: SetUserRolesRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """只替换用户角色，不改部门角色；随后刷新授权。"""
    user = await get_user(session, user_id)
    unique_ids = [require_int_id(item, "角色不存在") for item in dict.fromkeys(body.role_ids)]
    if unique_ids:
        result = await session.execute(select(Role).where(Role.id.in_([int(item) for item in unique_ids])))
        roles = {str(role.id): role for role in result.scalars().all()}
        missing = [role_id for role_id in unique_ids if str(role_id) not in roles]
        if missing:
            raise ApiError(404, "NOT_FOUND", "角色不存在")
        user.roles = [roles[str(role_id)] for role_id in unique_ids]
    else:
        user.roles = []
    if _principal["id"] == str(user.id):
        await assert_self_keeps_user_menu(session, str(user.id))
    await assert_user_manager_remains(session)
    await session.commit()
    await publish_acl_for_users(session, [str(user.id)])
    user = await get_user(session, user_id)
    return success(await user_roles_payload(session, user))
