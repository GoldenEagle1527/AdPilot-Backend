"""全域漫剧机器人规则的保存、列表和开关。

模板 id、平台 id 只从目录端口拿回来再写入。这里不查剧场表，也不查模板表。
按剧条件只有保存函数，这一轮不从 HTTP 进来。这里不创建任务，也不到点执行。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.uni_robot.crud import get_link_rule, get_rule, name_taken, page_link_rules
from app.modules.uni_robot.model import RuleKind, UniRobotRule
from app.modules.uni_robot.port import UniRobotCatalog
from app.modules.uni_robot.schema import (
    DramaRuleWrite,
    LinkRuleQuery,
    LinkRuleWrite,
    LinkScheduleWrite,
    LinkSwitchWrite,
)


async def _catalog_ids(catalog: UniRobotCatalog, template_id: int, platform_id: int) -> tuple[int, int]:
    """向目录要回可保存的模板 id 和平台 id。"""
    stored_template_id = await catalog.require_template(template_id)
    stored_platform_id = await catalog.require_platform(platform_id)
    return stored_template_id, stored_platform_id


async def create_link_rule(
    session: AsyncSession, catalog: UniRobotCatalog, body: LinkRuleWrite
) -> UniRobotRule:
    """按推广链接新增一条规则。条件列留空。"""
    template_id, platform_id = await _catalog_ids(catalog, body.template_id, body.platform_id)
    if await name_taken(session, RuleKind.PROMOTION_LINK, body.name, None):
        raise ApiError(409, "规则名称已存在")
    row = UniRobotRule(
        rule_kind=RuleKind.PROMOTION_LINK,
        name=body.name,
        template_id=template_id,
        platform_id=platform_id,
        max_videos_per_series=body.max_videos_per_series,
        schedule_hour=body.schedule_hour,
        schedule_minute=body.schedule_minute,
        is_enabled=body.is_enabled,
        stat_span=None,
        cost_min=None,
        cost_max=None,
        recovery_min=None,
        recovery_max=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def create_drama_rule(
    session: AsyncSession, catalog: UniRobotCatalog, body: DramaRuleWrite
) -> UniRobotRule:
    """按剧条件新增一条规则。统计时间、消耗区间、回收率区间一并写入。"""
    template_id, platform_id = await _catalog_ids(catalog, body.template_id, body.platform_id)
    if await name_taken(session, RuleKind.DRAMA_CONDITION, body.name, None):
        raise ApiError(409, "规则名称已存在")
    row = UniRobotRule(
        rule_kind=RuleKind.DRAMA_CONDITION,
        name=body.name,
        template_id=template_id,
        platform_id=platform_id,
        max_videos_per_series=body.max_videos_per_series,
        schedule_hour=body.schedule_hour,
        schedule_minute=body.schedule_minute,
        is_enabled=body.is_enabled,
        stat_span=body.stat_span,
        cost_min=body.cost_min,
        cost_max=body.cost_max,
        recovery_min=body.recovery_min,
        recovery_max=body.recovery_max,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def set_rule_enabled(session: AsyncSession, rule_id: int, is_enabled: bool) -> UniRobotRule:
    """只改开关。两种类型都能改，不经过 HTTP。"""
    row = await get_rule(session, rule_id)
    if row is None:
        raise ApiError(404, "规则不存在")
    row.is_enabled = is_enabled
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return row


def link_item(row: UniRobotRule) -> dict[str, Any]:
    """把按推广链接规则收成出参。不带剧条件列。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "template_id": str(row.template_id),
        "platform_id": str(row.platform_id),
        "max_videos_per_series": row.max_videos_per_series,
        "schedule_hour": row.schedule_hour,
        "schedule_minute": row.schedule_minute,
        "is_enabled": row.is_enabled,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def link_filters(query: LinkRuleQuery) -> list[ColumnElement[bool]]:
    """只列出未删除的按推广链接规则。名称模糊且转义 % 和 _。"""
    filters: list[ColumnElement[bool]] = [
        UniRobotRule.rule_kind == RuleKind.PROMOTION_LINK,
        UniRobotRule.is_deleted == 0,
    ]
    name = (query.name or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(UniRobotRule.name.ilike(f"%{escaped}%", escape="\\"))
    if query.is_enabled is not None:
        filters.append(UniRobotRule.is_enabled == query.is_enabled)
    return filters


async def _require_link(session: AsyncSession, rule_id: int) -> UniRobotRule:
    """取一条还在的按推广链接规则。按剧条件、已删、没有，都当不存在。"""
    row = await get_link_rule(session, rule_id)
    if row is None or row.rule_kind != RuleKind.PROMOTION_LINK or int(row.is_deleted or 0) != 0:
        raise ApiError(404, "规则不存在")
    return row


async def list_link_rules(session: AsyncSession, query: LinkRuleQuery) -> dict[str, Any]:
    """分页列出按推广链接规则。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_link_rules(
        session, link_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([link_item(row) for row in rows], total, params)


async def read_link_rule(session: AsyncSession, rule_id: int) -> dict[str, Any]:
    """取一条按推广链接规则。"""
    return link_item(await _require_link(session, rule_id))


async def update_link_rule(
    session: AsyncSession, catalog: UniRobotCatalog, rule_id: int, body: LinkRuleWrite
) -> dict[str, Any]:
    """整表保存一条按推广链接规则。条件列保持为空。"""
    row = await _require_link(session, rule_id)
    template_id, platform_id = await _catalog_ids(catalog, body.template_id, body.platform_id)
    if await name_taken(session, RuleKind.PROMOTION_LINK, body.name, row.id):
        raise ApiError(409, "规则名称已存在")
    row.name = body.name
    row.template_id = template_id
    row.platform_id = platform_id
    row.max_videos_per_series = body.max_videos_per_series
    row.schedule_hour = body.schedule_hour
    row.schedule_minute = body.schedule_minute
    row.is_enabled = body.is_enabled
    row.stat_span = None
    row.cost_min = None
    row.cost_max = None
    row.recovery_min = None
    row.recovery_max = None
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return link_item(row)


async def delete_link_rule(session: AsyncSession, rule_id: int) -> dict[str, Any]:
    """软删一条按推广链接规则。"""
    row = await _require_link(session, rule_id)
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


async def set_link_enabled(session: AsyncSession, rule_id: int, body: LinkSwitchWrite) -> dict[str, Any]:
    """只改按推广链接规则的开关。"""
    row = await _require_link(session, rule_id)
    row.is_enabled = body.is_enabled
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return link_item(row)


async def set_link_schedule(
    session: AsyncSession, rule_id: int, body: LinkScheduleWrite
) -> dict[str, Any]:
    """只改按推广链接规则每天的时分。"""
    row = await _require_link(session, rule_id)
    row.schedule_hour = body.schedule_hour
    row.schedule_minute = body.schedule_minute
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return link_item(row)
