"""全域漫剧机器人规则的表查询。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.uni_robot.model import UniRobotRule


def name_taken_stmt(rule_kind: str, name: str, exclude_id: int | None) -> Select[tuple[int]]:
    """同一类型下，未删除的规则是否已有这个名字。"""
    stmt = select(UniRobotRule.id).where(
        UniRobotRule.rule_kind == rule_kind,
        UniRobotRule.name == name,
        UniRobotRule.is_deleted == 0,
    )
    if exclude_id is not None:
        stmt = stmt.where(UniRobotRule.id != exclude_id)
    return stmt.limit(1)


async def name_taken(session: AsyncSession, rule_kind: str, name: str, exclude_id: int | None) -> bool:
    """同一类型下未删除的规则已占用这个名字。"""
    result = await session.execute(name_taken_stmt(rule_kind, name, exclude_id))
    return result.scalar_one_or_none() is not None


async def get_rule(session: AsyncSession, rule_id: int) -> UniRobotRule | None:
    """取一条未删除的规则。"""
    result = await session.execute(
        select(UniRobotRule).where(UniRobotRule.id == rule_id, UniRobotRule.is_deleted == 0)
    )
    return result.scalar_one_or_none()
