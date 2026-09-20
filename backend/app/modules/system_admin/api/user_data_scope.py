from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import Department
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
    department_ids = [dept.id for dept in user.data_scope_departments]
    return success({"department_ids": department_ids})


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
        result = await session.execute(select(Department).where(Department.id.in_(unique_ids)))
        departments = {dept.id: dept for dept in result.scalars().all()}
        missing = [dept_id for dept_id in unique_ids if dept_id not in departments]
        if missing:
            raise ApiError(404, "NOT_FOUND", "部门不存在")
        # 整集替换提交的 id，不自动展开子孙。
        user.data_scope_departments = [departments[dept_id] for dept_id in unique_ids]
    else:
        user.data_scope_departments = []
    await session.commit()
    user = await get_user(session, user_id)
    return success({"department_ids": [dept.id for dept in user.data_scope_departments]})
