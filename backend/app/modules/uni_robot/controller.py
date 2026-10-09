"""全域漫剧机器人 HTTP。按推广链接和按剧条件都要漫剧机器人菜单。规则没有归属人，有菜单即可看全部。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.system_admin import require_menu
from app.modules.uni_robot.port import UniRobotCatalog
from app.modules.uni_template.catalog import DatabaseUniRobotCatalog
from app.modules.uni_robot.schema import (
    DramaDeleted,
    DramaRuleItem,
    DramaRuleQuery,
    DramaRuleWrite,
    DramaScheduleWrite,
    DramaSwitchWrite,
    LinkDeleted,
    LinkRuleItem,
    LinkRuleQuery,
    LinkRuleWrite,
    LinkScheduleWrite,
    LinkSwitchWrite,
)
from app.modules.uni_robot.service import (
    create_drama_rule,
    create_link_rule,
    delete_drama_rule,
    delete_link_rule,
    drama_item,
    link_item,
    list_drama_rules,
    list_link_rules,
    read_drama_rule,
    read_link_rule,
    set_drama_enabled,
    set_drama_schedule,
    set_link_enabled,
    set_link_schedule,
    update_drama_rule,
    update_link_rule,
)

router = APIRouter(
    prefix="/api/v1/uni-robot",
    tags=["uni-robot"],
    dependencies=[Depends(require_menu("80"))],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_catalog(session: SessionDep) -> UniRobotCatalog:
    """模板查未删除的全域模板。剧场平台没有来源时拒绝。"""
    return DatabaseUniRobotCatalog(session)


CatalogDep = Annotated[UniRobotCatalog, Depends(get_catalog)]


@router.get(
    "/promotion-link-rules",
    response_model=Envelope[PageData[LinkRuleItem]],
    summary="分页查询按推广链接规则",
)
async def get_promotion_link_rules(
    session: SessionDep,
    query: Annotated[LinkRuleQuery, Query()],
) -> dict[str, Any]:
    """列出未删除的按推广链接规则。不跑机器人。"""
    return success(await list_link_rules(session, query))


@router.get(
    "/promotion-link-rules/{rule_id}",
    response_model=Envelope[LinkRuleItem],
    summary="查询一条按推广链接规则",
)
async def get_promotion_link_rule(rule_id: int, session: SessionDep) -> dict[str, Any]:
    """取一条未删除的按推广链接规则。按剧条件不在这条路径上。"""
    return success(await read_link_rule(session, rule_id))


@router.post(
    "/promotion-link-rules",
    response_model=Envelope[LinkRuleItem],
    summary="新增按推广链接规则",
)
async def post_promotion_link_rule(
    body: LinkRuleWrite, session: SessionDep, catalog: CatalogDep
) -> dict[str, Any]:
    """保存一条按推广链接规则。模板和平台经目录端口确认，条件列留空。不创建任务。"""
    return success(link_item(await create_link_rule(session, catalog, body)))


@router.put(
    "/promotion-link-rules/{rule_id}",
    response_model=Envelope[LinkRuleItem],
    summary="保存按推广链接规则",
)
async def put_promotion_link_rule(
    rule_id: int, body: LinkRuleWrite, session: SessionDep, catalog: CatalogDep
) -> dict[str, Any]:
    """整表保存。条件列保持为空。不到点执行。"""
    return success(await update_link_rule(session, catalog, rule_id, body))


@router.delete(
    "/promotion-link-rules/{rule_id}",
    response_model=Envelope[LinkDeleted],
    summary="删除按推广链接规则",
)
async def remove_promotion_link_rule(rule_id: int, session: SessionDep) -> dict[str, Any]:
    """软删一条按推广链接规则。"""
    return success(await delete_link_rule(session, rule_id))


@router.patch(
    "/promotion-link-rules/{rule_id}/switch",
    response_model=Envelope[LinkRuleItem],
    summary="开关按推广链接规则",
)
async def patch_promotion_link_rule_switch(
    rule_id: int, body: LinkSwitchWrite, session: SessionDep
) -> dict[str, Any]:
    """只改开关，不改每天的时分，也不创建任务。"""
    return success(await set_link_enabled(session, rule_id, body))


@router.patch(
    "/promotion-link-rules/{rule_id}/schedule",
    response_model=Envelope[LinkRuleItem],
    summary="改按推广链接规则的每天时分",
)
async def patch_promotion_link_rule_schedule(
    rule_id: int, body: LinkScheduleWrite, session: SessionDep
) -> dict[str, Any]:
    """只改每天触发的小时和分钟。不到点执行。"""
    return success(await set_link_schedule(session, rule_id, body))


@router.get(
    "/drama-rules",
    response_model=Envelope[PageData[DramaRuleItem]],
    summary="分页查询按剧条件规则",
)
async def get_drama_rules(
    session: SessionDep,
    query: Annotated[DramaRuleQuery, Query()],
) -> dict[str, Any]:
    """列出未删除的按剧条件规则。不跑机器人。"""
    return success(await list_drama_rules(session, query))


@router.get(
    "/drama-rules/{rule_id}",
    response_model=Envelope[DramaRuleItem],
    summary="查询一条按剧条件规则",
)
async def get_drama_rule(rule_id: int, session: SessionDep) -> dict[str, Any]:
    """取一条未删除的按剧条件规则。按推广链接不在这条路径上。"""
    return success(await read_drama_rule(session, rule_id))


@router.post(
    "/drama-rules",
    response_model=Envelope[DramaRuleItem],
    summary="新增按剧条件规则",
)
async def post_drama_rule(
    body: DramaRuleWrite, session: SessionDep, catalog: CatalogDep
) -> dict[str, Any]:
    """保存一条按剧条件规则。模板和平台经目录端口确认。不创建任务。"""
    return success(drama_item(await create_drama_rule(session, catalog, body)))


@router.put(
    "/drama-rules/{rule_id}",
    response_model=Envelope[DramaRuleItem],
    summary="保存按剧条件规则",
)
async def put_drama_rule(
    rule_id: int, body: DramaRuleWrite, session: SessionDep, catalog: CatalogDep
) -> dict[str, Any]:
    """整表保存。统计时间和两个区间一并改写。不到点执行。"""
    return success(await update_drama_rule(session, catalog, rule_id, body))


@router.delete(
    "/drama-rules/{rule_id}",
    response_model=Envelope[DramaDeleted],
    summary="删除按剧条件规则",
)
async def remove_drama_rule(rule_id: int, session: SessionDep) -> dict[str, Any]:
    """软删一条按剧条件规则。"""
    return success(await delete_drama_rule(session, rule_id))


@router.patch(
    "/drama-rules/{rule_id}/switch",
    response_model=Envelope[DramaRuleItem],
    summary="开关按剧条件规则",
)
async def patch_drama_rule_switch(
    rule_id: int, body: DramaSwitchWrite, session: SessionDep
) -> dict[str, Any]:
    """只改开关，不改每天的时分，也不创建任务。"""
    return success(await set_drama_enabled(session, rule_id, body))


@router.patch(
    "/drama-rules/{rule_id}/schedule",
    response_model=Envelope[DramaRuleItem],
    summary="改按剧条件规则的每天时分",
)
async def patch_drama_rule_schedule(
    rule_id: int, body: DramaScheduleWrite, session: SessionDep
) -> dict[str, Any]:
    """只改每天触发的小时和分钟。不到点执行。"""
    return success(await set_drama_schedule(session, rule_id, body))
