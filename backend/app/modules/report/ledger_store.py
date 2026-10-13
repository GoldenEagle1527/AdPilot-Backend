"""利润、素材日表的刷新和读取。列表不扫小时明细。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_now, beijing_stamp
from app.modules.account.model import DeliverySubject, OeMaterialReport
from app.modules.material.model import ManhuaSeries
from app.modules.material_video.model import MaterialVideo, MaterialVideoPitcher
from app.modules.report.crud import theater_lookup
from app.modules.report.ledger import (
    MaterialSlice,
    ProfitSlice,
    ProjectCard,
    RawMaterial,
    RoiSpan,
    SeriesCard,
    VideoCard,
    beijing_day,
    build_slices,
    library_ids,
)
from app.modules.report.serving import ReportMaterialDay, ReportProfitDay, ReportRoiConfig
from app.modules.standard_delivery.model import (
    DeliveryTaskDraft,
    DeliveryTaskProject,
    DeliveryTaskVideo,
    DeliveryTemplate,
)
from app.modules.system_admin.domain.models import Department, Role, User, UserRole, UserTag, UserTagLink
from app.modules.uni_native_task.model import (
    UniNativeTask,
    UniNativeTaskAccount,
    UniNativeTaskLink,
    UniNativeTaskVideo,
)

_NOT_FOUND = "ROI配置不存在"


@dataclass(frozen=True)
class AccountFlags:
    department_id: int | None
    role_names: tuple[str, ...]
    tag_names: tuple[str, ...]


def _money(value: Any) -> Decimal:
    return Decimal(value or 0)


def _day_text(stamp: Any) -> date | None:
    text = str(stamp or "")
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


async def account_flags(session: AsyncSession, user_id: int) -> AccountFlags:
    user = await session.get(User, user_id)
    department_id = None if user is None else int(user.department_id)
    roles = await session.scalars(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, UserRole.is_deleted == 0, Role.is_deleted == 0)
    )
    tags = await session.scalars(
        select(UserTag.name)
        .join(UserTagLink, UserTagLink.tag_id == UserTag.id)
        .where(UserTagLink.user_id == user_id, UserTagLink.is_deleted == 0, UserTag.is_deleted == 0)
    )
    return AccountFlags(department_id, tuple(roles.all()), tuple(tags.all()))


async def replace_ledger_days(session: AsyncSession, days: list[date]) -> int:
    """删掉这些统计日的利润和素材日行，再按素材小时表重写。不提交。"""
    if not days:
        return 0
    await session.execute(delete(ReportProfitDay).where(ReportProfitDay.stat_date.in_(days)))
    await session.execute(delete(ReportMaterialDay).where(ReportMaterialDay.stat_date.in_(days)))
    raws = await _raws(session, days)
    projects = await _projects(session, {row.project_id for row in raws})
    videos = await _videos(session, raws, projects)
    materials, profits = build_slices(raws, projects, videos)
    for row in materials:
        session.add(_material_row(row))
    for row in profits:
        session.add(_profit_row(row))
    return len(materials) + len(profits)


async def _raws(session: AsyncSession, days: list[date]) -> list[RawMaterial]:
    day_text = func.substr(OeMaterialReport.stat_time_hour, 1, 10)
    rows = await session.execute(
        select(
            day_text,
            OeMaterialReport.material_id,
            func.max(OeMaterialReport.ad_platform_material_name),
            OeMaterialReport.cdp_promotion_id,
            func.max(OeMaterialReport.cdp_promotion_name),
            OeMaterialReport.cdp_project_id,
            func.max(OeMaterialReport.cdp_project_name),
            func.sum(OeMaterialReport.stat_cost),
            func.sum(OeMaterialReport.stat_pay_amount),
            func.sum(OeMaterialReport.show_cnt),
            func.sum(OeMaterialReport.click_cnt),
            func.sum(OeMaterialReport.convert_cnt),
        )
        .where(OeMaterialReport.is_deleted == 0, day_text.in_([day.isoformat() for day in days]))
        .group_by(
            day_text,
            OeMaterialReport.material_id,
            OeMaterialReport.cdp_promotion_id,
            OeMaterialReport.cdp_project_id,
        )
    )
    raws: list[RawMaterial] = []
    for (
        stamp,
        material_id,
        material_name,
        promotion_id,
        promotion_name,
        project_id,
        project_name,
        cost,
        recovery,
        show_cnt,
        click_cnt,
        convert_cnt,
    ) in rows.all():
        stat_date = _day_text(stamp)
        if stat_date is None:
            continue
        raws.append(
            RawMaterial(
                stat_date=stat_date,
                material_id=int(material_id),
                material_name=str(material_name or ""),
                promotion_id=int(promotion_id),
                promotion_name=str(promotion_name or ""),
                project_id=int(project_id),
                project_name=str(project_name or ""),
                stat_cost=_money(cost),
                recovery=_money(recovery),
                show_cnt=int(show_cnt or 0),
                click_cnt=int(click_cnt or 0),
                convert_cnt=int(convert_cnt or 0),
            )
        )
    return raws


async def _projects(session: AsyncSession, project_ids: set[int]) -> dict[int, ProjectCard]:
    if not project_ids:
        return {}
    theaters = await theater_lookup(session)
    cards: dict[int, ProjectCard] = {}
    task_videos: dict[int, list[int]] = {}
    standard_tasks, uni_tasks = await _fill_projects(session, project_ids, theaters, cards)
    await _attach_videos(session, standard_tasks, uni_tasks, cards, task_videos)
    return cards


async def _fill_projects(
    session: AsyncSession,
    project_ids: set[int],
    theaters: dict[str, tuple[str, str]],
    cards: dict[int, ProjectCard],
) -> tuple[set[int], set[int]]:
    standard_tasks: set[int] = set()
    rows = await session.execute(
        select(
            DeliveryTaskProject.ocean_project_id,
            DeliveryTaskProject.task_id,
            DeliveryTemplate.name,
            DeliveryTaskDraft.charge_mode,
            DeliveryTaskDraft.series_id,
            ManhuaSeries.book_name,
            ManhuaSeries.estimate_publish_time,
            DeliverySubject.theater_name,
            DeliveryTaskDraft.pitcher_user_id,
            User.nickname,
            User.department_id,
            Department.name,
        )
        .join(DeliveryTaskDraft, DeliveryTaskDraft.id == DeliveryTaskProject.task_id)
        .join(DeliveryTemplate, DeliveryTemplate.id == DeliveryTaskDraft.template_id)
        .join(ManhuaSeries, ManhuaSeries.id == DeliveryTaskDraft.series_id)
        .outerjoin(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .join(User, User.id == DeliveryTaskDraft.pitcher_user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(
            DeliveryTaskProject.is_deleted == 0,
            DeliveryTaskDraft.is_deleted == 0,
            DeliveryTaskProject.ocean_project_id.in_(project_ids),
        )
    )
    for row in rows.all():
        project_id = int(row[0])
        task_id = int(row[1])
        standard_tasks.add(task_id)
        cards[project_id] = _card(row, "standard", str(row[3] or ""), theaters, task_id)
    uni_result = await session.execute(
        select(
            UniNativeTaskAccount.ocean_project_id,
            UniNativeTaskAccount.task_id,
            DeliveryTemplate.name,
            UniNativeTask.series_id,
            ManhuaSeries.book_name,
            ManhuaSeries.estimate_publish_time,
            DeliverySubject.theater_name,
            UniNativeTask.pitcher_user_id,
            User.nickname,
            User.department_id,
            Department.name,
        )
        .join(UniNativeTask, UniNativeTask.id == UniNativeTaskAccount.task_id)
        .outerjoin(DeliveryTemplate, DeliveryTemplate.id == UniNativeTask.template_id)
        .join(ManhuaSeries, ManhuaSeries.id == UniNativeTask.series_id)
        .outerjoin(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .join(User, User.id == UniNativeTask.pitcher_user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(
            UniNativeTaskAccount.is_deleted == 0,
            UniNativeTask.is_deleted == 0,
            UniNativeTaskAccount.ocean_project_id.is_not(None),
            UniNativeTaskAccount.ocean_project_id.in_(project_ids),
        )
    )
    uni_found = list(uni_result.all())
    uni_tasks = {int(row[1]) for row in uni_found}
    charges = await _uni_charge(session, uni_tasks)
    for row in uni_found:
        project_id = int(row[0])
        if project_id in cards:
            continue
        task_id = int(row[1])
        cards[project_id] = _card(row, "uni", charges.get(task_id, ""), theaters, task_id, uni=True)
    return standard_tasks, uni_tasks


def _card(
    row: Any,
    scope: str,
    charge_mode: str,
    theaters: dict[str, tuple[str, str]],
    task_id: int,
    *,
    uni: bool = False,
) -> ProjectCard:
    """标准行和全域行的列顺序不同，全域没有单独的 charge_mode 列。"""
    if uni:
        theater_name, pitcher_id, nickname, department_id, department_name = row[6], row[7], row[8], row[9], row[10]
        template_name, series_id, book_name, estimate = row[2], row[3], row[4], row[5]
    else:
        template_name, series_id, book_name, estimate = row[2], row[4], row[5], row[6]
        theater_name, pitcher_id, nickname, department_id, department_name = row[7], row[8], row[9], row[10], row[11]
    drama_type, channel = theaters.get(str(theater_name or ""), ("", ""))
    return ProjectCard(
        project_id=int(row[0]),
        task_id=task_id,
        scope=scope,
        template_name=str(template_name or ""),
        charge_mode=charge_mode,
        series_id=int(series_id),
        book_name=str(book_name or ""),
        estimate_publish_date=beijing_day(estimate),
        drama_type=drama_type,
        channel=channel,
        pitcher_id=int(pitcher_id),
        pitcher_name=str(nickname or ""),
        department_id=0 if department_id is None else int(department_id),
        department_name=str(department_name or ""),
    )


async def _uni_charge(session: AsyncSession, task_ids: set[int]) -> dict[int, str]:
    if not task_ids:
        return {}
    rows = await session.execute(
        select(UniNativeTaskLink.task_id, UniNativeTaskLink.charge_mode)
        .where(UniNativeTaskLink.is_deleted == 0, UniNativeTaskLink.task_id.in_(task_ids))
        .order_by(UniNativeTaskLink.task_id, UniNativeTaskLink.sort_order, UniNativeTaskLink.id)
    )
    charges: dict[int, str] = {}
    for task_id, mode in rows.all():
        charges.setdefault(int(task_id), str(mode or ""))
    return charges


async def _attach_videos(
    session: AsyncSession,
    standard_tasks: set[int],
    uni_tasks: set[int],
    cards: dict[int, ProjectCard],
    task_videos: dict[int, list[int]],
) -> None:
    if standard_tasks:
        rows = await session.execute(
            select(DeliveryTaskVideo.task_id, DeliveryTaskVideo.material_video_id).where(
                DeliveryTaskVideo.is_deleted == 0,
                DeliveryTaskVideo.task_id.in_(standard_tasks),
            )
        )
        for task_id, video_id in rows.all():
            task_videos.setdefault(int(task_id), []).append(int(video_id))
    if uni_tasks:
        rows = await session.execute(
            select(UniNativeTaskVideo.task_id, UniNativeTaskVideo.material_video_id).where(
                UniNativeTaskVideo.is_deleted == 0,
                UniNativeTaskVideo.task_id.in_(uni_tasks),
            )
        )
        for task_id, video_id in rows.all():
            task_videos.setdefault(int(task_id), []).append(int(video_id))
    for project_id, card in list(cards.items()):
        videos = tuple(dict.fromkeys(task_videos.get(card.task_id, [])))
        cards[project_id] = ProjectCard(
            project_id=card.project_id,
            task_id=card.task_id,
            scope=card.scope,
            template_name=card.template_name,
            charge_mode=card.charge_mode,
            series_id=card.series_id,
            book_name=card.book_name,
            estimate_publish_date=card.estimate_publish_date,
            drama_type=card.drama_type,
            channel=card.channel,
            pitcher_id=card.pitcher_id,
            pitcher_name=card.pitcher_name,
            department_id=card.department_id,
            department_name=card.department_name,
            video_ids=videos,
        )


async def _videos(
    session: AsyncSession,
    raws: list[RawMaterial],
    projects: dict[int, ProjectCard],
) -> dict[int, VideoCard]:
    names = {raw.material_name.strip() for raw in raws if raw.material_name.strip()}
    series_ids = {card.series_id for card in projects.values()}
    wanted = set(library_ids(raw.material_id for raw in raws))
    for card in projects.values():
        wanted.update(library_ids(card.video_ids))
    filters = [MaterialVideo.is_deleted == 0]
    either = []
    if wanted:
        either.append(MaterialVideo.id.in_(wanted))
    if names and series_ids:
        either.append((MaterialVideo.name.in_(names)) & (MaterialVideo.series_id.in_(series_ids)))
    if not either:
        return {}
    filters.append(or_(*either))
    rows = await session.execute(
        select(
            MaterialVideo.id,
            MaterialVideo.name,
            MaterialVideo.series_id,
            ManhuaSeries.book_name,
            ManhuaSeries.estimate_publish_time,
            MaterialVideo.material_type,
            MaterialVideo.ownership,
            MaterialVideo.file_urls,
            MaterialVideo.uploader_id,
            User.nickname,
            User.department_id,
            Department.name,
        )
        .join(ManhuaSeries, ManhuaSeries.id == MaterialVideo.series_id)
        .join(User, User.id == MaterialVideo.uploader_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(*filters)
    )
    found = list(rows.all())
    pitchers = await _video_pitchers(session, [int(row[0]) for row in found])
    cards: dict[int, VideoCard] = {}
    for row in found:
        video_id = int(row[0])
        urls = row[7] or []
        ids, names_ = pitchers.get(video_id, ((), ()))
        cards[video_id] = VideoCard(
            video_id=video_id,
            name=str(row[1] or ""),
            series_id=int(row[2]),
            book_name=str(row[3] or ""),
            estimate_publish_date=beijing_day(row[4]),
            material_type=str(row[5] or ""),
            ownership=str(row[6] or ""),
            file_url=str(urls[0]) if urls else "",
            uploader_id=int(row[8]),
            uploader_name=str(row[9] or ""),
            uploader_department_id=None if row[10] is None else int(row[10]),
            uploader_department_name=str(row[11] or ""),
            pitcher_ids=ids,
            pitcher_names=names_,
        )
    return cards


async def _video_pitchers(session: AsyncSession, video_ids: list[int]) -> dict[int, tuple[tuple[int, ...], tuple[str, ...]]]:
    if not video_ids:
        return {}
    rows = await session.execute(
        select(MaterialVideoPitcher.video_id, MaterialVideoPitcher.user_id, User.nickname)
        .join(User, User.id == MaterialVideoPitcher.user_id)
        .where(MaterialVideoPitcher.is_deleted == 0, MaterialVideoPitcher.video_id.in_(video_ids))
    )
    grouped: dict[int, list[tuple[int, str]]] = {}
    for video_id, user_id, nickname in rows.all():
        grouped.setdefault(int(video_id), []).append((int(user_id), str(nickname or "")))
    packed: dict[int, tuple[tuple[int, ...], tuple[str, ...]]] = {}
    for video_id, pairs in grouped.items():
        ordered = sorted(pairs)
        packed[video_id] = (tuple(item[0] for item in ordered), tuple(item[1] for item in ordered))
    return packed


def _material_row(row: MaterialSlice) -> ReportMaterialDay:
    return ReportMaterialDay(
        stat_date=row.stat_date,
        ocean_material_id=row.ocean_material_id,
        promotion_id=row.promotion_id,
        promotion_name=row.promotion_name,
        project_id=row.project_id,
        project_name=row.project_name,
        scope=row.scope,
        is_nobid=row.is_nobid,
        charge_mode=row.charge_mode,
        series_id=row.series_id,
        book_name=row.book_name,
        estimate_publish_date=row.estimate_publish_date,
        video_id=row.video_id,
        material_name=row.material_name,
        material_type=row.material_type,
        ownership=row.ownership,
        file_url=row.file_url,
        uploader_id=row.uploader_id,
        uploader_name=row.uploader_name,
        uploader_department_id=row.uploader_department_id,
        uploader_department_name=row.uploader_department_name,
        pitcher_id=row.pitcher_id,
        pitcher_name=row.pitcher_name,
        video_pitcher_ids=list(row.video_pitcher_ids),
        video_pitcher_names=list(row.video_pitcher_names),
        stat_cost=row.stat_cost,
        recovery=row.recovery,
        show_cnt=row.show_cnt,
        click_cnt=row.click_cnt,
        convert_cnt=row.convert_cnt,
    )


def _profit_row(row: ProfitSlice) -> ReportProfitDay:
    return ReportProfitDay(
        stat_date=row.stat_date,
        scope=row.scope,
        charge_mode=row.charge_mode,
        drama_type=row.drama_type,
        platform=row.platform,
        department_id=row.department_id,
        department_name=row.department_name,
        pitcher_id=row.pitcher_id,
        pitcher_name=row.pitcher_name,
        stat_cost=row.stat_cost,
        recovery=row.recovery,
    )


async def profit_slices(session: AsyncSession, start: date, end: date) -> list[ProfitSlice]:
    rows = await session.scalars(
        select(ReportProfitDay).where(
            ReportProfitDay.is_deleted == 0,
            ReportProfitDay.stat_date >= start,
            ReportProfitDay.stat_date <= end,
        )
    )
    return [
        ProfitSlice(
            stat_date=row.stat_date,
            scope=row.scope,
            charge_mode=row.charge_mode,
            drama_type=row.drama_type,
            platform=row.platform,
            department_id=row.department_id,
            department_name=row.department_name,
            pitcher_id=row.pitcher_id,
            pitcher_name=row.pitcher_name,
            stat_cost=_money(row.stat_cost),
            recovery=_money(row.recovery),
        )
        for row in rows.all()
    ]


async def material_slices(session: AsyncSession, start: date, end: date) -> list[MaterialSlice]:
    rows = await session.scalars(
        select(ReportMaterialDay).where(
            ReportMaterialDay.is_deleted == 0,
            ReportMaterialDay.stat_date >= start,
            ReportMaterialDay.stat_date <= end,
        )
    )
    return [_material_slice(row) for row in rows.all()]


def _material_slice(row: ReportMaterialDay) -> MaterialSlice:
    return MaterialSlice(
        stat_date=row.stat_date,
        ocean_material_id=int(row.ocean_material_id),
        promotion_id=int(row.promotion_id),
        promotion_name=row.promotion_name,
        project_id=int(row.project_id),
        project_name=row.project_name,
        scope=row.scope,
        is_nobid=bool(row.is_nobid),
        charge_mode=row.charge_mode,
        series_id=row.series_id,
        book_name=row.book_name,
        estimate_publish_date=row.estimate_publish_date,
        video_id=row.video_id,
        material_name=row.material_name,
        material_type=row.material_type,
        ownership=row.ownership,
        file_url=row.file_url,
        uploader_id=row.uploader_id,
        uploader_name=row.uploader_name,
        uploader_department_id=row.uploader_department_id,
        uploader_department_name=row.uploader_department_name,
        pitcher_id=row.pitcher_id,
        pitcher_name=row.pitcher_name,
        video_pitcher_ids=list(row.video_pitcher_ids or []),
        video_pitcher_names=list(row.video_pitcher_names or []),
        stat_cost=_money(row.stat_cost),
        recovery=_money(row.recovery),
        show_cnt=int(row.show_cnt or 0),
        click_cnt=int(row.click_cnt or 0),
        convert_cnt=int(row.convert_cnt or 0),
    )


async def roi_spans(session: AsyncSession) -> list[RoiSpan]:
    rows = await session.scalars(select(ReportRoiConfig).where(ReportRoiConfig.is_deleted == 0))
    return [
        RoiSpan(
            config_id=int(row.id),
            start=row.date_start,
            end=row.date_end,
            rate=_money(row.roi_rate),
            created_at=row.created_date,
        )
        for row in rows.all()
    ]


def roi_item(row: ReportRoiConfig) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "date_start": row.date_start.isoformat(),
        "date_end": row.date_end.isoformat(),
        "roi_rate": round(float(row.roi_rate), 2),
        "created_date": beijing_stamp(row.created_date),
    }


async def list_roi(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(ReportRoiConfig)
        .where(ReportRoiConfig.is_deleted == 0)
        .order_by(ReportRoiConfig.created_date.desc(), ReportRoiConfig.id.desc())
    )
    return [roi_item(row) for row in rows.all()]


async def create_roi(session: AsyncSession, start: date, end: date, rate: Decimal) -> dict[str, Any]:
    now = beijing_now()
    row = ReportRoiConfig(date_start=start, date_end=end, roi_rate=rate, created_date=now, updated_date=now)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return roi_item(row)


async def update_roi(session: AsyncSession, config_id: int, start: date, end: date, rate: Decimal) -> dict[str, Any]:
    row = await _live_roi(session, config_id)
    row.date_start = start
    row.date_end = end
    row.roi_rate = rate
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return roi_item(row)


async def delete_roi(session: AsyncSession, config_id: int) -> dict[str, Any]:
    row = await _live_roi(session, config_id)
    row.mark_deleted()
    await session.commit()
    return {"id": config_id, "deleted": True}


async def _live_roi(session: AsyncSession, config_id: int) -> ReportRoiConfig:
    row = await session.get(ReportRoiConfig, config_id)
    if row is None or row.is_deleted:
        raise ApiError(404, _NOT_FOUND)
    return row


async def library_counts(session: AsyncSession, series_ids: Iterable[int]) -> dict[int, int]:
    ids = list({int(item) for item in series_ids})
    if not ids:
        return {}
    rows = await session.execute(
        select(MaterialVideo.series_id, func.count())
        .where(MaterialVideo.is_deleted == 0, MaterialVideo.series_id.in_(ids))
        .group_by(MaterialVideo.series_id)
    )
    return {int(series_id): int(count) for series_id, count in rows.all()}


async def series_on_estimate(session: AsyncSession, start: date, end: date) -> list[SeriesCard]:
    day = func.date(func.timezone("Asia/Shanghai", ManhuaSeries.estimate_publish_time))
    rows = await session.execute(
        select(ManhuaSeries.id, ManhuaSeries.book_name, ManhuaSeries.estimate_publish_time).where(
            ManhuaSeries.is_deleted == 0,
            ManhuaSeries.estimate_publish_time.is_not(None),
            day >= start,
            day <= end,
        )
    )
    cards = []
    for series_id, book_name, estimate in rows.all():
        publish = beijing_day(estimate)
        if publish is None:
            continue
        cards.append(SeriesCard(int(series_id), str(book_name or ""), publish))
    return cards


async def nb_material_counts(session: AsyncSession, series_ids: Iterable[int]) -> dict[int, int]:
    ids = list({int(item) for item in series_ids})
    if not ids:
        return {}
    nb_name = or_(
        func.upper(DeliveryTemplate.name).contains("NB"),
        func.upper(DeliveryTemplate.name).contains("CBO"),
    )
    standard = await session.execute(
        select(DeliveryTaskDraft.series_id, DeliveryTaskVideo.material_video_id)
        .join(DeliveryTemplate, DeliveryTemplate.id == DeliveryTaskDraft.template_id)
        .join(DeliveryTaskVideo, DeliveryTaskVideo.task_id == DeliveryTaskDraft.id)
        .where(
            DeliveryTaskDraft.is_deleted == 0,
            DeliveryTaskVideo.is_deleted == 0,
            DeliveryTemplate.is_deleted == 0,
            DeliveryTaskDraft.series_id.in_(ids),
            nb_name,
        )
    )
    uni = await session.execute(
        select(UniNativeTask.series_id, UniNativeTaskVideo.material_video_id)
        .join(DeliveryTemplate, DeliveryTemplate.id == UniNativeTask.template_id)
        .join(UniNativeTaskVideo, UniNativeTaskVideo.task_id == UniNativeTask.id)
        .where(
            UniNativeTask.is_deleted == 0,
            UniNativeTaskVideo.is_deleted == 0,
            DeliveryTemplate.is_deleted == 0,
            UniNativeTask.series_id.in_(ids),
            nb_name,
        )
    )
    grouped: dict[int, set[int]] = {}
    for series_id, video_id in [*standard.all(), *uni.all()]:
        grouped.setdefault(int(series_id), set()).add(int(video_id))
    return {series_id: len(videos) for series_id, videos in grouped.items()}
