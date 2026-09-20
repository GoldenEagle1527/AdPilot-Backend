from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import MENU_DEPARTMENTS, SessionDep, require_menu
from app.modules.system_admin.domain import Department
from app.modules.system_admin.schemas.common import DepartmentNode, DepartmentTree, IdEnabled
from app.modules.system_admin.schemas.departments import (
    CreateDepartmentBody,
    SetDepartmentStatusBody,
    UpdateDepartmentBody,
    build_department_tree,
    department_node,
    filter_departments,
)

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])


def _principal(user: dict[str, str] = Depends(require_menu(MENU_DEPARTMENTS))) -> dict[str, str]:
    return user


async def _get_department(session: SessionDep, department_id: str) -> Department:
    result = await session.scalars(
        select(Department)
        .where(Department.id == department_id)
        .options(selectinload(Department.tags))
    )
    dept = result.first()
    if dept is None:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    return dept


async def _require_parent(session: SessionDep, parent_id: str | None) -> None:
    if parent_id is None:
        return
    parent = await session.get(Department, parent_id)
    if parent is None:
        raise ApiError(404, "NOT_FOUND", "父部门不存在")


async def _would_cycle(session: SessionDep, dept_id: str, parent_id: str | None) -> bool:
    if parent_id is None:
        return False
    cursor: str | None = parent_id
    seen: set[str] = set()
    while cursor is not None:
        if cursor == dept_id:
            return True
        if cursor in seen:
            return True
        seen.add(cursor)
        parent = await session.get(Department, cursor)
        if parent is None:
            return False
        cursor = parent.parent_id
    return False


@router.get("/departments", response_model=Envelope[DepartmentTree])
async def list_departments(
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
    name: str | None = None,
    enabled: bool | None = None,
):
    result = await session.scalars(
        select(Department).options(selectinload(Department.tags))
    )
    items = build_department_tree(filter_departments(list(result.all()), name, enabled))
    return success({"items": items})


@router.post("/departments", response_model=Envelope[DepartmentNode])
async def create_department(
    body: CreateDepartmentBody,
    session: SessionDep,
    user: dict[str, str] = Depends(_principal),
):
    await _require_parent(session, body.parent_id)
    tenant = body.tenant if body.tenant is not None else user["tenant"]
    dept = Department(
        name=body.name,
        parent_id=body.parent_id,
        sort=body.sort,
        enabled=True,
        tenant=tenant,
    )
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    loaded = await _get_department(session, dept.id)
    return success(department_node(loaded, children=[]))


@router.put("/departments/{id}", response_model=Envelope[DepartmentNode])
async def update_department(
    id: str,
    body: UpdateDepartmentBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    dept = await _get_department(session, id)
    await _require_parent(session, body.parent_id)
    if await _would_cycle(session, id, body.parent_id):
        raise ApiError(409, "CYCLE_NOT_ALLOWED", "不能将父部门设为自身或子孙")
    dept.name = body.name
    dept.parent_id = body.parent_id
    dept.sort = body.sort
    session.add(dept)
    await session.commit()
    loaded = await _get_department(session, id)
    return success(department_node(loaded, children=[]))


@router.patch("/departments/{id}/status", response_model=Envelope[IdEnabled])
async def set_department_status(
    id: str,
    body: SetDepartmentStatusBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    dept = await session.get(Department, id)
    if dept is None:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    dept.enabled = body.enabled
    session.add(dept)
    await session.commit()
    return success({"id": dept.id, "enabled": bool(dept.enabled)})
