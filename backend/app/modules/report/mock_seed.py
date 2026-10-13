"""把库里已有的报表夹具接到中台任务上，供日表刷新使用。

旧快照 `oe_report_snapshot` 的 8001、8002，以及已经落在小时表里、
但没有任务归属的项目，列表都看不到。这里补归属和对应的小时行，幂等。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import BEIJING, beijing_now
from app.modules.account.model import AdvertiserAccount, OeDeliveryReport
from app.modules.standard_delivery.model import (
    DeliveryTaskAccount,
    DeliveryTaskDraft,
    DeliveryTaskProject,
    DeliveryTaskPromotion,
)
from app.modules.uni_native_task.model import NativeTaskStatus, UniNativeTask, UniNativeTaskAccount

# 启动种子里的两行旧快照。项目号是本夹具自己的，广告号沿用 8001、8002。
_SEED_ADVERTISER = 1873916032590219
_SEED_PROJECT = 80010001
_SEED_PROMOTIONS = (
    (8001, Decimal("120.00"), Decimal("36.00")),
    (8002, Decimal("10.00"), Decimal("12.00")),
)

# 本机已经拉取的小时数据。项目和两条广告都在原始表里，缺中台归属。
_PULLED_ADVERTISER = 1877368580368602
_PULLED_PROJECT = 7691188278174826546
_PULLED_PROMOTIONS = (7691188146411814975, 7691188154167427115)

_PITCHER_ID = 3
_SERIES_PULLED = 1
_SERIES_SEED = 2
_STANDARD_IAP_TEMPLATE = 7
_UNI_TEMPLATE = 10
_PANEL = "中额"


async def ensure_report_mock(session: AsyncSession) -> None:
    """补齐夹具归属，并把这些日期的日表重刷一遍。"""
    await _ensure_seed_hours(session)
    await _ensure_standard(
        session,
        ocean_project_id=_PULLED_PROJECT,
        promotion_ids=_PULLED_PROMOTIONS,
        advertiser_ocean_id=_PULLED_ADVERTISER,
        template_id=_STANDARD_IAP_TEMPLATE,
        series_id=_SERIES_PULLED,
        charge_mode="IAP",
        optimize_goal="AD_CONVERT_TYPE_PAY",
        panel=_PANEL,
        project_budget=Decimal("800.00"),
    )
    await _ensure_standard(
        session,
        ocean_project_id=_SEED_PROJECT,
        promotion_ids=tuple(item[0] for item in _SEED_PROMOTIONS),
        advertiser_ocean_id=_SEED_ADVERTISER,
        template_id=5,
        series_id=_SERIES_SEED,
        charge_mode="IAA",
        optimize_goal="AD_CONVERT_TYPE_ACTIVE",
        panel="",
        project_budget=Decimal("300.00"),
    )
    await _ensure_uni(session)
    await session.flush()


async def _ensure_seed_hours(session: AsyncSession) -> None:
    """旧快照只有广告和消耗。补成今天两个小时的标准投放原始行。"""
    existing = await session.scalar(
        select(OeDeliveryReport.id).where(
            OeDeliveryReport.cdp_promotion_id == _SEED_PROMOTIONS[0][0],
            OeDeliveryReport.is_deleted == 0,
        )
    )
    if existing is not None:
        return
    now = beijing_now()
    day = now.astimezone(BEIJING).date().isoformat()
    for hour in (10, 14):
        stamp = f"{day} {hour:02d}:00:00"
        for promotion_id, cost, pay in _SEED_PROMOTIONS:
            session.add(
                OeDeliveryReport(
                    advertiser_id=_SEED_ADVERTISER,
                    stat_time_hour=stamp,
                    cdp_project_id=_SEED_PROJECT,
                    cdp_project_name="夹具项目8001",
                    cdp_promotion_id=promotion_id,
                    cdp_promotion_name=f"夹具广告{promotion_id}",
                    stat_cost=cost,
                    stat_pay_amount=pay,
                    attribution_game_in_app_ltv_1day=pay,
                    attribution_game_in_app_ltv_8days=pay,
                    attribution_micro_game_0d_ltv=pay,
                    attribution_micro_game_7d_ltv=pay,
                    show_cnt=1000,
                    click_cnt=50,
                    convert_cnt=5,
                    active=8,
                    synced_at=now,
                )
            )
    await session.flush()


async def _ensure_standard(
    session: AsyncSession,
    *,
    ocean_project_id: int,
    promotion_ids: tuple[int, ...],
    advertiser_ocean_id: int,
    template_id: int,
    series_id: int,
    charge_mode: str,
    optimize_goal: str,
    panel: str,
    project_budget: Decimal,
) -> None:
    found = await session.scalar(
        select(DeliveryTaskProject.id).where(
            DeliveryTaskProject.ocean_project_id == ocean_project_id,
            DeliveryTaskProject.is_deleted == 0,
        )
    )
    if found is not None:
        return
    account = await _advertiser(session, advertiser_ocean_id)
    draft = DeliveryTaskDraft(
        template_id=template_id,
        charge_mode=charge_mode,
        pitcher_user_id=_PITCHER_ID,
        series_id=series_id,
        project_budget=project_budget,
        ad_budget=Decimal("100.00"),
        optimize_goal=optimize_goal,
        submitted_at=beijing_now(),
    )
    session.add(draft)
    await session.flush()
    session.add(
        DeliveryTaskAccount(
            task_id=draft.id,
            advertiser_account_id=account.id,
            sort_order=0,
            ocean_project_id=ocean_project_id if len(promotion_ids) else None,
        )
    )
    project = DeliveryTaskProject(
        task_id=draft.id,
        advertiser_account_id=account.id,
        bid_panel=panel,
        ocean_project_id=ocean_project_id,
        sort_order=0,
    )
    session.add(project)
    await session.flush()
    for index, promotion_id in enumerate(promotion_ids):
        session.add(
            DeliveryTaskPromotion(
                task_project_id=project.id,
                ocean_promotion_id=promotion_id,
                sort_order=index,
            )
        )
    await session.flush()


async def _ensure_uni(session: AsyncSession) -> None:
    found = await session.scalar(
        select(UniNativeTaskAccount.id).where(
            UniNativeTaskAccount.ocean_project_id == _PULLED_PROJECT,
            UniNativeTaskAccount.is_deleted == 0,
        )
    )
    if found is not None:
        return
    account = await _advertiser(session, _PULLED_ADVERTISER)
    task = UniNativeTask(
        template_id=_UNI_TEMPLATE,
        pitcher_user_id=_PITCHER_ID,
        series_id=_SERIES_PULLED,
        project_budget=Decimal("500.00"),
        roi_coefficient=Decimal("1.250"),
        status=NativeTaskStatus.DONE,
        materials_uploaded=True,
        executed_at=beijing_now(),
    )
    session.add(task)
    await session.flush()
    session.add(
        UniNativeTaskAccount(
            task_id=task.id,
            douyin_account_id=1,
            advertiser_account_id=account.id,
            sort_order=0,
            ocean_project_id=_PULLED_PROJECT,
            ocean_promotion_id=_PULLED_PROMOTIONS[0],
        )
    )
    await session.flush()


async def _advertiser(session: AsyncSession, ocean_id: int) -> AdvertiserAccount:
    found = await session.scalar(
        select(AdvertiserAccount).where(AdvertiserAccount.advertiser_id == ocean_id)
    )
    if found is not None:
        return found
    sample = await session.get(AdvertiserAccount, 1)
    now = beijing_now()
    row = AdvertiserAccount(
        organization_id=sample.organization_id if sample is not None else 1,
        oe_app_id=sample.oe_app_id if sample is not None else 1,
        advertiser_id=ocean_id,
        name="报表夹具广告主",
        valid_balance=Decimal("100.00"),
        company_name="报表夹具",
        balance_synced_at=now,
        company_synced_at=now,
        pitcher_user_id=_PITCHER_ID,
        sync_status="active",
    )
    session.add(row)
    await session.flush()
    return row


