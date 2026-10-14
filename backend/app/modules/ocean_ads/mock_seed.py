"""巨量广告列表联调用的项目模板和全域素材小时行。

项目模板把预算和 ROI 系数放进 delivery_setting。
全域夹具按固定项目号、广告号和素材号，在指定那天写出两个小时的素材行。
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.account.model import OeMaterialReport

# 全域夹具的项目、广告和素材。
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
