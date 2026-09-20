from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import Department
from app.modules.system_admin.domain.org import department_not_deleted, expand_department_ids, stored_data_scope_ids
from app.modules.system_admin.schemas.common import DepartmentIds
from app.modules.system_admin.schemas.users import SetUserDataScopeRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


@router.get("/users/{user_id}/data-scope", response_model=Envelope[DepartmentIds])
async def get_user_data_scope(
    user_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    return success({"department_ids": await stored_data_scope_ids(session, user)})


@router.put("/users/{user_id}/data-scope", response_model=Envelope[DepartmentIds])
async def set_user_data_scope(
    user_id: str,
    body: SetUserDataScopeRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    unique_ids = list(dict.fromkeys(body.department_ids))
    if unique_ids:
        result = await session.execute(
            select(Department).where(Department.id.in_(unique_ids), department_not_deleted())
        )
        departments = {dept.id: dept for dept in result.scalars().all()}
        missing = [dept_id for dept_id in unique_ids if dept_id not in departments]
        if missing:
            raise ApiError(404, "NOT_FOUND", "部门不存在")
        expanded = await expand_department_ids(session, unique_ids)
        found = await session.execute(
            select(Department).where(Department.id.in_(expanded), department_not_deleted())
        )
        by_id = {dept.id: dept for dept in found.scalars().all()}
        user.data_scope_departments = [by_id[dept_id] for dept_id in expanded if dept_id in by_id]
    else:
        user.data_scope_departments = []
    await session.commit()
    user = await get_user(session, user_id)
    return success({"department_ids": await stored_data_scope_ids(session, user)})
