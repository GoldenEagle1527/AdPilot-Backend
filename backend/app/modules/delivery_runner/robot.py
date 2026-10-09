"""漫剧机器人到点执行。只做按推广链接和按剧条件，不关项目、不删、不改预算。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.account.model import AdvertiserAccount, DouyinAccount, DouyinPitcher, OeReportSnapshot
from app.modules.delivery_runner.due import as_beijing, publish_on_day, robot_is_due, snapshots_satisfy, span_day
from app.modules.material.model import ManhuaSeries
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.schema import VideoQuery
from app.modules.material_video.service import video_filters
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.theater.model import TheaterApp, TheaterPromotionLink
from app.modules.uni_native_auto_run.model import RunStatus
from app.modules.uni_native_auto_run.service import RunFailure, record_run
from app.modules.uni_native_task.schema import AccountPair, PromotionLinkWrite, TaskWrite
from app.modules.uni_robot.model import RuleKind, UniRobotRule

logger = logging.getLogger("adpilot")

_VIDEO_CAP = 800
_inflight: set[int] = set()


def uni_task_body(
    *,
    template_id: int,
    series_id: int,
    douyin_id: int,
    advertiser_id: int,
    promotion_url: str | None,
    video_ids: list[int],
) -> TaskWrite:
    """组一条端原生任务。推广链只进 link_text，并且收费模式是 IAA。没有专辑链接字段。"""
    links: list[PromotionLinkWrite] = []
    if promotion_url:
        links.append(PromotionLinkWrite(charge_mode="IAA", link_text=promotion_url))
    return TaskWrite(
        template_id=template_id,
        series_id=series_id,
        accounts=[AccountPair(douyin_account_id=douyin_id, advertiser_id=advertiser_id)],
        promotion_links=links,
        video_ids=video_ids[:_VIDEO_CAP],
    )


async def _ran_today(session: AsyncSession, rule_id: int, now: datetime) -> bool:
    from app.modules.uni_native_auto_run.model import UniNativeAutoRun

    clock = as_beijing(now)
    start = clock.replace(hour=0, minute=0, second=0, microsecond=0)
    found = await session.scalar(
        select(UniNativeAutoRun.id)
        .where(
            UniNativeAutoRun.rule_id == rule_id,
            UniNativeAutoRun.is_deleted == 0,
            UniNativeAutoRun.executed_at >= start,
            UniNativeAutoRun.executed_at < start + timedelta(days=1),
        )
        .limit(1)
    )
    return found is not None


async def _pitcher_pair(
    session: AsyncSession,
    user_id: int | None,
) -> tuple[int, DouyinAccount, AdvertiserAccount] | None:
    """只用规则所属投手的全域抖音号和广告账户。"""
    if user_id is None:
        return None
    row = (
        await session.execute(
            select(DouyinAccount, AdvertiserAccount)
            .join(DouyinPitcher, DouyinPitcher.douyin_account_id == DouyinAccount.id)
            .join(
                AdvertiserAccount,
                AdvertiserAccount.pitcher_user_id == DouyinPitcher.user_id,
            )
            .where(
                DouyinPitcher.user_id == user_id,
                DouyinAccount.is_deleted == 0,
                DouyinAccount.enabled.is_(True),
                DouyinAccount.delivery_mode == "uni",
                DouyinPitcher.is_deleted == 0,
                AdvertiserAccount.pitcher_user_id == user_id,
                AdvertiserAccount.is_deleted == 0,
                AdvertiserAccount.sync_status == "active",
            )
            .order_by(AdvertiserAccount.assigned_at.desc().nulls_last(), AdvertiserAccount.id.desc())
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        return None
    douyin, account = row
    return int(account.pitcher_user_id), douyin, account


async def _videos(session: AsyncSession, series_id: int, user_id: int, limit: int) -> list[int]:
    rows = await session.scalars(
        select(MaterialVideo.id)
        .where(*video_filters(VideoQuery(series_id=series_id), user_id))
        .order_by(MaterialVideo.id)
        .limit(min(limit, _VIDEO_CAP))
    )
    return [int(item) for item in rows.all()]


async def _promotion_series(
    session: AsyncSession, platform_id: int
) -> list[tuple[ManhuaSeries, str]]:
    """平台下启用的 IAA 推广链。链接文本稍后只写入任务，不写入标准专辑链接。"""
    rows = (
        await session.execute(
            select(ManhuaSeries, TheaterPromotionLink.promotion_url)
            .join(TheaterPromotionLink, TheaterPromotionLink.series_id == ManhuaSeries.id)
            .join(TheaterApp, TheaterApp.id == TheaterPromotionLink.theater_app_id)
            .where(
                TheaterApp.platform_id == platform_id,
                TheaterApp.is_deleted == 0,
                TheaterPromotionLink.is_deleted == 0,
                TheaterPromotionLink.is_enabled.is_(True),
                ManhuaSeries.is_deleted == 0,
                or_(
                    TheaterPromotionLink.recharge_template_name == "IAA",
                    TheaterPromotionLink.media_config_type == 3,
                ),
            )
            .order_by(ManhuaSeries.id, TheaterPromotionLink.id.desc())
        )
    ).all()
    picked: list[tuple[ManhuaSeries, str]] = []
    seen: set[int] = set()
    for series, url in rows:
        if int(series.id) in seen or not str(url or "").strip():
            continue
        seen.add(int(series.id))
        picked.append((series, str(url)))
    return picked


async def _drama_series(
    session: AsyncSession,
    *,
    tab: str,
    stat_span: str,
    now: datetime,
    cost_min,
    cost_max,
    recovery_min,
    recovery_max,
) -> list[ManhuaSeries]:
    """按这部剧当天或昨天的消耗和回收比值筛选，不对上架日期。"""
    from app.modules.standard_delivery.match import series_stats

    day = span_day(stat_span, now)
    rows = await session.scalars(
        select(ManhuaSeries)
        .where(ManhuaSeries.is_deleted == 0, ManhuaSeries.tab_text == tab)
        .order_by(ManhuaSeries.id)
    )
    kept: list[ManhuaSeries] = []
    for series in rows.all():
        stats = await series_stats(session, int(series.id), series.book_name, day)
        if snapshots_satisfy(
            stats,
            cost_min=cost_min,
            cost_max=cost_max,
            recovery_min=recovery_min,
            recovery_max=recovery_max,
        ):
            kept.append(series)
    return kept


async def _snapshots(session: AsyncSession) -> list[tuple]:
    from decimal import Decimal

    rows = await session.execute(
        select(OeReportSnapshot.stat_cost, OeReportSnapshot.attribution_micro_game_0d_roi).where(
            OeReportSnapshot.is_deleted == 0
        )
    )
    return [(Decimal(cost), Decimal(roi)) for cost, roi in rows.all()]


async def execute_robot_rule(session: AsyncSession, rule: UniRobotRule, now: datetime) -> None:
    """创建端原生任务并走现有假客户端提交，再用 record_run 记下结果。"""
    from app.modules.uni_native_task.service import create_task
    from app.modules.uni_native_task.submit import submit_task

    clock = as_beijing(now)
    template = await session.get(DeliveryTemplate, int(rule.template_id))
    template_name = template.name if template is not None and not template.is_deleted else "模板"
    if template is None or template.is_deleted:
        await record_run(
            session,
            rule_id=int(rule.id),
            rule_name=rule.name,
            rule_type=rule.rule_kind,
            executed_at=clock,
            template_name=template_name,
            status=RunStatus.FAILED,
            series_names=[],
            failures=[RunFailure(series_name="规则", reason="模板不存在")],
        )
        await session.commit()
        return
    if rule.rule_kind == RuleKind.PROMOTION_LINK:
        linked = await _promotion_series(session, int(rule.platform_id))
        chosen = [(series, url) for series, url in linked]
    else:
        dramas = await _drama_series(
            session,
            tab=str(template.charge_mode),
            stat_span=str(rule.stat_span or "today"),
            now=clock,
            cost_min=rule.cost_min,
            cost_max=rule.cost_max,
            recovery_min=rule.recovery_min,
            recovery_max=rule.recovery_max,
        )
        chosen = [(series, None) for series in dramas]
    if not chosen:
        await record_run(
            session,
            rule_id=int(rule.id),
            rule_name=rule.name,
            rule_type=rule.rule_kind,
            executed_at=clock,
            template_name=template.name,
            status=RunStatus.SUCCESS,
            series_names=[],
        )
        await session.commit()
        return
    owner_id = getattr(rule, "pitcher_user_id", None)
    pair = await _pitcher_pair(session, int(owner_id) if owner_id is not None else None)
    failures: list[RunFailure] = []
    succeeded: list[str] = []
    if owner_id is None:
        for series, _url in chosen:
            failures.append(RunFailure(series_name=series.book_name, reason="规则没有所属投手"))
    elif pair is None:
        for series, _url in chosen:
            failures.append(RunFailure(series_name=series.book_name, reason="没有已分配的全域抖音号或广告账户"))
    else:
        user_id, douyin, account = pair
        for series, url in chosen:
            videos = await _videos(
                session, int(series.id), user_id, int(rule.max_videos_per_series)
            )
            if not videos:
                failures.append(RunFailure(series_name=series.book_name, reason="这部剧没有视频素材"))
                continue
            try:
                body = uni_task_body(
                    template_id=int(template.id),
                    series_id=int(series.id),
                    douyin_id=int(douyin.id),
                    advertiser_id=int(account.advertiser_id),
                    promotion_url=url,
                    video_ids=videos,
                )
                saved = await create_task(session, body, user_id)
                await submit_task(session, int(saved["id"]), user_id)
            except ApiError as exc:
                failures.append(RunFailure(series_name=series.book_name, reason=exc.message))
                continue
            except Exception as exc:
                logger.exception("漫剧机器人规则 %s 短剧 %s 执行失败", rule.id, series.id)
                failures.append(RunFailure(series_name=series.book_name, reason=str(exc)[:2000] or "执行失败"))
                continue
            succeeded.append(series.book_name)
    if not failures:
        status = RunStatus.SUCCESS
    elif not succeeded:
        status = RunStatus.FAILED
    else:
        status = RunStatus.PARTIAL
    names = succeeded + [item.series_name for item in failures]
    await record_run(
        session,
        rule_id=int(rule.id),
        rule_name=rule.name,
        rule_type=rule.rule_kind,
        executed_at=clock,
        template_name=template.name,
        status=status,
        series_names=names,
        failures=failures,
    )
    await session.commit()


async def run_due_robots(session: AsyncSession, now: datetime) -> int:
    """跑今天已到时分、仍开启、今天还没记录的机器人规则。"""
    rules = list(
        await session.scalars(
            select(UniRobotRule).where(UniRobotRule.is_deleted == 0, UniRobotRule.is_enabled.is_(True))
        )
    )
    ran = 0
    for rule in rules:
        if int(rule.id) in _inflight:
            continue
        already = await _ran_today(session, int(rule.id), now)
        if not robot_is_due(
            is_enabled=bool(rule.is_enabled),
            schedule_hour=int(rule.schedule_hour),
            schedule_minute=int(rule.schedule_minute),
            ran_today=already,
            now=now,
        ):
            continue
        _inflight.add(int(rule.id))
        try:
            await execute_robot_rule(session, rule, now)
            ran += 1
        except Exception:
            logger.exception("漫剧机器人规则 %s 执行失败", rule.id)
        finally:
            _inflight.discard(int(rule.id))
    return ran
