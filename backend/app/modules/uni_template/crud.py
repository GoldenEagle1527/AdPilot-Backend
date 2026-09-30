"""全域模板和投手抖音号分配的表查询。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.account.model import DeliverySubject, DouyinAccount, DouyinPitcher
from app.modules.standard_delivery.model import DeliveryTemplate, TemplateMode
from app.modules.uni_template.model import DeliveryTemplateDouyin

TemplateRow = tuple[DeliveryTemplate, DeliverySubject]
DouyinLink = tuple[int, DouyinAccount]


def alive_uni_template_id_stmt(template_id: int) -> Select[tuple[int]]:
    """未删除的全域模板 id。标准模板不在这里。"""
    return select(DeliveryTemplate.id).where(
        DeliveryTemplate.id == template_id,
        DeliveryTemplate.delivery_mode == TemplateMode.UNI,
        DeliveryTemplate.is_deleted == 0,
    )


def uni_template_by_id_stmt(template_id: int) -> Select[TemplateRow]:
    """一条未删除的全域模板，连带主体。"""
    return (
        select(DeliveryTemplate, DeliverySubject)
        .join(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .where(
            DeliveryTemplate.id == template_id,
            DeliveryTemplate.delivery_mode == TemplateMode.UNI,
            DeliveryTemplate.is_deleted == 0,
        )
    )


async def get_uni_template_row(session: AsyncSession, template_id: int) -> TemplateRow | None:
    """取未删除的全域模板，连带主体。"""
    result = await session.execute(uni_template_by_id_stmt(template_id))
    return result.one_or_none()


def uni_name_taken_stmt(charge_mode: str, name: str, exclude_id: int | None) -> Select[tuple[int]]:
    """同一变现模式下，未删除的全域模板是否已有这个名字。标准同名不算。"""
    stmt = select(DeliveryTemplate.id).where(
        DeliveryTemplate.delivery_mode == TemplateMode.UNI,
        DeliveryTemplate.charge_mode == charge_mode,
        DeliveryTemplate.name == name,
        DeliveryTemplate.is_deleted == 0,
    )
    if exclude_id is not None:
        stmt = stmt.where(DeliveryTemplate.id != exclude_id)
    return stmt.limit(1)


async def uni_name_taken(
    session: AsyncSession, charge_mode: str, name: str, exclude_id: int | None
) -> bool:
    """同一变现模式下未删除的全域模板是否已有这个名字。"""
    result = await session.execute(uni_name_taken_stmt(charge_mode, name, exclude_id))
    return result.scalar_one_or_none() is not None


def _joined():
    """列表和计数共用的主体连接。"""
    return select(DeliveryTemplate, DeliverySubject).join(
        DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id
    )


async def page_uni_templates(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[TemplateRow], int]:
    """按创建时间倒序分页全域模板。"""
    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(DeliveryTemplate)
                .join(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
                .where(*filters)
            )
        ).scalar_one()
    )
    result = await session.execute(
        _joined()
        .where(*filters)
        .order_by(DeliveryTemplate.created_date.desc(), DeliveryTemplate.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.all()), total


def pitcher_douyin_stmt(template_ids: list[int], user_id: int) -> Select[DouyinLink]:
    """当前投手挂在这些模板上的未删除全域号。"""
    return (
        select(DeliveryTemplateDouyin.template_id, DouyinAccount)
        .join(DouyinAccount, DouyinAccount.id == DeliveryTemplateDouyin.douyin_account_id)
        .where(
            DeliveryTemplateDouyin.template_id.in_(template_ids),
            DeliveryTemplateDouyin.user_id == user_id,
            DouyinAccount.is_deleted == 0,
            DouyinAccount.delivery_mode == "uni",
        )
        .order_by(DeliveryTemplateDouyin.id)
    )


async def pitcher_douyin_links(
    session: AsyncSession, template_ids: list[int], user_id: int
) -> list[DouyinLink]:
    """当前投手在这些模板上的抖音号。没有模板 id 时不查。"""
    if not template_ids:
        return []
    result = await session.execute(pitcher_douyin_stmt(template_ids, user_id))
    return list(result.all())


def douyin_by_ids_stmt(account_ids: list[int]) -> Select[tuple[DouyinAccount]]:
    """按 id 取未删除的抖音号，不限投放模式，好区分标准号和缺失。"""
    return select(DouyinAccount).where(
        DouyinAccount.id.in_(account_ids),
        DouyinAccount.is_deleted == 0,
    )


async def douyin_by_ids(session: AsyncSession, account_ids: list[int]) -> list[DouyinAccount]:
    """取未删除的抖音号。"""
    if not account_ids:
        return []
    result = await session.execute(douyin_by_ids_stmt(account_ids))
    return list(result.scalars().all())


def pitcher_owned_stmt(account_ids: list[int], user_id: int) -> Select[tuple[int]]:
    """这些号里，已经分给当前投手的。"""
    return select(DouyinPitcher.douyin_account_id).where(
        DouyinPitcher.user_id == user_id,
        DouyinPitcher.douyin_account_id.in_(account_ids),
    )


async def pitcher_owned_ids(session: AsyncSession, account_ids: list[int], user_id: int) -> set[int]:
    """当前投手名下的号。"""
    if not account_ids:
        return set()
    result = await session.execute(pitcher_owned_stmt(account_ids, user_id))
    return set(result.scalars().all())


async def replace_pitcher_douyin(
    session: AsyncSession, template_id: int, user_id: int, account_ids: list[int]
) -> None:
    """用这批号换掉当前投手在该模板上的分配。不动别人的行。"""
    await session.execute(
        delete(DeliveryTemplateDouyin).where(
            DeliveryTemplateDouyin.template_id == template_id,
            DeliveryTemplateDouyin.user_id == user_id,
        )
    )
    for account_id in account_ids:
        session.add(
            DeliveryTemplateDouyin(
                template_id=template_id,
                user_id=user_id,
                douyin_account_id=account_id,
            )
        )
