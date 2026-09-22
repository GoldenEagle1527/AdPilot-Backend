"""用户数据范围：查询已勾部门，勾选后服务端展开子孙。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.domain.ids import require_int_id
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import Department
from app.modules.system_admin.domain.org import (
    department_not_deleted,
    expand_department_ids,
    stored_data_scope_ids,
)
from app.modules.system_admin.schemas.common import DepartmentIds
from app.modules.system_admin.schemas.users import SetUserDataScopeRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


@router.get(
    "/users/{user_id}/data-scope",
    response_model=Envelope[DepartmentIds],
    summary="用户已勾选数据范围",
)
async def get_user_data_scope(
    user_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """返回已存储范围再展开后的部门 id（含后来新建的启用子孙）。"""
    user = await get_user(session, user_id)
    stored = await stored_data_scope_ids(session, user)
    return success(
        {"department_ids": await expand_department_ids(session, stored, enabled_only=True)}
    )


@router.put(
    "/users/{user_id}/data-scope",
    response_model=Envelope[DepartmentIds],
    summary="设置用户数据范围",
)
async def set_user_data_scope(
    user_id: str,
    body: SetUserDataScopeRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """勾选部门并由服务端展开子孙；空列表表示仅本人。"""
    user = await get_user(session, user_id)
    unique_ids = [require_int_id(item, "部门不存在") for item in dict.fromkeys(body.department_ids)]
    if unique_ids:
        result = await session.execute(
            select(Department).where(
                Department.id.in_([int(item) for item in unique_ids]),
                department_not_deleted(),
            )
        )
        departments = {str(dept.id): dept for dept in result.scalars().all()}
        missing = [dept_id for dept_id in unique_ids if str(dept_id) not in departments]
        if missing:
            raise ApiError(404, "部门不存在")
        if any(not dept.enabled for dept in departments.values()):
            raise ApiError(409, "部门已停用")
        expanded = await expand_department_ids(session, unique_ids, enabled_only=True)
        found = await session.execute(
            select(Department).where(
                Department.id.in_([int(item) for item in expanded]),
                department_not_deleted(),
            )
        )
        by_id = {str(dept.id): dept for dept in found.scalars().all()}
        user.data_scope_departments = [by_id[str(dept_id)] for dept_id in expanded if str(dept_id) in by_id]
    else:
        user.data_scope_departments = []
    await session.commit()
    user = await get_user(session, user_id)
    stored = await stored_data_scope_ids(session, user)
    return success(
        {"department_ids": await expand_department_ids(session, stored, enabled_only=True)}
    )
