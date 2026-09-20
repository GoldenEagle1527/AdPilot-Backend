from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import UserTag
from app.modules.system_admin.schemas.common import IdTags, Tag, TagList
from app.modules.system_admin.schemas.users import CreateUserTagRequest, SetUserTagsRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


def _tag(item: UserTag) -> dict[str, str]:
    return {"id": item.id, "name": item.name}


@router.get("/user-tags", response_model=Envelope[TagList])
async def list_user_tags(session: SessionDep, _principal: PrincipalDep) -> dict:
    result = await session.execute(select(UserTag).order_by(UserTag.id))
    return success({"items": [_tag(item) for item in result.scalars().all()]})


@router.post("/user-tags", response_model=Envelope[Tag])
async def create_user_tag(
    body: CreateUserTagRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    existing = await session.execute(select(UserTag.id).where(UserTag.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise ApiError(409, "CONFLICT", "同名已存在")
    tag = UserTag(name=body.name)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "CONFLICT", "同名已存在") from exc
    await session.refresh(tag)
    return success(_tag(tag))


@router.put("/users/{user_id}/tags", response_model=Envelope[IdTags])
async def set_user_tags(
    user_id: str,
    body: SetUserTagsRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    unique_ids = list(dict.fromkeys(body.tag_ids))
    if unique_ids:
        result = await session.execute(select(UserTag).where(UserTag.id.in_(unique_ids)))
        tags = {tag.id: tag for tag in result.scalars().all()}
        missing = [tag_id for tag_id in unique_ids if tag_id not in tags]
        if missing:
            raise ApiError(404, "NOT_FOUND", "标签不存在")
        user.tags = [tags[tag_id] for tag_id in unique_ids]
    else:
        user.tags = []
    await session.commit()
    user = await get_user(session, user_id)
    return success({"id": user.id, "tags": [_tag(tag) for tag in sorted(user.tags, key=lambda t: t.id)]})
