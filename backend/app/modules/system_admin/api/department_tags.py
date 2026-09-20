from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import MENU_DEPARTMENTS, SessionDep, require_menu
from app.modules.system_admin.domain import Department, DepartmentTag
from app.modules.system_admin.schemas.common import IdTags, Tag, TagList
from app.modules.system_admin.schemas.departments import (
    CreateDepartmentTagBody,
    SetDepartmentTagsBody,
    tag_item,
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


@router.get("/department-tags", response_model=Envelope[TagList])
async def list_department_tags(
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    result = await session.scalars(select(DepartmentTag).order_by(DepartmentTag.name, DepartmentTag.id))
    return success({"items": [tag_item(t) for t in result.all()]})


@router.post("/department-tags", response_model=Envelope[Tag])
async def create_department_tag(
    body: CreateDepartmentTagBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    existing = await session.scalar(
        select(DepartmentTag.id).where(DepartmentTag.name == body.name)
    )
    if existing is not None:
        raise ApiError(409, "CONFLICT", "标签同名")
    tag = DepartmentTag(name=body.name)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "CONFLICT", "标签同名") from exc
    await session.refresh(tag)
    return success(tag_item(tag))


@router.put("/departments/{id}/tags", response_model=Envelope[IdTags])
async def set_department_tags(
    id: str,
    body: SetDepartmentTagsBody,
    session: SessionDep,
    _user: dict[str, str] = Depends(_principal),
):
    dept = await _get_department(session, id)
    unique_ids = list(dict.fromkeys(body.tag_ids))
    if unique_ids:
        found = list(
            (
                await session.scalars(select(DepartmentTag).where(DepartmentTag.id.in_(unique_ids)))
            ).all()
        )
        found_by_id = {t.id: t for t in found}
        missing = [tid for tid in unique_ids if tid not in found_by_id]
        if missing:
            raise ApiError(404, "NOT_FOUND", "标签不存在")
        dept.tags = [found_by_id[tid] for tid in unique_ids]
    else:
        dept.tags = []
    session.add(dept)
    await session.commit()
    loaded = await _get_department(session, id)
    return success({"id": loaded.id, "tags": [tag_item(t) for t in loaded.tags]})
