"""巨量广告列表的联调数据。只在 mock 启动时写一次，已有同号的项目或广告就跳过。

列表只认 oe_project、oe_promotion，效果数按项目号、广告号从 oe_material_report 加总。
报表夹具已经把一个标准付费项目和下面两条广告写进素材小时表和投放任务表，这里补上项目行和广告行。
全域另建一个项目和一条广告，并在首次写入那天补两个小时的素材行，全域项目页才有消耗。
主体、短剧、抖音号、预算和 ROI 都从夹具任务上读。夹具不在库里时不写。
全域项目没有挂在投放任务上，报表日表刷新时会丢掉这些素材行，不进利润和素材报表。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import BEIJING, beijing_now
from app.modules.account.model import AdvertiserAccount, OeMaterialReport, OeProject, OePromotion
from app.modules.standard_delivery.model import (
    DeliveryTaskDraft,
    DeliveryTaskProject,
    DeliveryTaskPromotion,
    DeliveryTemplate,
)
from app.modules.uni_native_task.model import UniNativeTask, UniNativeTaskAccount

# 报表夹具里已有素材小时数据的项目。标准付费，模板上挂的主体决定页签。
_STANDARD_PROJECT = 7691188278174826546
# 全域夹具任务也指向上面这个项目号。全域项目另用一组号。
_UNI_PROJECT = 80030001
_UNI_PROMOTION = 80030002
_UNI_PROJECT_NAME = "全域夹具项目"
_UNI_PROMOTION_NAME = "全域夹具广告"
_UNI_MATERIAL = 80030003
_UNI_MATERIAL_NAME = "全域夹具素材"
# 和报表夹具广告 8001 每小时的数一致。
_UNI_HOURS = (10, 14)
_UNI_HOUR_COST = Decimal("120.00")
_UNI_HOUR_PAY = Decimal("36.00")


def project_template(budget: Decimal | None, roi_goal: Decimal | None = None) -> dict:
    """和创建项目时存下的形状一致：预算和 ROI 系数在 delivery_setting 里。"""
    setting: dict = {"budget_mode": "BUDGET_MODE_DAY"}
    if budget is not None:
        setting["budget"] = float(budget)
    if roi_goal is not None:
        setting["roi_goal"] = float(roi_goal)
    return {"delivery_setting": setting}


async def ensure_ocean_ads_mock(session: AsyncSession) -> None:
    """补齐标准和全域各一个项目，以及下面的广告。"""
    await _ensure_standard(session)
    await _ensure_uni(session)
    await session.flush()
    await _ensure_uni_hours(session)
    await session.flush()


async def _ensure_standard(session: AsyncSession) -> None:
    if await _project_exists(session, _STANDARD_PROJECT):
        return
    found = (
        await session.execute(
            select(DeliveryTaskProject, DeliveryTaskDraft, DeliveryTemplate, AdvertiserAccount)
            .join(DeliveryTaskDraft, DeliveryTaskDraft.id == DeliveryTaskProject.task_id)
            .join(DeliveryTemplate, DeliveryTemplate.id == DeliveryTaskDraft.template_id)
            .join(AdvertiserAccount, AdvertiserAccount.id == DeliveryTaskProject.advertiser_account_id)
            .where(
                DeliveryTaskProject.ocean_project_id == _STANDARD_PROJECT,
                DeliveryTaskProject.is_deleted == 0,
            )
        )
    ).first()
    if found is None:
        return
    task_project, draft, template, account = found
    advertiser_id = int(account.advertiser_id)
    project_name, promotion_names = await _report_names(session, advertiser_id, _STANDARD_PROJECT)
    budget = draft.project_budget if draft.project_budget is not None else template.project_budget
    session.add(
        OeProject(
            advertiser_id=advertiser_id,
            ocean_project_id=_STANDARD_PROJECT,
            name=project_name or f"夹具项目{_STANDARD_PROJECT}",
            subject_id=template.subject_id,
            opt_status="ENABLE",
            template=project_template(budget),
        )
    )
    promotion_ids = (
        await session.scalars(
            select(DeliveryTaskPromotion.ocean_promotion_id)
            .where(
                DeliveryTaskPromotion.task_project_id == task_project.id,
                DeliveryTaskPromotion.is_deleted == 0,
            )
            .order_by(DeliveryTaskPromotion.sort_order)
        )
    ).all()
    for promotion_id in promotion_ids:
        if await _promotion_exists(session, advertiser_id, int(promotion_id)):
            continue
        session.add(
            OePromotion(
                advertiser_id=advertiser_id,
                promotion_id=int(promotion_id),
                ocean_project_id=_STANDARD_PROJECT,
                series_id=draft.series_id,
                douyin_account_id=draft.douyin_account_id,
                opt_status="ENABLE",
                name=promotion_names.get(int(promotion_id)) or f"夹具广告{promotion_id}",
                budget=draft.ad_budget,
            )
        )


async def _ensure_uni(session: AsyncSession) -> None:
    if await _project_exists(session, _UNI_PROJECT):
        return
    found = (
        await session.execute(
            select(UniNativeTask, UniNativeTaskAccount, DeliveryTemplate, AdvertiserAccount)
            .join(UniNativeTaskAccount, UniNativeTaskAccount.task_id == UniNativeTask.id)
            .join(DeliveryTemplate, DeliveryTemplate.id == UniNativeTask.template_id)
            .join(AdvertiserAccount, AdvertiserAccount.id == UniNativeTaskAccount.advertiser_account_id)
            .where(
                UniNativeTaskAccount.ocean_project_id == _STANDARD_PROJECT,
                UniNativeTaskAccount.is_deleted == 0,
                UniNativeTask.is_deleted == 0,
            )
        )
    ).first()
    if found is None:
        return
    task, link, template, account = found
    advertiser_id = int(account.advertiser_id)
    session.add(
        OeProject(
            advertiser_id=advertiser_id,
            ocean_project_id=_UNI_PROJECT,
            name=_UNI_PROJECT_NAME,
            subject_id=template.subject_id,
            opt_status="ENABLE",
            template=project_template(task.project_budget, task.roi_coefficient),
        )
    )
    if await _promotion_exists(session, advertiser_id, _UNI_PROMOTION):
        return
    session.add(
        OePromotion(
            advertiser_id=advertiser_id,
            promotion_id=_UNI_PROMOTION,
            ocean_project_id=_UNI_PROJECT,
            series_id=task.series_id,
            douyin_account_id=link.douyin_account_id,
            opt_status="ENABLE",
            name=_UNI_PROMOTION_NAME,
        )
    )


def uni_hour_rows(advertiser_id: int, day: str, synced_at: object) -> list[OeMaterialReport]:
    """全域夹具广告在这一天的素材小时行。"""
    return [
        OeMaterialReport(
            advertiser_id=advertiser_id,
            stat_time_hour=f"{day} {hour:02d}:00:00",
            material_id=_UNI_MATERIAL,
            ad_platform_material_name=_UNI_MATERIAL_NAME,
            cdp_promotion_id=_UNI_PROMOTION,
            cdp_promotion_name=_UNI_PROMOTION_NAME,
            cdp_project_id=_UNI_PROJECT,
            cdp_project_name=_UNI_PROJECT_NAME,
            stat_cost=_UNI_HOUR_COST,
            attribution_billing_game_in_app_ltv_1day=_UNI_HOUR_PAY,
            stat_pay_amount=_UNI_HOUR_PAY,
            show_cnt=1000,
            click_cnt=50,
            convert_cnt=5,
            active=8,
            game_addiction=0,
            synced_at=synced_at,
        )
        for hour in _UNI_HOURS
    ]


async def _ensure_uni_hours(session: AsyncSession) -> None:
    """全域项目还在、这条广告一行素材数据都没有时，补首次写入那天的两个小时。"""
    project = await session.scalar(
        select(OeProject).where(OeProject.ocean_project_id == _UNI_PROJECT, OeProject.is_deleted == 0)
    )
    if project is None:
        return
    existing = await session.scalar(
        select(OeMaterialReport.id).where(
            OeMaterialReport.advertiser_id == project.advertiser_id,
            OeMaterialReport.cdp_promotion_id == _UNI_PROMOTION,
        )
    )
    if existing is not None:
        return
    now = beijing_now()
    day = now.astimezone(BEIJING).date().isoformat()
    for row in uni_hour_rows(int(project.advertiser_id), day, now):
        session.add(row)


async def _project_exists(session: AsyncSession, ocean_project_id: int) -> bool:
    """软删过的也算有，页面上删掉的不在重启后冒出来。"""
    found = await session.scalar(select(OeProject.id).where(OeProject.ocean_project_id == ocean_project_id))
    return found is not None


async def _promotion_exists(session: AsyncSession, advertiser_id: int, promotion_id: int) -> bool:
    found = await session.scalar(
        select(OePromotion.id).where(
            OePromotion.advertiser_id == advertiser_id,
            OePromotion.promotion_id == promotion_id,
        )
    )
    return found is not None


async def _report_names(
    session: AsyncSession, advertiser_id: int, ocean_project_id: int
) -> tuple[str | None, dict[int, str]]:
    """项目名和广告名用素材小时表里已有的名字。"""
    rows = await session.execute(
        select(
            OeMaterialReport.cdp_promotion_id,
            func.max(OeMaterialReport.cdp_project_name),
            func.max(OeMaterialReport.cdp_promotion_name),
        )
        .where(
            OeMaterialReport.advertiser_id == advertiser_id,
            OeMaterialReport.cdp_project_id == ocean_project_id,
            OeMaterialReport.is_deleted == 0,
        )
        .group_by(OeMaterialReport.cdp_promotion_id)
    )
    project_name: str | None = None
    names: dict[int, str] = {}
    for promotion_id, report_project_name, promotion_name in rows.all():
        if report_project_name and project_name is None:
            project_name = str(report_project_name)
        if promotion_name:
            names[int(promotion_id)] = str(promotion_name)
    return project_name, names
