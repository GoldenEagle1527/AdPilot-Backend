"""保存标准端原生机器人。免费模板必须是 IAA，付费模板必须是 IAP。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.standard_delivery.crud import get_template_row
from app.modules.standard_robot.model import StandardNativeRobotRule
from app.modules.standard_robot.schema import RobotWrite


async def create_robot_rule(
    session: AsyncSession, body: RobotWrite, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """charge_mode 由菜单决定：76 是 IAA，77 是 IAP。"""
    found = await get_template_row(session, body.template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, _subject = found
    if template.charge_mode != charge_mode:
        expected = "免费端原生模板" if charge_mode == "IAA" else "付费端原生模板"
        raise ApiError(400, f"机器人须使用{expected}")
    if body.rule_kind == "promotion_link" and body.platform_id is None:
        raise ApiError(400, "推广链规则需要剧场平台")
    if body.schedule_kind == "period" and body.schedule_hour is None:
        raise ApiError(400, "周期执行需要小时")
    row = StandardNativeRobotRule(
        name=body.name,
        charge_mode=charge_mode,
        rule_kind=body.rule_kind,
        schedule_kind=body.schedule_kind,
        schedule_hour=body.schedule_hour,
        schedule_minute=body.schedule_minute,
        template_id=template.id,
        pitcher_user_id=user_id,
        platform_id=body.platform_id,
        accounts_per_series=body.accounts_per_series,
        max_videos_per_series=body.max_videos_per_series,
        stat_span=body.stat_span,
        cost_min=body.cost_min,
        cost_max=body.cost_max,
        recovery_min=body.recovery_min,
        recovery_max=body.recovery_max,
        is_enabled=body.is_enabled,
        last_ran_at=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return {
        "id": str(row.id),
        "name": row.name,
        "charge_mode": row.charge_mode,
        "rule_kind": row.rule_kind,
        "schedule_kind": row.schedule_kind,
        "template_id": str(row.template_id),
        "pitcher_user_id": str(row.pitcher_user_id),
        "is_enabled": row.is_enabled,
    }
