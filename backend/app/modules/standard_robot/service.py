"""保存标准端原生机器人。免费模板必须是 IAA，付费模板必须是 IAP。

列表、修改、删除、开关都不创建投放任务。到点仍由既有循环 mock 提交。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.standard_delivery.crud import get_template_row
from app.modules.standard_robot.model import StandardNativeRobotRule
from app.modules.standard_robot.schema import RobotQuery, RobotWrite


def _bound(value: Decimal | None, places: str) -> str | None:
    """区间端点按固定小数位输出。空保持空。"""
    if value is None:
        return None
    return format(Decimal(value).quantize(Decimal(places)), "f")


def robot_item(row: StandardNativeRobotRule) -> dict[str, Any]:
    """把规则行收成出参。收费模式由菜单决定，这里只读出来。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "charge_mode": row.charge_mode,
        "rule_kind": row.rule_kind,
        "schedule_kind": row.schedule_kind,
        "schedule_hour": row.schedule_hour,
        "schedule_minute": row.schedule_minute,
        "template_id": str(row.template_id),
        "pitcher_user_id": str(row.pitcher_user_id),
        "platform_id": None if row.platform_id is None else str(row.platform_id),
        "accounts_per_series": row.accounts_per_series,
        "max_videos_per_series": row.max_videos_per_series,
        "stat_span": row.stat_span,
        "cost_min": _bound(row.cost_min, "0.01"),
        "cost_max": _bound(row.cost_max, "0.01"),
        "recovery_min": _bound(row.recovery_min, "0.0001"),
        "recovery_max": _bound(row.recovery_max, "0.0001"),
        "is_enabled": row.is_enabled,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def robot_filters(query: RobotQuery, user_id: int, charge_mode: str) -> list[ColumnElement[bool]]:
    """只列当前投手、该收费模式、未删除的规则。名称模糊且转义 % 和 _。"""
    filters: list[ColumnElement[bool]] = [
        StandardNativeRobotRule.is_deleted == 0,
        StandardNativeRobotRule.charge_mode == charge_mode,
        StandardNativeRobotRule.pitcher_user_id == user_id,
    ]
    name = (query.name or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(StandardNativeRobotRule.name.ilike(f"%{escaped}%", escape="\\"))
    if query.is_enabled is not None:
        filters.append(StandardNativeRobotRule.is_enabled == query.is_enabled)
    return filters


async def _checked_template(session: AsyncSession, template_id: int, charge_mode: str) -> int:
    """模板须存在，且收费模式和菜单一致。"""
    found = await get_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, _subject = found
    if template.charge_mode != charge_mode:
        expected = "免费端原生模板" if charge_mode == "IAA" else "付费端原生模板"
        raise ApiError(400, f"机器人须使用{expected}")
    return int(template.id)


def _check_shape(body: RobotWrite) -> None:
    """推广链要剧场；每天执行要小时。"""
    if body.rule_kind == "promotion_link" and body.platform_id is None:
        raise ApiError(400, "推广链规则需要剧场平台")
    if body.schedule_kind == "period" and body.schedule_hour is None:
        raise ApiError(400, "周期执行需要小时")


def _apply(row: StandardNativeRobotRule, body: RobotWrite, template_id: int) -> None:
    """整表写入可改字段。收费模式和所属投手不动。"""
    row.name = body.name
    row.rule_kind = body.rule_kind
    row.schedule_kind = body.schedule_kind
    row.schedule_hour = body.schedule_hour
    row.schedule_minute = body.schedule_minute
    row.template_id = template_id
    row.platform_id = body.platform_id
    row.accounts_per_series = body.accounts_per_series
    row.max_videos_per_series = body.max_videos_per_series
    row.stat_span = body.stat_span
    row.cost_min = body.cost_min
    row.cost_max = body.cost_max
    row.recovery_min = body.recovery_min
    row.recovery_max = body.recovery_max
    row.is_enabled = body.is_enabled
    row.updated_date = beijing_now()


async def _own(
    session: AsyncSession, rule_id: int, user_id: int, charge_mode: str
) -> StandardNativeRobotRule:
    """取当前投手在该菜单下的一条未删除规则。别人的、另一种收费模式的，都当不存在。"""
    row = await session.get(StandardNativeRobotRule, rule_id)
    if (
        row is None
        or int(row.is_deleted or 0) != 0
        or int(row.pitcher_user_id) != user_id
        or row.charge_mode != charge_mode
    ):
        raise ApiError(404, "规则不存在")
    return row


async def create_robot_rule(
    session: AsyncSession, body: RobotWrite, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """charge_mode 由菜单决定：76 是 IAA，77 是 IAP。不在这里提交投放。"""
    _check_shape(body)
    template_id = await _checked_template(session, body.template_id, charge_mode)
    now = beijing_now()
    row = StandardNativeRobotRule(
        name=body.name,
        charge_mode=charge_mode,
        rule_kind=body.rule_kind,
        schedule_kind=body.schedule_kind,
        schedule_hour=body.schedule_hour,
        schedule_minute=body.schedule_minute,
        template_id=template_id,
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
    row.created_date = now
    row.updated_date = now
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return robot_item(row)


async def list_robot_rules(
    session: AsyncSession, query: RobotQuery, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """分页列出当前投手的规则。不跑机器人。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = robot_filters(query, user_id, charge_mode)
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(StandardNativeRobotRule).where(*filters)
            )
        ).scalar_one()
    )
    rows = list(
        (
            await session.scalars(
                select(StandardNativeRobotRule)
                .where(*filters)
                .order_by(StandardNativeRobotRule.created_date.desc(), StandardNativeRobotRule.id.desc())
                .offset(params.offset)
                .limit(params.page_size)
            )
        ).all()
    )
    return page_data([robot_item(row) for row in rows], total, params)


async def update_robot_rule(
    session: AsyncSession, rule_id: int, body: RobotWrite, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """整表保存自己的规则。不到点执行。"""
    row = await _own(session, rule_id, user_id, charge_mode)
    _check_shape(body)
    template_id = await _checked_template(session, body.template_id, charge_mode)
    _apply(row, body, template_id)
    await session.commit()
    await session.refresh(row)
    return robot_item(row)


async def delete_robot_rule(
    session: AsyncSession, rule_id: int, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """软删自己的规则。"""
    row = await _own(session, rule_id, user_id, charge_mode)
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


async def set_robot_enabled(
    session: AsyncSession, rule_id: int, is_enabled: bool, user_id: int, charge_mode: str
) -> dict[str, Any]:
    """只改开关。关掉后到点循环会跳过。这里不提交投放。"""
    row = await _own(session, rule_id, user_id, charge_mode)
    row.is_enabled = is_enabled
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return robot_item(row)
