"""全域漫剧机器人规则的保存和开关。

模板 id、平台 id 只从目录端口拿回来再写入。这里不查剧场表，也不查模板表。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.modules.uni_robot.crud import get_rule, name_taken
from app.modules.uni_robot.model import RuleKind, UniRobotRule
from app.modules.uni_robot.port import UniRobotCatalog
from app.modules.uni_robot.schema import DramaRuleWrite, LinkRuleWrite


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
    """只改开关。"""
    row = await get_rule(session, rule_id)
    if row is None:
        raise ApiError(404, "规则不存在")
    row.is_enabled = is_enabled
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return row
