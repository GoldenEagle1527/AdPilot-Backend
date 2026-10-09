"""确认提交一条全域端原生任务。

每个账户行已经是一个抖音号对一个广告账户。项目、商品、主图走已装上的客户端。
假客户端执行期间把状态写成 running（执行中），结束后写成 done（完成）。
materials_uploaded 保持 false，不表示巨量已经收下素材。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_iso, beijing_now
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    DouyinAccount,
    ProductLibrary,
    ProductLibraryPitcher,
)
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.oceanengine.delivery import create_project, upload_image, upload_product
from app.modules.oceanengine.schema import ProductCreate, ProjectCreate
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.uni_native_task.crud import (
    accounts_by_tasks,
    batch_titles_by_tasks,
    get_task_row,
    links_by_tasks,
    present_tables,
    titles_by_tasks,
    videos_by_tasks,
)
from app.modules.uni_native_task.model import NativeTaskStatus, UniNativeTask, UniNativeTaskLink
from app.modules.uni_template.crud import get_uni_template_row

_TITLE_MIN = 5
_TITLE_MAX = 30
_IMAGE_MODE = {
    "vertical_video": "CREATIVE_IMAGE_MODE_VIDEO_VERTICAL",
    "horizontal_video": "CREATIVE_IMAGE_MODE_VIDEO",
}


def _num(value: Decimal) -> float:
    """金额和 ROI 交给 JSON 时用数字。"""
    return float(value)


def _project_name(book_name: str) -> str:
    """短剧前两个字 + NB + 月日时分。"""
    return f"{book_name[:2]}NB{beijing_now().strftime('%m%d%H%M')}"


def _video_material(video: MaterialVideo) -> dict[str, Any]:
    """素材库主键。没有巨量视频号时不补。"""
    return {
        "material_id": int(video.id),
        "image_mode": _IMAGE_MODE.get(video.material_type, "CREATIVE_IMAGE_MODE_VIDEO_VERTICAL"),
    }


async def pitcher_library(session: AsyncSession, user_id: int) -> ProductLibrary:
    """投手已分配的商品库。没有就用兜底库。"""
    assigned = await session.execute(
        select(ProductLibrary)
        .join(ProductLibraryPitcher, ProductLibraryPitcher.product_library_id == ProductLibrary.id)
        .where(
            ProductLibraryPitcher.user_id == user_id,
            ProductLibraryPitcher.is_deleted == 0,
            ProductLibrary.is_deleted == 0,
        )
        .limit(1)
    )
    found = assigned.scalar_one_or_none()
    if found is not None:
        return found
    fallback = await session.execute(
        select(ProductLibrary)
        .where(ProductLibrary.library_role == "fallback", ProductLibrary.is_deleted == 0)
        .limit(1)
    )
    library = fallback.scalar_one_or_none()
    if library is None:
        raise ApiError(404, "商品库不存在")
    return library


def _reject_titles(titles: list[str]) -> None:
    """有一条标题长度不对就整单拒绝。"""
    if any(not _TITLE_MIN <= len(title) <= _TITLE_MAX for title in titles):
        raise ApiError(400, "标题长度须为 5–30 个字")


async def submit_loaded(
    session: AsyncSession,
    task: UniNativeTask,
    template: DeliveryTemplate,
    subject: DeliverySubject,
    book_name: str,
    pairs: list[tuple[DouyinAccount, AdvertiserAccount]],
    links: list[UniNativeTaskLink],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
    batch_titles: list[str],
    library: ProductLibrary,
) -> dict[str, Any]:
    """每个账户一行一个项目、一条广告。不改模板的 delivery_mode。

    标题不合格时保持 saved。通过后先标 running，假客户端返回后再标 done。
    """
    chosen = [title.title for title in titles] + list(batch_titles)
    _reject_titles(chosen)
    task.status = NativeTaskStatus.RUNNING
    await session.flush()
    name = _project_name(book_name)
    built: list[dict[str, Any]] = []
    for douyin, account in pairs:
        advertiser_id = int(account.advertiser_id)
        product = await upload_product(
            session,
            ProductCreate(
                advertiser_id=advertiser_id,
                library_no=int(library.library_no),
                book_name=book_name,
            ),
        )
        image = await upload_image(session, advertiser_id, "product.png")
        project = {
            "advertiser_id": advertiser_id,
            "name": name,
            "landing_type": "MICRO_GAME",
            "marketing_goal": "VIDEO_AND_IMAGE",
            "ad_type": "ALL",
            "delivery_mode": "PROCEDURAL",
            "delivery_range": {"inventory_catalog": "UNIVERSAL_SMART"},
            "delivery_setting": {
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": _num(task.project_budget),
                "roi_goal": _num(task.roi_coefficient),
            },
            "related_product": {
                "product_platform_id": int(library.library_no),
                "product_id": int(product["product_id"]),
                "product_setting": "SINGLE",
            },
            "audience": {"district": "NONE"},
            "micro_promotion_type": "AWEME",
            "native_setting": {"aweme_id": douyin.aweme_id},
        }
        created = await create_project(
            session,
            ProjectCreate(
                advertiser_id=advertiser_id,
                name=name,
                landing_type="MICRO_GAME",
                marketing_goal="VIDEO_AND_IMAGE",
                ad_type="ALL",
                delivery_mode="PROCEDURAL",
                subject_id=int(subject.id),
                template={
                    "delivery_range": project["delivery_range"],
                    "delivery_setting": project["delivery_setting"],
                    "related_product": project["related_product"],
                    "audience": project["audience"],
                    "micro_promotion_type": project["micro_promotion_type"],
                    "native_setting": project["native_setting"],
                },
            ),
        )
        project_id = int(created["project_id"])
        promotion = {
            "advertiser_id": advertiser_id,
            "project_id": project_id,
            "name": name,
            "native_setting": {"aweme_id": douyin.aweme_id},
            "promotion_materials": {
                "video_material_list": [_video_material(video) for video in videos],
                "title_material_list": [{"title": title} for title in chosen],
                "product_info": {"image_ids": [str(image["image_id"])]},
            },
        }
        built.append(
            {
                "douyin_account_id": str(douyin.id),
                "aweme_id": douyin.aweme_id,
                "advertiser_id": advertiser_id,
                "project_id": project_id,
                "product_id": int(product["product_id"]),
                "image_id": str(image["image_id"]),
                "project": project,
                "promotions": [promotion],
            }
        )
    task.status = NativeTaskStatus.DONE
    task.executed_at = beijing_now()
    await session.commit()
    return {
        "id": str(task.id),
        "status": task.status,
        "executed_at": None if task.executed_at is None else beijing_iso(task.executed_at),
        "materials_uploaded": False,
        "promotion_links": [
            {"charge_mode": link.charge_mode, "link_text": link.link_text} for link in links
        ],
        "accounts": built,
    }


async def submit_task(session: AsyncSession, task_id: int, user_id: int) -> dict[str, Any]:
    """只提交当前投手自己的任务。素材表不在就当没有素材，不标成已上传。"""
    present = await present_tables(session)
    if "manhua_series" not in present:
        raise ApiError(400, "短剧库不存在")
    found = await get_task_row(session, task_id, user_id, series_present=True)
    if found is None:
        raise ApiError(404, "投放任务不存在")
    task, template, book_name = found
    owned = await get_uni_template_row(session, task.template_id)
    if owned is None:
        raise ApiError(404, "模板不存在")
    template, subject = owned
    accounts = (await accounts_by_tasks(session, [task.id])).get(task.id, [])
    links = (await links_by_tasks(session, [task.id])).get(task.id, [])
    videos = (
        (await videos_by_tasks(session, [task.id])).get(task.id, [])
        if "material_videos" in present
        else []
    )
    titles = (
        (await titles_by_tasks(session, [task.id])).get(task.id, [])
        if "material_titles" in present
        else []
    )
    batches = (await batch_titles_by_tasks(session, [task.id])).get(task.id, [])
    library = await pitcher_library(session, user_id)
    return await submit_loaded(
        session,
        task,
        template,
        subject,
        book_name,
        accounts,
        links,
        videos,
        titles,
        batches,
        library,
    )
