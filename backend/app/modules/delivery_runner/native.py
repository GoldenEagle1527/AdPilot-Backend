"""标准端原生机器人到点执行。内部建草稿并确认提交，不在这里上传素材。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.account.model import OeProject
from app.modules.delivery_runner.due import as_beijing, snapshots_satisfy, span_day
from app.modules.material.model import ManhuaSeries
from app.modules.oceanengine.runtime import _access_token, get_ocean_client
from app.modules.standard_delivery.match import (
    iaa_link_for_series,
    library_titles,
    match_advertisers,
    series_stats,
    series_videos,
)
from app.modules.standard_delivery.model import GOAL_BY_CHARGE, DeliveryTemplate, OperationStatus
from app.modules.standard_delivery.schema import DraftWrite
from app.modules.standard_robot.model import StandardNativeRobotRule
from app.modules.theater.model import TheaterApp, TheaterPromotionLink

logger = logging.getLogger("adpilot")


def native_is_due(rule: StandardNativeRobotRule, now: datetime) -> bool:
    """每小时或每天到点，并且这一档还没跑过。"""
    if not rule.is_enabled:
        return False
    clock = as_beijing(now)
    last = None if rule.last_ran_at is None else as_beijing(rule.last_ran_at)
    if rule.schedule_kind == "hourly":
        if clock.minute < int(rule.schedule_minute):
            return False
        if last is None:
            return True
        return (last.date(), last.hour) != (clock.date(), clock.hour)
    slot = clock.replace(
        hour=int(rule.schedule_hour or 0),
        minute=int(rule.schedule_minute),
        second=0,
        microsecond=0,
    )
    if clock < slot:
        return False
    return last is None or last.date() != clock.date()


async def _nb_names(session: AsyncSession) -> list[str]:
    """项目列表里名字带 NB，或出价是最大转化的项目名。"""
    client = get_ocean_client()
    remote = await client.list_projects(await _access_token(session), {})
    names = [str(item.get("name") or "") for item in ((remote.get("data") or {}).get("list") or [])]
    rows = await session.scalars(select(OeProject).where(OeProject.is_deleted == 0))
    for project in rows.all():
        template = project.template if isinstance(project.template, dict) else {}
        setting = template.get("delivery_setting") if isinstance(template, dict) else {}
        bid = ""
        if isinstance(setting, dict):
            bid = str(setting.get("bid_type") or "")
        blob = str(template)
        if "NB" in str(project.name or "") or bid == "NO_BID" or "NO_BID" in blob:
            names.append(str(project.name or ""))
    return [name for name in names if name]


async def _targets(session: AsyncSession, rule: StandardNativeRobotRule, now: datetime) -> list[tuple[ManhuaSeries, str | None]]:
    """按规则类型找出要建任务的短剧。推广链规则带回链接。"""
    clock = as_beijing(now)
    if rule.rule_kind == "promotion_link":
        rows = (
            await session.execute(
                select(ManhuaSeries, TheaterPromotionLink.promotion_url)
                .join(TheaterPromotionLink, TheaterPromotionLink.series_id == ManhuaSeries.id)
                .join(TheaterApp, TheaterApp.id == TheaterPromotionLink.theater_app_id)
                .where(
                    TheaterApp.platform_id == rule.platform_id,
                    TheaterApp.is_deleted == 0,
                    TheaterPromotionLink.is_deleted == 0,
                    TheaterPromotionLink.is_enabled.is_(True),
                    ManhuaSeries.is_deleted == 0,
                )
                .order_by(ManhuaSeries.id)
            )
        ).all()
        picked: list[tuple[ManhuaSeries, str | None]] = []
        seen: set[int] = set()
        for series, url in rows:
            if int(series.id) in seen or not str(url or "").strip():
                continue
            seen.add(int(series.id))
            picked.append((series, str(url)))
        return picked
    series_rows = list(
        await session.scalars(select(ManhuaSeries).where(ManhuaSeries.is_deleted == 0).order_by(ManhuaSeries.id))
    )
    if rule.rule_kind == "nb":
        names = await _nb_names(session)
        series_rows = [row for row in series_rows if any(row.book_name[:2] and row.book_name[:2] in name for name in names)]
    day = span_day(str(rule.stat_span or "today"), clock)
    kept: list[tuple[ManhuaSeries, str | None]] = []
    for series in series_rows:
        if rule.cost_min is None and rule.recovery_min is None and rule.rule_kind == "drama":
            continue
        stats = await series_stats(session, int(series.id), series.book_name, day if rule.rule_kind == "drama" else None)
        if rule.cost_min is None and rule.recovery_min is None:
            kept.append((series, None))
            continue
        if snapshots_satisfy(
            stats,
            cost_min=rule.cost_min,
            cost_max=rule.cost_max,
            recovery_min=rule.recovery_min,
            recovery_max=rule.recovery_max,
        ):
            kept.append((series, None))
    return kept


async def execute_native_rule(session: AsyncSession, rule: StandardNativeRobotRule, now: datetime) -> None:
    """用规则所属投手的新账户建草稿并提交。"""
    from app.modules.standard_delivery.service import create_draft
    from app.modules.standard_delivery.submit import submit_draft

    template = await session.get(DeliveryTemplate, int(rule.template_id))
    if template is None or template.is_deleted or template.delivery_mode != "standard":
        return
    if template.charge_mode != rule.charge_mode or template.ad_budget is None:
        return
    targets = await _targets(session, rule, now)
    user_id = int(rule.pitcher_user_id)
    allowed = {str(rule.charge_mode)}
    limit = min(int(rule.max_videos_per_series), 800)
    for series, url in targets:
        accounts = await match_advertisers(session, user_id, int(rule.accounts_per_series), unused_only=True)
        videos = await series_videos(session, int(series.id), user_id, limit=limit, order="upload")
        category = "paid" if rule.charge_mode == "IAP" else "common"
        titles = await library_titles(session, user_id, limit=int(template.titles_per_ad or 10), category=category)
        if not accounts or not videos or not titles:
            continue
        album = url
        if not album:
            link = await iaa_link_for_series(session, int(series.id))
            album = None if link is None else link.promotion_url
        if not album:
            continue
        try:
            saved = await create_draft(
                session,
                DraftWrite(
                    template_id=int(template.id),
                    charge_mode=rule.charge_mode,
                    advertiser_ids=[int(account.advertiser_id) for account in accounts],
                    series_id=int(series.id),
                    video_ids=[int(video.id) for video in videos],
                    title_ids=[int(title.id) for title in titles],
                    ad_budget=template.ad_budget,
                    optimize_goal=GOAL_BY_CHARGE[template.charge_mode],
                    album_url=str(album),
                    project_operation=OperationStatus.ENABLE,
                ),
                user_id,
                allowed,
                free_template=False,
            )
            await submit_draft(session, int(saved["id"]), user_id, allowed)
        except ApiError:
            await session.rollback()
        except Exception:
            logger.exception("标准端原生机器人 %s 短剧 %s 执行失败", rule.id, series.id)
            await session.rollback()


async def run_due_native(session: AsyncSession, now: datetime) -> int:
    """跑到点的标准端原生机器人。"""
    rules = list(
        await session.scalars(
            select(StandardNativeRobotRule).where(
                StandardNativeRobotRule.is_deleted == 0,
                StandardNativeRobotRule.is_enabled.is_(True),
            )
        )
    )
    ran = 0
    clock = as_beijing(now)
    for rule in rules:
        if not native_is_due(rule, clock):
            continue
        try:
            await execute_native_rule(session, rule, clock)
            rule.last_ran_at = clock
            await session.commit()
            ran += 1
        except Exception:
            logger.exception("标准端原生机器人 %s 执行失败", rule.id)
            await session.rollback()
    return ran
