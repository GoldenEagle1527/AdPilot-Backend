"""部门树：查询、新增、改名/改父、启停、软删。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import MENU_DEPARTMENTS, SessionDep, require_menu
from app.modules.system_admin.domain import Department, User
from app.modules.system_admin.domain.access import (
    assert_user_manager_remains,
    publish_acl_for_users,
    user_ids_in_department,
)
from app.modules.system_admin.domain.ids import parse_int_id, require_int_id
from app.modules.system_admin.domain.org import department_not_deleted, user_not_deleted
from app.modules.system_admin.schemas.common import DeletedId, DepartmentNode, DepartmentTree, IdEnabled
from app.modules.system_admin.schemas.departments import (
    CreateDepartmentBody,
    SetDepartmentStatusBody,
    UpdateDepartmentBody,
    build_department_tree,
    department_node,
    filter_departments,
)

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

_DEPT_LOAD = (selectinload(Department.tags), selectinload(Department.roles))


def _principal(user: dict[str, str] = Depends(require_menu(MENU_DEPARTMENTS))) -> dict[str, str]:
    return user


async def _get_department(session: SessionDep, department_id: str) -> Department:
    department_id = require_int_id(department_id, "部门不存在")
    result = await session.scalars(
        select(Department)
        .where(Department.id == int(department_id), department_not_deleted())
        .options(*_DEPT_LOAD)
    )
    dept = result.first()
    if dept is None:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    return dept


async def _require_parent(session: SessionDep, parent_id: str | None) -> None:
    if parent_id is None:
        return
    parent_id = require_int_id(parent_id, "父部门不存在")
    parent = await session.scalar(
        select(Department).where(Department.id == int(parent_id), department_not_deleted())
    )
    if parent is None:
        raise ApiError(404, "NOT_FOUND", "父部门不存在")
    if not parent.enabled:
        raise ApiError(409, "DEPARTMENT_DISABLED", "部门已停用")


async def _would_cycle(session: SessionDep, dept_id: str, parent_id: str | None) -> bool:
    if parent_id is None:
        return False
    cursor: str | None = None if parent_id is None else str(parent_id)
    dept_key = str(dept_id)
    seen: set[str] = set()
    while cursor is not None:
        if cursor == dept_key:
            return True
        if cursor in seen:
            return True
        seen.add(cursor)
        parsed = parse_int_id(cursor)
        if parsed is None:
            return False
        parent = await session.get(Department, int(parsed))
        if parent is None or parent.deleted_at is not None:
            return False
        cursor = None if parent.parent_id is None else str(parent.parent_id)
    return False


@router.get("/departments", response_model=Envelope[DepartmentTree], summary="查询部门树")
async def list_departments(
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
    name: str | None = None,
    enabled: bool | None = None,
    id: str | None = None,
):
    """列出未删除部门树，可按名称、启用状态、id 过滤；节点含标签与角色。"""
    result = await session.scalars(
        select(Department).where(department_not_deleted()).options(*_DEPT_LOAD)
    )
    items = build_department_tree(
        filter_departments(list(result.all()), name, enabled, id)
    )
    return success({"items": items})


@router.post("/departments", response_model=Envelope[DepartmentNode], summary="新增部门")
async def create_department(
    body: CreateDepartmentBody,
    session: SessionDep,
    user: dict[str, str] = Depends(_principal),
):
    """新增部门或子部门，默认启用。"""
    await _require_parent(session, body.parent_id)
    tenant = body.tenant if body.tenant is not None else user["tenant"]
    dept = Department(
        name=body.name,
        parent_id=None if body.parent_id is None else int(require_int_id(body.parent_id, "父部门不存在")),
        sort=body.sort,
        enabled=True,
        tenant=tenant,
    )
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    loaded = await _get_department(session, dept.id)
    return success(department_node(loaded, children=[]))


@router.put("/departments/{id}", response_model=Envelope[DepartmentNode], summary="改部门")
async def update_department(
    id: str,
    body: UpdateDepartmentBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    """改名称、父部门、排序；禁止把父部门设为自身或子孙。"""
    dept = await _get_department(session, id)
    await _require_parent(session, body.parent_id)
    if await _would_cycle(session, id, body.parent_id):
        raise ApiError(409, "CYCLE_NOT_ALLOWED", "不能将父部门设为自身或子孙")
    dept.name = body.name
    dept.parent_id = (
        None if body.parent_id is None else int(require_int_id(body.parent_id, "父部门不存在"))
    )
    dept.sort = body.sort
    session.add(dept)
    await session.commit()
    loaded = await _get_department(session, id)
    return success(department_node(loaded, children=[]))


@router.patch(
    "/departments/{id}/status",
    response_model=Envelope[IdEnabled],
    summary="部门启停",
)
async def set_department_status(
    id: str,
    body: SetDepartmentStatusBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    """启用或停用部门，并刷新该部门用户授权。"""
    dept = await _get_department(session, id)
    dept.enabled = body.enabled
    session.add(dept)
    await assert_user_manager_remains(session)
    await session.commit()
    await publish_acl_for_users(session, await user_ids_in_department(session, str(dept.id)))
    return success({"id": str(dept.id), "enabled": bool(dept.enabled)})


@router.delete("/departments/{id}", response_model=Envelope[DeletedId], summary="软删部门")
async def delete_department(
    id: str,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    """软删部门。有子部门或在职员工时拒绝。"""
    dept = await _get_department(session, id)
    child_n = int(
        await session.scalar(
            select(func.count())
            .select_from(Department)
            .where(Department.parent_id == dept.id, department_not_deleted())
        )
        or 0
    )
    if child_n:
        raise ApiError(409, "HAS_CHILDREN", "请先删除或挪走子部门")
    member_n = int(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.department_id == dept.id, user_not_deleted())
        )
        or 0
    )
    if member_n:
        raise ApiError(409, "HAS_MEMBERS", "部门下仍有员工，请先把员工挪到其他部门")
    dept.deleted_at = datetime.now(timezone.utc)
    session.add(dept)
    await session.commit()
    return success({"id": str(dept.id), "deleted": True})
