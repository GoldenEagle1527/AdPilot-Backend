"""确认提交一条标准投放草稿。

项目号、商品号、主图号都从已装上的客户端拿。报文留在返回值里，本模块不发 HTTP。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount, ProductLibrary
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.oceanengine.delivery import create_project, upload_image, upload_product
from app.modules.oceanengine.schema import ProductCreate, ProjectCreate
from app.modules.standard_delivery.crud import (
    SeriesBrief,
    accounts_by_drafts,
    get_draft_row,
    get_library_by_id,
    get_standard_douyin,
    titles_by_drafts,
    videos_by_drafts,
)
from app.modules.standard_delivery.model import (
    ChargeMode,
    DeliveryTaskDraft,
    DeliveryTemplate,
    OceanDeliveryMode,
    Placement,
    ScheduleType,
)

_TITLE_MIN = 5
_TITLE_MAX = 30
_MANUAL_VIDEO_CAP = 10
_IMAGE_MODE = {
    "vertical_video": "CREATIVE_IMAGE_MODE_VIDEO_VERTICAL",
    "horizontal_video": "CREATIVE_IMAGE_MODE_VIDEO",
}


def slice_materials(
    videos: list[Any],
    titles: list[Any],
    *,
    videos_per_ad: int,
    titles_per_ad: int,
    ads_per_account: int,
    account_count: int,
) -> list[list[tuple[list[Any], list[Any]]]]:
    """按保存顺序切块。账户之间共用一个游标，不够一整块就停，不回头取。"""
    video_at = 0
    title_at = 0
    per_account: list[list[tuple[list[Any], list[Any]]]] = []
    for _account in range(account_count):
        promotions: list[tuple[list[Any], list[Any]]] = []
        for _ad in range(ads_per_account):
            if video_at + videos_per_ad > len(videos) or title_at + titles_per_ad > len(titles):
                break
            promotions.append(
                (
                    list(videos[video_at : video_at + videos_per_ad]),
                    list(titles[title_at : title_at + titles_per_ad]),
                )
            )
            video_at += videos_per_ad
            title_at += titles_per_ad
        per_account.append(promotions)
    return per_account


def _num(value: Decimal) -> float:
    """金额和 ROI 交给 JSON 时用数字。"""
    return float(value)


def _project_name(book_name: str) -> str:
    """短剧前两个字 + NB + 月日时分。"""
    return f"{book_name[:2]}NB{beijing_now().strftime('%m%d%H%M')}"


def _delivery_range(placement: str) -> dict[str, Any]:
    """版位换成巨量广告位。通投不带 inventory_type。"""
    if placement == Placement.UNIVERSAL:
        return {"inventory_catalog": "UNIVERSAL_SMART"}
    inventory = ["INVENTORY_AWEME_FEED"]
    if placement == Placement.AWEME_FEED:
        inventory.append("INVENTORY_FEED")
    return {"inventory_catalog": "MANUAL", "inventory_type": inventory}


def _picked_placement(draft: DeliveryTaskDraft, template: DeliveryTemplate) -> str:
    """草稿写了版位就用草稿，否则用模板。手动版位本身带抖音信息流。"""
    placement = draft.placement or template.placement
    if placement not in (Placement.AWEME, Placement.AWEME_FEED, Placement.UNIVERSAL):
        raise ApiError(400, "广告位置不能为空")
    return str(placement)


def _picked_budget(draft: DeliveryTaskDraft, template: DeliveryTemplate) -> Decimal:
    """草稿写了项目预算就用草稿，否则用模板。"""
    budget = draft.project_budget if draft.project_budget is not None else template.project_budget
    if budget is None:
        raise ApiError(400, "项目预算不能为空")
    return budget


def _picked_operation(draft: DeliveryTaskDraft, template: DeliveryTemplate) -> str:
    """广告开关以草稿为准。草稿没写时用模板上的广告状态。"""
    operation = draft.promotion_operation or template.promotion_operation
    if operation not in ("ENABLE", "DISABLE"):
        raise ApiError(400, "广告开关不能为空")
    return str(operation)


def _picked_audience(template: DeliveryTemplate) -> dict[str, Any]:
    """定向只在模板上。不限不带城市；选了行政区域才带城市编码。"""
    if template.district == "REGION" and template.city_codes:
        return {"district": "REGION", "city": [int(code) for code in template.city_codes]}
    return {"district": "NONE"}


def _stored_image_id(template: DeliveryTemplate) -> str | None:
    """模板上已有 img- 主图时直接用，不再上传新图。"""
    image_id = (template.product_image_id or "").strip()
    if image_id.startswith("img-"):
        return image_id
    return None


def _delivery_setting(template: DeliveryTemplate, draft: DeliveryTaskDraft, budget: Decimal) -> dict[str, Any]:
    """项目排期和日预算。手动投放不把 ROI 放在项目上。"""
    setting: dict[str, Any] = {
        "schedule_type": template.schedule_type,
        "bid_type": template.bid_type,
        "budget_mode": "BUDGET_MODE_DAY",
        "budget": _num(budget),
    }
    if template.schedule_type == ScheduleType.START_END:
        setting["start_time"] = template.schedule_start_date.isoformat()
        setting["end_time"] = template.schedule_end_date.isoformat()
    if template.schedule_time:
        setting["schedule_time"] = template.schedule_time
    if (
        template.ocean_delivery_mode == OceanDeliveryMode.PROCEDURAL
        and draft.charge_mode == ChargeMode.IAP
        and template.roi_goal is not None
    ):
        setting["roi_goal"] = _num(template.roi_goal)
        setting["deep_bid_type"] = "ROI_COEFFICIENT"
    return setting


def _optimize_goal(draft: DeliveryTaskDraft) -> dict[str, Any]:
    """免费只传激活。付费再加付费 ROI。不带 asset_ids。"""
    goal: dict[str, Any] = {"external_action": draft.optimize_goal}
    if draft.charge_mode == ChargeMode.IAP:
        goal["deep_external_action"] = "AD_CONVERT_TYPE_PURCHASE_ROI"
    return goal


def _reject_unready(template: DeliveryTemplate, draft: DeliveryTaskDraft) -> None:
    """整单校验。不合格就不调用客户端。"""
    if template.ocean_delivery_mode not in (OceanDeliveryMode.MANUAL, OceanDeliveryMode.PROCEDURAL):
        raise ApiError(400, "模板还不能确认提交")
    if template.videos_per_ad is None or template.titles_per_ad is None or template.ads_per_account is None:
        raise ApiError(400, "模板还不能确认提交")
    if template.schedule_type == ScheduleType.START_END and (
        template.schedule_start_date is None or template.schedule_end_date is None
    ):
        raise ApiError(400, "模板还不能确认提交")
    if not template.ad_source or not template.product_name:
        raise ApiError(400, "模板还不能确认提交")
    if template.ocean_delivery_mode == OceanDeliveryMode.MANUAL and template.videos_per_ad > _MANUAL_VIDEO_CAP:
        raise ApiError(400, "手动投放每个广告最多 10 个视频")
    if (
        template.ocean_delivery_mode == OceanDeliveryMode.PROCEDURAL
        and draft.charge_mode == ChargeMode.IAP
        and template.roi_goal is None
    ):
        raise ApiError(400, "付费自动投放需要 ROI 目标")
    if not (draft.album_url or "").strip():
        raise ApiError(400, "专辑链接不能为空")
    if draft.project_operation not in ("ENABLE", "DISABLE"):
        raise ApiError(400, "项目开关不能为空")


def _reject_titles(titles: list[MaterialTitle]) -> None:
    """切进广告的标题有一条长度不对，整单拒绝。"""
    if any(not _TITLE_MIN <= len(title.title) <= _TITLE_MAX for title in titles):
        raise ApiError(400, "标题长度须为 5–30 个字")


def _video_material(video: MaterialVideo) -> dict[str, Any]:
    """素材库主键。没有巨量视频号时不补。"""
    return {
        "material_id": int(video.id),
        "image_mode": _IMAGE_MODE.get(video.material_type, "CREATIVE_IMAGE_MODE_VIDEO_VERTICAL"),
    }


def _promotion_body(
    *,
    advertiser_id: int,
    project_id: int,
    name: str,
    draft: DeliveryTaskDraft,
    template: DeliveryTemplate,
    douyin: DouyinAccount,
    image_id: str,
    operation: str,
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
) -> dict[str, Any]:
    """一条广告的报文。专辑链接只用草稿上的 album_url，不抄剧场推广链。"""
    body: dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "project_id": project_id,
        "name": name,
        "operation": operation,
        "source": template.ad_source,
        "budget": _num(draft.ad_budget),
        "budget_mode": "BUDGET_MODE_DAY",
        "native_setting": {"aweme_id": douyin.aweme_id},
        "promotion_materials": {
            "playlet_series_url_list": [draft.album_url],
            "video_material_list": [_video_material(video) for video in videos],
            "title_material_list": [{"title": title.title} for title in titles],
            "product_info": {
                "titles": [template.product_name],
                "image_ids": [image_id],
                "selling_points": list(template.selling_points or []),
            },
            "call_to_action_buttons": list(template.call_to_action_buttons or []),
        },
    }
    if template.ocean_delivery_mode == OceanDeliveryMode.MANUAL and template.roi_goal is not None:
        body["roi_goal"] = _num(template.roi_goal)
    return body


def _project_body(
    *,
    advertiser_id: int,
    name: str,
    draft: DeliveryTaskDraft,
    template: DeliveryTemplate,
    douyin: DouyinAccount,
    library: ProductLibrary,
    product_id: int,
    placement: str,
    budget: Decimal,
    audience: dict[str, Any],
) -> dict[str, Any]:
    """创建项目的报文。定向、版位和项目预算已经按草稿是否覆盖解析过。"""
    return {
        "advertiser_id": advertiser_id,
        "name": name,
        "landing_type": "MICRO_GAME",
        "marketing_goal": "VIDEO_AND_IMAGE",
        "ad_type": "ALL",
        "delivery_mode": template.ocean_delivery_mode,
        "operation": draft.project_operation,
        "delivery_range": _delivery_range(placement),
        "delivery_setting": _delivery_setting(template, draft, budget),
        "optimize_goal": _optimize_goal(draft),
        "related_product": {
            "product_platform_id": int(library.library_no),
            "product_id": product_id,
            "product_setting": "SINGLE",
        },
        "audience": audience,
        "micro_promotion_type": "AWEME",
        "native_setting": {"aweme_id": douyin.aweme_id},
    }


async def submit_loaded(
    session: AsyncSession,
    draft: DeliveryTaskDraft,
    template: DeliveryTemplate,
    subject: DeliverySubject,
    douyin: DouyinAccount,
    series: SeriesBrief,
    library: ProductLibrary,
    accounts: list[AdvertiserAccount],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
) -> dict[str, Any]:
    """按账户建项目，再按模板的条数切广告。不改模板的 delivery_mode。

    草稿没写的版位、项目预算、广告开关用模板。定向、商品选择方式、主图和标题模式只在模板上。
    草稿上的标题列表视为对标题模式的覆盖。专辑链接仍只用草稿的 album_url。
    """
    _reject_unready(template, draft)
    placement = _picked_placement(draft, template)
    budget = _picked_budget(draft, template)
    operation = _picked_operation(draft, template)
    audience = _picked_audience(template)
    stored_image = _stored_image_id(template)
    name = _project_name(series.book_name)
    slices = slice_materials(
        videos,
        titles,
        videos_per_ad=int(template.videos_per_ad),
        titles_per_ad=int(template.titles_per_ad),
        ads_per_account=int(template.ads_per_account),
        account_count=len(accounts),
    )
    _reject_titles([title for chunk in slices for _videos, chunk_titles in chunk for title in chunk_titles])
    built: list[dict[str, Any]] = []
    for account, promotions in zip(accounts, slices, strict=True):
        advertiser_id = int(account.advertiser_id)
        product = await upload_product(
            session,
            ProductCreate(
                advertiser_id=advertiser_id,
                library_no=int(library.library_no),
                book_name=series.book_name,
            ),
        )
        if stored_image is None:
            image = await upload_image(session, advertiser_id, "product.png")
            image_id = str(image["image_id"])
        else:
            image_id = stored_image
        project = _project_body(
            advertiser_id=advertiser_id,
            name=name,
            draft=draft,
            template=template,
            douyin=douyin,
            library=library,
            product_id=int(product["product_id"]),
            placement=placement,
            budget=budget,
            audience=audience,
        )
        created = await create_project(
            session,
            ProjectCreate(
                advertiser_id=advertiser_id,
                name=name,
                landing_type="MICRO_GAME",
                marketing_goal="VIDEO_AND_IMAGE",
                ad_type="ALL",
                delivery_mode=template.ocean_delivery_mode,
                subject_id=int(subject.id),
                template={
                    "delivery_range": project["delivery_range"],
                    "delivery_setting": project["delivery_setting"],
                    "optimize_goal": project["optimize_goal"],
                    "related_product": project["related_product"],
                    "audience": project["audience"],
                    "micro_promotion_type": project["micro_promotion_type"],
                    "native_setting": project["native_setting"],
                    "operation": project["operation"],
                },
            ),
        )
        project_id = int(created["project_id"])
        built.append(
            {
                "advertiser_id": advertiser_id,
                "project_id": project_id,
                "product_id": int(product["product_id"]),
                "image_id": image_id,
                "project": project,
                "promotions": [
                    _promotion_body(
                        advertiser_id=advertiser_id,
                        project_id=project_id,
                        name=name,
                        draft=draft,
                        template=template,
                        douyin=douyin,
                        image_id=image_id,
                        operation=operation,
                        videos=chunk_videos,
                        titles=chunk_titles,
                    )
                    for chunk_videos, chunk_titles in promotions
                ],
            }
        )
    await session.commit()
    return {"id": str(draft.id), "aweme_id": douyin.aweme_id, "accounts": built}


async def submit_draft(
    session: AsyncSession, draft_id: int, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """只提交当前投手自己的草稿。收费模式须落在已授权菜单里。"""
    found = await get_draft_row(session, draft_id, user_id)
    if found is None:
        raise ApiError(404, "投放草稿不存在")
    draft, template, subject, douyin, series, library = found
    if draft.charge_mode not in allowed:
        raise ApiError(403, "已登录但无对应菜单或组件")
    if douyin is None:
        if template.douyin_account_id is None:
            raise ApiError(400, "抖音号不能为空")
        douyin = await get_standard_douyin(session, int(template.douyin_account_id))
        if douyin is None:
            raise ApiError(400, "抖音号不是已启用的标准号")
    if library is None:
        if template.product_library_id is None:
            raise ApiError(404, "商品库不存在")
        library = await get_library_by_id(session, int(template.product_library_id))
        if library is None:
            raise ApiError(404, "商品库不存在")
    accounts = (await accounts_by_drafts(session, [draft.id])).get(draft.id, [])
    videos = (await videos_by_drafts(session, [draft.id])).get(draft.id, [])
    titles = (await titles_by_drafts(session, [draft.id])).get(draft.id, [])
    return await submit_loaded(
        session, draft, template, subject, douyin, series, library, accounts, videos, titles
    )
