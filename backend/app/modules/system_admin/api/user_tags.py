"""用户标签目录，以及给用户打标/换标/去标。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.domain.ids import require_int_id
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import UserTag
from app.modules.system_admin.domain.tags import require_user_tag_name
from app.modules.system_admin.schemas.common import BatchTagResult, IdTags, Tag, TagList
from app.modules.system_admin.schemas.users import AddUserTagsRequest, CreateUserTagRequest, SetUserTagsRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


def _tag(item: UserTag) -> dict[str, str]:
    return {"id": str(item.id), "name": item.name}


async def _tags_by_ids(session, tag_ids: list[str]) -> list[UserTag]:
    unique_ids = [require_int_id(item, "标签不存在") for item in dict.fromkeys(tag_ids)]
    result = await session.execute(select(UserTag).where(UserTag.id.in_(unique_ids)))
    tags = {str(tag.id): tag for tag in result.scalars().all()}
    missing = [tag_id for tag_id in unique_ids if str(tag_id) not in tags]
    if missing:
        raise ApiError(404, "NOT_FOUND", "标签不存在")
    return [tags[str(tag_id)] for tag_id in unique_ids]


@router.get("/user-tags", response_model=Envelope[TagList], summary="用户标签目录")
async def list_user_tags(session: SessionDep, _principal: PrincipalDep) -> dict:
    """列出固定枚举的用户标签（投手、素材手）。"""
    result = await session.execute(select(UserTag).order_by(UserTag.id))
    return success({"items": [_tag(item) for item in result.scalars().all()]})


@router.post("/user-tags", response_model=Envelope[Tag], summary="新增用户标签")
async def create_user_tag(
    body: CreateUserTagRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """仅允许枚举名；同名冲突。"""
    try:
        name = require_user_tag_name(body.name)
    except ValueError as exc:
        raise ApiError(422, "TAG_NOT_ALLOWED", str(exc)) from exc
    existing = await session.execute(select(UserTag.id).where(UserTag.name == name))
    if existing.scalar_one_or_none() is not None:
        raise ApiError(409, "CONFLICT", "同名已存在")
    tag = UserTag(name=name)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "CONFLICT", "同名已存在") from exc
    await session.refresh(tag)
    return success(_tag(tag))


@router.put("/users/batch-tags", response_model=Envelope[BatchTagResult], summary="批量给用户追加标签")
async def add_user_tags(
    body: AddUserTagsRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """给多个用户追加标签，已有的不重复加。"""
    tags = await _tags_by_ids(session, body.tag_ids)
    for user_id in list(dict.fromkeys(body.user_ids)):
        user = await get_user(session, user_id)
        have = {str(t.id) for t in user.tags}
        user.tags = list(user.tags) + [t for t in tags if str(t.id) not in have]
    await session.commit()
    items = []
    for user_id in list(dict.fromkeys(body.user_ids)):
        user = await get_user(session, user_id)
        items.append(
            {"id": str(user.id), "tags": [_tag(tag) for tag in sorted(user.tags, key=lambda t: t.id)]}
        )
    return success({"items": items})


@router.put("/users/{user_id}/tags", response_model=Envelope[IdTags], summary="替换用户标签")
async def set_user_tags(
    user_id: str,
    body: SetUserTagsRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """用传入的 tag_ids 整表替换该用户标签。"""
    user = await get_user(session, user_id)
    unique_ids = list(dict.fromkeys(body.tag_ids))
    user.tags = await _tags_by_ids(session, unique_ids) if unique_ids else []
    await session.commit()
    user = await get_user(session, user_id)
    return success({"id": str(user.id), "tags": [_tag(tag) for tag in sorted(user.tags, key=lambda t: t.id)]})


@router.delete("/users/{user_id}/tags/{tag_id}", response_model=Envelope[IdTags], summary="去掉一个用户标签")
async def remove_user_tag(
    user_id: str,
    tag_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """从用户上移除单个标签；标签本身不删。"""
    user = await get_user(session, user_id)
    user.tags = [tag for tag in user.tags if str(tag.id) != str(tag_id)]
    await session.commit()
    user = await get_user(session, user_id)
    return success({"id": str(user.id), "tags": [_tag(tag) for tag in sorted(user.tags, key=lambda t: t.id)]})
