"""全域漫剧机器人规则的表查询。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.uni_robot.model import RuleKind, UniRobotRule


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
    """取一条未删除的规则。两种类型都算。"""
    result = await session.execute(
        select(UniRobotRule).where(UniRobotRule.id == rule_id, UniRobotRule.is_deleted == 0)
    )
    return result.scalar_one_or_none()


def get_link_rule_stmt(rule_id: int) -> Select[tuple[UniRobotRule]]:
    """一条未删除的按推广链接规则。按剧条件不在这里。"""
    return select(UniRobotRule).where(
        UniRobotRule.id == rule_id,
        UniRobotRule.rule_kind == RuleKind.PROMOTION_LINK,
        UniRobotRule.is_deleted == 0,
    )


async def get_link_rule(session: AsyncSession, rule_id: int) -> UniRobotRule | None:
    """取一条未删除的按推广链接规则。"""
    result = await session.execute(get_link_rule_stmt(rule_id))
    return result.scalar_one_or_none()


def link_page_stmt(
    filters: list[ColumnElement[bool]], *, offset: int, limit: int
) -> Select[tuple[UniRobotRule]]:
    """按创建时间倒序的按推广链接分页查询。"""
    return (
        select(UniRobotRule)
        .where(*filters)
        .order_by(UniRobotRule.created_date.desc(), UniRobotRule.id.desc())
        .offset(offset)
        .limit(limit)
    )


async def page_link_rules(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[UniRobotRule], int]:
    """按创建时间倒序分页。返回 (行, 总数)。"""
    total = int(
        (await session.execute(select(func.count()).select_from(UniRobotRule).where(*filters))).scalar_one()
    )
    result = await session.execute(link_page_stmt(filters, offset=offset, limit=limit))
    return list(result.scalars().all()), total


def get_drama_rule_stmt(rule_id: int) -> Select[tuple[UniRobotRule]]:
    """一条未删除的按剧条件规则。按推广链接不在这里。"""
    return select(UniRobotRule).where(
        UniRobotRule.id == rule_id,
        UniRobotRule.rule_kind == RuleKind.DRAMA_CONDITION,
        UniRobotRule.is_deleted == 0,
    )


async def get_drama_rule(session: AsyncSession, rule_id: int) -> UniRobotRule | None:
    """取一条未删除的按剧条件规则。"""
    result = await session.execute(get_drama_rule_stmt(rule_id))
    return result.scalar_one_or_none()


def drama_page_stmt(
    filters: list[ColumnElement[bool]], *, offset: int, limit: int
) -> Select[tuple[UniRobotRule]]:
    """按创建时间倒序的按剧条件分页查询。类型由 filters 限定。"""
    return link_page_stmt(filters, offset=offset, limit=limit)


async def page_drama_rules(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[UniRobotRule], int]:
    """按创建时间倒序分页。返回 (行, 总数)。"""
    return await page_link_rules(session, filters, offset=offset, limit=limit)
