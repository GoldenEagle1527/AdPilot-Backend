"""报表读库。只读快照表和中台任务表，不调巨量。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.account.model import DeliverySubject, OeDeliveryReport, OeUniProjectReport
from app.modules.material.model import ManhuaSeries
from app.modules.report.service import (
    MANHUA_BASE,
    UNI_MONEY,
    ManhuaFact,
    ProjectLink,
    PromotionLink,
    UniFact,
    parse_publish_date,
)
from app.modules.standard_delivery.model import (
    DeliveryTaskDraft,
    DeliveryTaskProject,
    DeliveryTaskPromotion,
    DeliveryTemplate,
)
from app.modules.system_admin.domain.models import Department, User
from app.modules.theater.model import TheaterApp, TheaterPlatform
from app.modules.uni_native_task.model import UniNativeTask, UniNativeTaskAccount

_STYLE_NAMES = {"live_action": "真人剧", "manhua": "漫剧"}
_BID_TYPE_NAMES = {"NO_BID": "最大转化", "CUSTOM": "稳定成本"}
_STORED_UNI = ("running", "done")


def _hour_range(start: date, end: date) -> tuple[str, str]:
    return f"{start.isoformat()} 00:00:00", f"{end.isoformat()} 23:59:59"


async def theater_lookup(session: AsyncSession) -> dict[str, tuple[str, str]]:
    """剧场应用名 → （剧目类型，渠道名）。主体只存剧场名，按名称对上应用。"""
    rows = await session.execute(
        select(TheaterApp.name, TheaterApp.style, TheaterPlatform.name)
        .join(TheaterPlatform, TheaterPlatform.id == TheaterApp.platform_id)
        .where(TheaterApp.is_deleted == 0)
        .order_by(TheaterApp.id)
    )
    lookup: dict[str, tuple[str, str]] = {}
    for name, style, platform in rows.all():
        lookup.setdefault(str(name), (_STYLE_NAMES.get(str(style), ""), str(platform)))
    return lookup


async def standard_links(
    session: AsyncSession,
    *,
    charge_mode: str | None = None,
    project_ids: Iterable[int] | None = None,
    series_id: int | None = None,
) -> dict[int, ProjectLink]:
    """标准投放提交成功的巨量项目，按 delivery_task_project.ocean_project_id 回到剧、投手和部门。"""
    filters: list[Any] = [DeliveryTaskProject.is_deleted == 0, DeliveryTaskDraft.is_deleted == 0]
    if charge_mode is not None:
        filters.append(DeliveryTaskDraft.charge_mode == charge_mode)
    if project_ids is not None:
        ids = list({int(item) for item in project_ids})
        if not ids:
            return {}
        filters.append(DeliveryTaskProject.ocean_project_id.in_(ids))
    if series_id is not None:
        filters.append(DeliveryTaskDraft.series_id == series_id)
    rows = await session.execute(
        select(
            DeliveryTaskProject.ocean_project_id,
            DeliveryTaskProject.bid_panel,
            DeliveryTaskProject.created_date,
            DeliveryTaskDraft.series_id,
            DeliveryTaskDraft.charge_mode,
            DeliveryTaskDraft.pitcher_user_id,
            DeliveryTaskDraft.project_budget,
            DeliveryTemplate.project_budget,
            DeliveryTemplate.roi_goal,
            DeliveryTemplate.bid_type,
            DeliverySubject.theater_name,
            ManhuaSeries.book_name,
            ManhuaSeries.publish_time,
            User.nickname,
            User.department_id,
            Department.name,
        )
        .join(DeliveryTaskDraft, DeliveryTaskDraft.id == DeliveryTaskProject.task_id)
        .join(DeliveryTemplate, DeliveryTemplate.id == DeliveryTaskDraft.template_id)
        .outerjoin(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .join(ManhuaSeries, ManhuaSeries.id == DeliveryTaskDraft.series_id)
        .join(User, User.id == DeliveryTaskDraft.pitcher_user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(*filters)
    )
    theaters = await theater_lookup(session)
    links: dict[int, ProjectLink] = {}
    for (
        project_id,
        bid_panel,
        created_at,
        series,
        mode,
        pitcher_id,
        draft_budget,
        template_budget,
        roi_goal,
        bid_type,
        theater_name,
        book_name,
        publish_time,
        nickname,
        department_id,
        department_name,
    ) in rows.all():
        drama_type, channel = theaters.get(str(theater_name or ""), ("", ""))
        links[int(project_id)] = ProjectLink(
            project_id=int(project_id),
            series_id=int(series),
            book_name=str(book_name or ""),
            pitcher_id=int(pitcher_id),
            pitcher_name=str(nickname or ""),
            department_id=None if department_id is None else int(department_id),
            department_name=str(department_name or ""),
            charge_mode=str(mode),
            bid_panel=str(bid_panel or ""),
            bid_type=_BID_TYPE_NAMES.get(str(bid_type or ""), ""),
            drama_type=drama_type,
            channel=channel,
            publish_date=parse_publish_date(publish_time),
            created_at=created_at,
            project_budget=draft_budget if draft_budget is not None else template_budget,
            roi_goal=roi_goal,
        )
    return links


async def standard_promotions(
    session: AsyncSession,
    promotion_ids: Iterable[int] | None = None,
) -> dict[int, PromotionLink]:
    """中台建出的广告 → 所属巨量项目。"""
    filters: list[Any] = [DeliveryTaskPromotion.is_deleted == 0, DeliveryTaskProject.is_deleted == 0]
    if promotion_ids is not None:
        ids = list({int(item) for item in promotion_ids})
        if not ids:
            return {}
        filters.append(DeliveryTaskPromotion.ocean_promotion_id.in_(ids))
    rows = await session.execute(
        select(
            DeliveryTaskPromotion.ocean_promotion_id,
            DeliveryTaskProject.ocean_project_id,
            DeliveryTaskPromotion.created_date,
        )
        .join(DeliveryTaskProject, DeliveryTaskProject.id == DeliveryTaskPromotion.task_project_id)
        .where(*filters)
    )
    return {
        int(promotion_id): PromotionLink(int(promotion_id), int(project_id), created_at)
        for promotion_id, project_id, created_at in rows.all()
    }


def _standard_project_ids(charge_mode: str) -> Any:
    return (
        select(DeliveryTaskProject.ocean_project_id)
        .join(DeliveryTaskDraft, DeliveryTaskDraft.id == DeliveryTaskProject.task_id)
        .where(
            DeliveryTaskProject.is_deleted == 0,
            DeliveryTaskDraft.is_deleted == 0,
            DeliveryTaskDraft.charge_mode == charge_mode,
        )
    )


async def manhua_facts(session: AsyncSession, start: date, end: date, charge_mode: str) -> list[ManhuaFact]:
    """区间内按广告合计。只取中台建出的、收费模式对得上的项目；对不上的巨量行不进个人列表。"""
    low, high = _hour_range(start, end)
    report = OeDeliveryReport
    rows = await session.execute(
        select(
            report.cdp_project_id,
            report.cdp_promotion_id,
            func.max(report.cdp_project_name),
            func.max(report.cdp_promotion_name),
            func.min(case((report.stat_cost > 0, report.stat_time_hour))),
            *[func.sum(getattr(report, name)) for name in MANHUA_BASE],
        )
        .where(
            report.is_deleted == 0,
            report.stat_time_hour >= low,
            report.stat_time_hour <= high,
            report.cdp_project_id.in_(_standard_project_ids(charge_mode)),
        )
        .group_by(report.cdp_project_id, report.cdp_promotion_id)
    )
    facts: list[ManhuaFact] = []
    for project_id, promotion_id, project_name, promotion_name, first_cost, *sums in rows.all():
        facts.append(
            ManhuaFact(
                project_id=int(project_id),
                promotion_id=int(promotion_id),
                project_name=str(project_name or ""),
                promotion_name=str(promotion_name or ""),
                metrics={name: Decimal(value or 0) for name, value in zip(MANHUA_BASE, sums)},
                first_cost_hour=first_cost,
            )
        )
    return facts


async def manhua_first_cost(
    session: AsyncSession, ids: Iterable[int], *, by_promotion: bool
) -> dict[int, str]:
    """第一个 stat_cost > 0 的快照小时，不限所选区间。"""
    wanted = list({int(item) for item in ids})
    if not wanted:
        return {}
    column = OeDeliveryReport.cdp_promotion_id if by_promotion else OeDeliveryReport.cdp_project_id
    rows = await session.execute(
        select(column, func.min(OeDeliveryReport.stat_time_hour))
        .where(OeDeliveryReport.is_deleted == 0, OeDeliveryReport.stat_cost > 0, column.in_(wanted))
        .group_by(column)
    )
    return {int(key): str(value) for key, value in rows.all() if value}


async def manhua_hourly(
    session: AsyncSession,
    day: date,
    *,
    project_ids: Iterable[int] | None = None,
    promotion_id: int | None = None,
) -> dict[int, tuple[Decimal, Decimal]]:
    """一天按小时的消耗和付费金额。"""
    low, high = _hour_range(day, day)
    filters: list[Any] = [
        OeDeliveryReport.is_deleted == 0,
        OeDeliveryReport.stat_time_hour >= low,
        OeDeliveryReport.stat_time_hour <= high,
    ]
    if promotion_id is not None:
        filters.append(OeDeliveryReport.cdp_promotion_id == promotion_id)
    else:
        ids = list({int(item) for item in project_ids or []})
        if not ids:
            return {}
        filters.append(OeDeliveryReport.cdp_project_id.in_(ids))
    rows = await session.execute(
        select(
            OeDeliveryReport.stat_time_hour,
            func.sum(OeDeliveryReport.stat_cost),
            func.sum(OeDeliveryReport.stat_pay_amount),
        )
        .where(*filters)
        .group_by(OeDeliveryReport.stat_time_hour)
    )
    hourly: dict[int, tuple[Decimal, Decimal]] = {}
    for stamp, cost, pay in rows.all():
        hour = _hour_of(stamp)
        if hour is None:
            continue
        old_cost, old_pay = hourly.get(hour, (Decimal("0"), Decimal("0")))
        hourly[hour] = (old_cost + Decimal(cost or 0), old_pay + Decimal(pay or 0))
    return hourly


def _hour_of(stamp: Any) -> int | None:
    text = str(stamp or "")
    if len(text) < 13 or not text[11:13].isdigit():
        return None
    return int(text[11:13])


async def uni_links(
    session: AsyncSession,
    *,
    project_ids: Iterable[int] | None = None,
    created_between: tuple[date, date] | None = None,
    series_id: int | None = None,
    pitcher_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, ProjectLink]:
    """全域任务账户行上的巨量项目 → 剧、投手、部门。project_ids 与 created_between 取并集。"""
    account = UniNativeTaskAccount
    task = UniNativeTask
    filters: list[Any] = [
        account.is_deleted == 0,
        task.is_deleted == 0,
        account.ocean_project_id.is_not(None),
    ]
    either: list[Any] = []
    if project_ids is not None:
        ids = list({int(item) for item in project_ids})
        if ids:
            either.append(account.ocean_project_id.in_(ids))
    if created_between is not None:
        low, high = created_between
        either.append(
            and_(
                task.status.in_(_STORED_UNI),
                func.date(func.timezone("Asia/Shanghai", account.updated_date)) >= low,
                func.date(func.timezone("Asia/Shanghai", account.updated_date)) <= high,
            )
        )
    if project_ids is not None or created_between is not None:
        if not either:
            return {}
        filters.append(or_(*either))
    if series_id is not None:
        filters.append(task.series_id == series_id)
    if pitcher_id is not None:
        filters.append(task.pitcher_user_id == pitcher_id)
    if department_id is not None:
        filters.append(User.department_id == department_id)
    rows = await session.execute(
        select(
            account.ocean_project_id,
            account.updated_date,
            task.status,
            task.series_id,
            task.pitcher_user_id,
            ManhuaSeries.book_name,
            DeliverySubject.theater_name,
            User.nickname,
            User.department_id,
            Department.name,
        )
        .join(task, task.id == account.task_id)
        .join(ManhuaSeries, ManhuaSeries.id == task.series_id)
        .outerjoin(DeliveryTemplate, DeliveryTemplate.id == task.template_id)
        .outerjoin(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .join(User, User.id == task.pitcher_user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(*filters)
    )
    theaters = await theater_lookup(session)
    links: dict[int, ProjectLink] = {}
    for (
        project_id,
        stored_at,
        status,
        series,
        pitcher,
        book_name,
        theater_name,
        nickname,
        dept_id,
        dept_name,
    ) in rows.all():
        _, channel = theaters.get(str(theater_name or ""), ("", ""))
        links[int(project_id)] = ProjectLink(
            project_id=int(project_id),
            series_id=int(series),
            book_name=str(book_name or ""),
            pitcher_id=int(pitcher),
            pitcher_name=str(nickname or ""),
            department_id=None if dept_id is None else int(dept_id),
            department_name=str(dept_name or ""),
            channel=channel,
            created_at=stored_at,
            stored=str(status) in _STORED_UNI,
        )
    return links


def _uni_project_ids() -> Any:
    return select(UniNativeTaskAccount.ocean_project_id).where(
        UniNativeTaskAccount.is_deleted == 0,
        UniNativeTaskAccount.ocean_project_id.is_not(None),
    )


async def uni_facts(session: AsyncSession, start: date, end: date) -> list[UniFact]:
    """区间内按（天，项目）合计。只取中台全域任务建出的项目。"""
    low, high = _hour_range(start, end)
    report = OeUniProjectReport
    day = func.substr(report.stat_time_hour, 1, 10)
    rows = await session.execute(
        select(
            day,
            report.cdp_project_id,
            func.max(report.cdp_project_name),
            *[func.sum(getattr(report, name)) for name in UNI_MONEY],
            func.sum(report.all_show_cnt_trend),
            func.sum(report.all_click_cnt_trend),
        )
        .where(
            report.is_deleted == 0,
            report.stat_time_hour >= low,
            report.stat_time_hour <= high,
            report.cdp_project_id.in_(_uni_project_ids()),
        )
        .group_by(day, report.cdp_project_id)
    )
    return [
        UniFact(
            day=str(stat_day),
            project_id=int(project_id),
            project_name=str(project_name or ""),
            metrics={
                name: Decimal(value or 0)
                for name, value in zip((*UNI_MONEY, "all_show_cnt_trend", "all_click_cnt_trend"), sums)
            },
        )
        for stat_day, project_id, project_name, *sums in rows.all()
    ]


async def uni_hourly_cost(session: AsyncSession, day: date, project_ids: Iterable[int]) -> dict[int, Decimal]:
    """一天按小时的 all_stat_cost_trend。"""
    ids = list({int(item) for item in project_ids})
    if not ids:
        return {}
    low, high = _hour_range(day, day)
    rows = await session.execute(
        select(OeUniProjectReport.stat_time_hour, func.sum(OeUniProjectReport.all_stat_cost_trend))
        .where(
            OeUniProjectReport.is_deleted == 0,
            OeUniProjectReport.stat_time_hour >= low,
            OeUniProjectReport.stat_time_hour <= high,
            OeUniProjectReport.cdp_project_id.in_(ids),
        )
        .group_by(OeUniProjectReport.stat_time_hour)
    )
    hourly: dict[int, Decimal] = {}
    for stamp, cost in rows.all():
        hour = _hour_of(stamp)
        if hour is not None:
            hourly[hour] = hourly.get(hour, Decimal("0")) + Decimal(cost or 0)
    return hourly


async def user_department_id(session: AsyncSession, user_id: int) -> int | None:
    return await session.scalar(select(User.department_id).where(User.id == user_id))
