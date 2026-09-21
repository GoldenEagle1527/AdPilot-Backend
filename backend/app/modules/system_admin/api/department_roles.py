"""部门角色：查询已分配表，整表替换。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import MENU_DEPARTMENTS, SessionDep, require_menu
from app.modules.system_admin.domain import Department, DepartmentRole, Role
from app.modules.system_admin.domain.org import department_not_deleted
from app.modules.system_admin.domain.access import (
    assert_user_manager_remains,
    publish_acl_for_users,
    user_ids_in_department,
)
from app.modules.system_admin.domain.ids import require_int_id
from app.modules.system_admin.schemas.common import RoleBriefList
from app.modules.system_admin.schemas.departments import SetDepartmentRolesBody, role_brief

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])


def _principal(user: dict[str, str] = Depends(require_menu(MENU_DEPARTMENTS))) -> dict[str, str]:
    return user


async def _require_department(session: SessionDep, department_id: str) -> Department:
    department_id = require_int_id(department_id, "部门不存在")
    dept = await session.scalar(
        select(Department).where(Department.id == int(department_id), department_not_deleted())
    )
    if dept is None:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    return dept


async def _all_role_briefs(session: SessionDep, department_id: str) -> list[dict]:
    roles = list((await session.scalars(select(Role).order_by(Role.id))).all())
    dept_pk = int(require_int_id(department_id, "部门不存在"))
    links = list(
        (
            await session.scalars(
                select(DepartmentRole).where(DepartmentRole.department_id == dept_pk)
            )
        ).all()
    )
    assigned_at = {link.role_id: link.assigned_at for link in links}
    return [
        role_brief(role, role.id in assigned_at, assigned_at.get(role.id)) for role in roles
    ]


@router.get(
    "/departments/{id}/roles",
    response_model=Envelope[RoleBriefList],
    summary="部门角色已分配表",
)
async def list_department_roles(
    id: str,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    """列出全部角色及该部门是否已分配。"""
    await _require_department(session, id)
    return success({"items": await _all_role_briefs(session, id)})


@router.put(
    "/departments/{id}/roles",
    response_model=Envelope[RoleBriefList],
    summary="替换部门角色",
)
async def set_department_roles(
    id: str,
    body: SetDepartmentRolesBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    """用 role_ids 整表替换部门角色，并刷新该部门下用户授权。"""
    await _require_department(session, id)
    unique_ids = [require_int_id(item, "角色不存在") for item in dict.fromkeys(body.role_ids)]
    if unique_ids:
        found = set(
            (await session.scalars(select(Role.id).where(Role.id.in_([int(item) for item in unique_ids])))).all()
        )
        if any(str(rid) not in {str(item) for item in found} for rid in unique_ids):
            raise ApiError(404, "NOT_FOUND", "角色不存在")
    await session.execute(delete(DepartmentRole).where(DepartmentRole.department_id == int(id)))
    for role_id in unique_ids:
        session.add(DepartmentRole(department_id=int(id), role_id=int(role_id)))
    await assert_user_manager_remains(session)
    await session.commit()
    await publish_acl_for_users(session, await user_ids_in_department(session, str(id)))
    return success({"items": await _all_role_briefs(session, id)})
