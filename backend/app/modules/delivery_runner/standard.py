"""标准自动规则执行。建草稿后走现有确认提交，不在这里发明巨量视频号。"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.modules.account.model import AdvertiserAccount, OeReportSnapshot
from app.modules.delivery_runner.due import (
    as_beijing,
    series_block_reason,
    snapshots_satisfy,
    standard_is_due,
)
from app.modules.standard_delivery.match import iaa_link_for_series, match_advertisers, series_stats
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.schema import VideoQuery
from app.modules.material_video.service import video_filters
from app.modules.standard_delivery.model import (
    GOAL_BY_CHARGE,
    DeliveryAutoRule,
    DeliveryAutoRuleRun,
    DeliveryAutoRuleSeries,
    DeliveryTaskDraft,
    DeliveryTemplate,
    OperationStatus,
)
from app.modules.standard_delivery.schema import DraftWrite

logger = logging.getLogger("adpilot")

_VIDEO_CAP = 800
_TITLE_CAP = 100
_TITLE_MIN = 5
_TITLE_MAX = 55


def _publish_ok(publish_time: str, start: date | None, end: date | None) -> bool:
    """没填上架区间就通过。填了则原串日期要落在闭区间。"""
    if start is None or end is None:
        return True
    text = str(publish_time or "")[:10]
    if len(text) < 10:
        return False
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return False
    return start <= day <= end


async def claim_standard(session: AsyncSession, rule_id: int, now: datetime) -> bool:
    """抢到一次执行权。已经跑过或还没到点则返回 False。"""
    clock = as_beijing(now)
    result = await session.execute(
        update(DeliveryAutoRule)
        .where(
            DeliveryAutoRule.id == rule_id,
            DeliveryAutoRule.is_deleted == 0,
            DeliveryAutoRule.is_enabled.is_(True),
            DeliveryAutoRule.ran_at.is_(None),
            or_(DeliveryAutoRule.schedule_start.is_(None), DeliveryAutoRule.schedule_start <= clock),
            or_(DeliveryAutoRule.schedule_end.is_(None), DeliveryAutoRule.schedule_end >= clock),
        )
        .values(ran_at=clock)
    )
    await session.commit()
    return int(result.rowcount or 0) == 1


async def due_standard_ids(session: AsyncSession, now: datetime) -> list[int]:
    """此刻应当执行的规则 id。"""
    clock = as_beijing(now)
    rows = await session.scalars(
        select(DeliveryAutoRule.id).where(
            DeliveryAutoRule.is_deleted == 0,
            DeliveryAutoRule.is_enabled.is_(True),
            DeliveryAutoRule.ran_at.is_(None),
            or_(DeliveryAutoRule.schedule_start.is_(None), DeliveryAutoRule.schedule_start <= clock),
            or_(DeliveryAutoRule.schedule_end.is_(None), DeliveryAutoRule.schedule_end >= clock),
        )
    )
    return [int(item) for item in rows.all()]


async def _accounts(session: AsyncSession, user_id: int, limit: int) -> list[AdvertiserAccount]:
    """每部剧取还没有项目的新账户，默认由规则上的个数决定。"""
    return await match_advertisers(session, user_id, limit, unused_only=True)


async def _videos(session: AsyncSession, series_id: int, user_id: int, limit: int) -> list[MaterialVideo]:
    rows = await session.scalars(
        select(MaterialVideo)
        .where(*video_filters(VideoQuery(series_id=series_id), user_id))
        .order_by(MaterialVideo.id)
        .limit(limit)
    )
    return list(rows.all())


async def _titles(session: AsyncSession, user_id: int, limit: int) -> list[MaterialTitle]:
    rows = await session.scalars(
        select(MaterialTitle)
        .where(MaterialTitle.uploader_id == user_id, MaterialTitle.is_deleted == 0)
        .order_by(MaterialTitle.id)
        .limit(_TITLE_CAP)
    )
    picked = [row for row in rows.all() if _TITLE_MIN <= len(row.title) <= _TITLE_MAX]
    return picked[:limit]


async def _snapshot_pairs(session: AsyncSession) -> list[tuple[Decimal, Decimal]]:
    rows = await session.execute(
        select(OeReportSnapshot.stat_cost, OeReportSnapshot.attribution_micro_game_0d_roi).where(
            OeReportSnapshot.is_deleted == 0
        )
    )
    return [(Decimal(cost), Decimal(roi)) for cost, roi in rows.all()]


async def _write_run(
    session: AsyncSession,
    *,
    rule_id: int,
    series_id: int | None,
    series_name: str,
    status: str,
    reason: str,
    draft_id: int | None,
    executed_at: datetime,
) -> None:
    session.add(
        DeliveryAutoRuleRun(
            rule_id=rule_id,
            series_id=series_id,
            series_name=series_name[:512] or "规则",
            status=status,
            reason=reason[:2000],
            draft_id=draft_id,
            executed_at=as_beijing(executed_at),
        )
    )
    await session.commit()


async def execute_standard_rule(session: AsyncSession, rule_id: int, now: datetime) -> int:
    """对已抢到的规则逐部短剧建草稿并确认提交。返回写入的结果行数。"""
    from app.modules.standard_delivery.service import create_draft
    from app.modules.standard_delivery.submit import submit_draft

    clock = as_beijing(now)
    rule = await session.get(DeliveryAutoRule, rule_id)
    if rule is None or rule.is_deleted:
        return 0
    template = await session.get(DeliveryTemplate, rule.template_id)
    if template is None or template.is_deleted:
        await _write_run(
            session,
            rule_id=rule_id,
            series_id=None,
            series_name="规则",
            status="failed",
            reason="模板不存在",
            draft_id=None,
            executed_at=clock,
        )
        return 1
    series_ids = list(
        await session.scalars(
            select(DeliveryAutoRuleSeries.series_id)
            .where(DeliveryAutoRuleSeries.rule_id == rule_id, DeliveryAutoRuleSeries.is_deleted == 0)
            .order_by(DeliveryAutoRuleSeries.sort_order, DeliveryAutoRuleSeries.id)
        )
    )
    series_rows = list(
        await session.scalars(
            select(ManhuaSeries).where(ManhuaSeries.id.in_(series_ids), ManhuaSeries.is_deleted == 0)
        )
    ) if series_ids else []
    by_id = {int(row.id): row for row in series_rows}
    ad_budget = template.ad_budget
    title_limit = int(template.titles_per_ad or 10)
    video_limit = min(int(rule.max_videos_per_series), _VIDEO_CAP)
    titles = await _titles(session, int(rule.pitcher_user_id), title_limit)
    written = 0
    allowed = {str(template.charge_mode)}
    if not series_ids:
        await _write_run(
            session,
            rule_id=rule_id,
            series_id=None,
            series_name="规则",
            status="failed",
            reason="规则没有短剧",
            draft_id=None,
            executed_at=clock,
        )
        return 1
    for series_id in series_ids:
        series = by_id.get(int(series_id))
        name = series.book_name if series is not None else f"短剧{series_id}"
        if series is None:
            await _write_run(
                session,
                rule_id=rule_id,
                series_id=None,
                series_name=name,
                status="failed",
                reason="短剧不存在",
                draft_id=None,
                executed_at=clock,
            )
            written += 1
            continue
        videos = await _videos(session, int(series.id), int(rule.pitcher_user_id), video_limit)
        accounts = await _accounts(session, int(rule.pitcher_user_id), int(rule.accounts_per_series))
        stats = await series_stats(session, int(series.id), series.book_name)
        snapshot_ok = snapshots_satisfy(
            stats,
            cost_min=rule.cost_min,
            cost_max=rule.cost_max,
            recovery_min=rule.roi_min,
            recovery_max=rule.roi_max,
        )
        link = await iaa_link_for_series(session, int(series.id))
        reason = series_block_reason(
            videos=[int(video.id) for video in videos],
            titles=[int(title.id) for title in titles],
            accounts=[int(account.advertiser_id) for account in accounts],
            playlet_id=1,
            publish_ok=_publish_ok(series.publish_time, rule.publish_start, rule.publish_end),
            snapshot_ok=snapshot_ok,
        )
        if rule.no_bid_only and template.bid_type != "NO_BID":
            reason = reason or "模板不是最大转化"
        if ad_budget is None or ad_budget <= 0:
            reason = reason or "模板没有广告预算"
        if link is None or not link.promotion_url:
            reason = reason or "没有可匹配的 IAA 推广链"
        if reason:
            await _write_run(
                session,
                rule_id=rule_id,
                series_id=int(series.id),
                series_name=series.book_name,
                status="failed",
                reason=reason,
                draft_id=None,
                executed_at=clock,
            )
            written += 1
            continue
        draft_id: int | None = None
        try:
            body = DraftWrite(
                template_id=int(template.id),
                advertiser_ids=[int(account.advertiser_id) for account in accounts],
                series_id=int(series.id),
                video_ids=[int(video.id) for video in videos],
                title_ids=[int(title.id) for title in titles],
                ad_budget=ad_budget,
                optimize_goal=GOAL_BY_CHARGE[template.charge_mode],
                album_url=str(link.promotion_url),
                project_operation=OperationStatus.ENABLE,
            )
            saved = await create_draft(session, body, int(rule.pitcher_user_id), allowed)
            draft_id = int(saved["id"])
            await submit_draft(session, draft_id, int(rule.pitcher_user_id), allowed)
        except ApiError as exc:
            await session.rollback()
            await _write_run(
                session,
                rule_id=rule_id,
                series_id=int(series.id),
                series_name=series.book_name,
                status="failed",
                reason=exc.message,
                draft_id=draft_id,
                executed_at=clock,
            )
            written += 1
            continue
        except Exception as exc:
            logger.exception("标准自动规则 %s 短剧 %s 执行失败", rule_id, series.id)
            await session.rollback()
            await _write_run(
                session,
                rule_id=rule_id,
                series_id=int(series.id),
                series_name=series.book_name,
                status="failed",
                reason=str(exc)[:2000] or "执行失败",
                draft_id=draft_id,
                executed_at=clock,
            )
            written += 1
            continue
        await _write_run(
            session,
            rule_id=rule_id,
            series_id=int(series.id),
            series_name=series.book_name,
            status="success",
            reason="",
            draft_id=draft_id,
            executed_at=clock,
        )
        written += 1
    return written


async def maybe_run_standard(session: AsyncSession, rule_id: int, now: datetime | None = None) -> int:
    """创建或打开立即执行时调用。没到点就什么都不做。"""
    clock = as_beijing(now or beijing_now())
    rule = await session.get(DeliveryAutoRule, rule_id)
    if rule is None:
        return 0
    if not standard_is_due(
        is_enabled=bool(rule.is_enabled),
        schedule_start=rule.schedule_start,
        schedule_end=rule.schedule_end,
        ran_at=rule.ran_at,
        now=clock,
    ):
        return 0
    if not await claim_standard(session, rule_id, clock):
        return 0
    return await execute_standard_rule(session, rule_id, clock)


async def run_due_standard(session: AsyncSession, now: datetime) -> int:
    """跑所有到点且还没执行的标准自动规则。一部短剧失败不影响其余。"""
    ran = 0
    for rule_id in await due_standard_ids(session, now):
        try:
            if await claim_standard(session, rule_id, now):
                await execute_standard_rule(session, rule_id, now)
                ran += 1
        except Exception:
            logger.exception("标准自动规则 %s 执行失败", rule_id)
    return ran


async def run_due_drafts(session: AsyncSession, now: datetime) -> int:
    """预约窗口内、还没提交的草稿到点确认提交。没有预约的不自动提交。"""
    clock = as_beijing(now)
    draft_ids = list(
        await session.scalars(
            select(DeliveryTaskDraft.id).where(
                DeliveryTaskDraft.is_deleted == 0,
                DeliveryTaskDraft.submitted_at.is_(None),
                DeliveryTaskDraft.schedule_start.is_not(None),
                DeliveryTaskDraft.schedule_start <= clock,
                DeliveryTaskDraft.schedule_end >= clock,
            )
        )
    )
    from app.modules.standard_delivery.submit import submit_draft

    submitted = 0
    for draft_id in draft_ids:
        draft = await session.get(DeliveryTaskDraft, int(draft_id))
        if draft is None or draft.is_deleted or draft.submitted_at is not None:
            continue
        try:
            await submit_draft(session, int(draft.id), int(draft.pitcher_user_id), {str(draft.charge_mode)})
            submitted += 1
        except Exception:
            logger.exception("预约草稿 %s 提交失败", draft_id)
            await session.rollback()
    return submitted
