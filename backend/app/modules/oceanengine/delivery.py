"""建项目、创建广告、上传视频和商品、广告启停。"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.oceanengine.client import OceanEngineError
from app.modules.account.model import (
    DeliverySubject,
    OeProduct,
    OeProject,
    OePromotion,
    OeVideo,
    ProductLibrary,
)
from app.modules.material_video.model import MaterialVideo
from app.modules.oceanengine.runtime import _access_token, get_ocean_client
from app.modules.oceanengine.schema import (
    ProductCreate,
    ProjectCreate,
    PromotionCreate,
    PromotionStatusBody,
    VideoCreate,
)

_CENT = Decimal("0.01")
_PROJECT_TEMPLATE_KEYS = (
    "optimize_goal",
    "related_product",
    "audience",
    "micro_promotion_type",
    "aigc_dynamic_creative_switch",
)
_PROMOTION_BATCH = 10


def split_project_budget(total: Decimal, count: int) -> list[Decimal]:
    """把创建页上的项目总预算按账户拆开。前几个四舍五入到分，最后一个补齐差额。"""
    if count < 1:
        return []
    amount = Decimal(total)
    if count == 1:
        return [amount.quantize(_CENT, rounding=ROUND_HALF_UP)]
    share = (amount / Decimal(count)).quantize(_CENT, rounding=ROUND_HALF_UP)
    last = (amount - share * (count - 1)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return [share] * (count - 1) + [last]


def _project_row(
    body: ProjectCreate,
    subject_id: int | None,
    raw_payload: dict[str, Any] | None,
    *,
    create_message: str | None = None,
    ocean_project_id: int | None = None,
) -> OeProject:
    """落一条项目。创建失败时记下巨量返回的 message，项目 id 仍由库里的序列补。"""
    row = OeProject(
        advertiser_id=body.advertiser_id,
        name=body.name,
        landing_type=body.landing_type,
        marketing_goal=body.marketing_goal,
        ad_type=body.ad_type,
        delivery_mode=body.delivery_mode,
        subject_id=subject_id,
        template=body.template,
        raw_payload=raw_payload,
        create_message=create_message,
    )
    if ocean_project_id is not None:
        row.ocean_project_id = ocean_project_id
    return row


async def create_project(session: AsyncSession, body: ProjectCreate) -> dict[str, Any]:
    """创建项目。项目 id 来自客户端。"""
    saved = body.model_dump()
    subject_fk = await _subject_row_id(session, body.subject_id)
    client = get_ocean_client()
    remote_body = _project_remote_body(body) if client.requires_stored_token else saved
    try:
        remote = await client.create_project(await _access_token(session), remote_body)
    except OceanEngineError as exc:
        message = exc.ocean_message or str(exc)
        session.add(_project_row(body, subject_fk, {"message": message}, create_message=message))
        await session.flush()
        raise ApiError(502, message) from exc
    project_id = int((remote.get("data") or {}).get("project_id") or 0) or None
    row = _project_row(body, subject_fk, remote, ocean_project_id=project_id)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return {**saved, "project_id": int(row.ocean_project_id)}


def _payload_links(payload: dict[str, Any]) -> list[str]:
    """创建广告报文里的完整推广链接。"""
    materials = payload.get("promotion_materials")
    raw = materials.get("playlet_series_url_list") if isinstance(materials, dict) else None
    if raw is None:
        raw = payload.get("playlet_series_url_list")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _payload_budget(payload: dict[str, Any]) -> Decimal | None:
    """创建广告报文里的预算。不是正数就不记。"""
    raw = payload.get("budget")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        amount = Decimal(str(raw))
    except InvalidOperation:
        return None
    if amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


def _payload_project_id(payload: dict[str, Any]) -> int | None:
    """创建广告的报文里带了项目 id 就记下，用来判断父项目是否暂停。"""
    raw = payload.get("project_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


async def create_promotion(session: AsyncSession, body: PromotionCreate) -> dict[str, Any]:
    """调用已装上的客户端创建广告，并写入 oe_promotion。"""
    client = get_ocean_client()
    remote = await client.create_promotion(
        await _access_token(session),
        {"advertiser_id": body.advertiser_id, "name": body.name, **body.payload},
    )
    promotion_id = int((remote.get("data") or {}).get("promotion_id") or 0)
    if promotion_id <= 0:
        raise ApiError(502, "创建广告失败")
    row = OePromotion(
        advertiser_id=body.advertiser_id,
        promotion_id=promotion_id,
        ocean_project_id=_payload_project_id(body.payload),
        promotion_links=_payload_links(body.payload) or None,
        series_id=body.series_id,
        douyin_account_id=body.douyin_account_id,
        opt_status=body.opt_status,
        name=body.name,
        budget=_payload_budget(body.payload),
        raw_payload=remote,
    )
    session.add(row)
    await session.flush()
    return {"promotion_id": promotion_id, "opt_status": body.opt_status, "name": body.name}


def creative_material_id(remote: dict[str, Any]) -> int | None:
    """上传视频返回的 material_id。这就是头条素材 id，也是创意 id。"""
    data = remote.get("data") if isinstance(remote, dict) else None
    if not isinstance(data, dict):
        return None
    raw = data.get("material_id")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


async def upload_video(session: AsyncSession, body: VideoCreate) -> dict[str, Any]:
    """登记视频。视频 id 来自客户端。素材库视频把返回的 material_id 记到该行。"""
    saved = body.model_dump()
    client = get_ocean_client()
    remote = await client.upload_video(await _access_token(session), saved)
    raw_payload = remote
    video_id = str((remote.get("data") or {}).get("video_id") or "")
    material_id = creative_material_id(remote)
    if body.library_video_id is not None and material_id is not None:
        library_video = await session.get(MaterialVideo, body.library_video_id)
        if isinstance(library_video, MaterialVideo) and library_video.is_deleted == 0:
            library_video.ocean_material_id = material_id
    row = OeVideo(
        advertiser_id=body.advertiser_id,
        video_url=body.video_url,
        ocean_video_id=video_id or f"local-{uuid.uuid4().hex}",
        status="完成",
        raw_payload=raw_payload,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    if not video_id:
        video_id = str(row.ocean_video_id)
    return {**saved, "video_id": video_id, "material_id": material_id, "status": "完成"}


async def upload_product(session: AsyncSession, body: ProductCreate) -> dict[str, Any]:
    """按 library_no 写入 oe_product。库不存在则 404。同一事务把 uploaded_count 加 1。

    假客户端发 product_id，不走 503。真客户端仍因开放平台 path 未定而 503，这里不改派库。
    """
    library = await session.scalar(
        select(ProductLibrary)
        .where(ProductLibrary.library_no == body.library_no, ProductLibrary.is_deleted == 0)
        .with_for_update()
    )
    if library is None:
        raise ApiError(404, "商品库不存在")
    client = get_ocean_client()
    remote = await client.upload_product(
        await _access_token(session),
        {
            "advertiser_id": body.advertiser_id,
            "library_no": body.library_no,
            "book_name": body.book_name,
        },
    )
    product_id = int((remote.get("data") or {}).get("product_id") or 0) or None
    row = OeProduct(
        product_library_id=library.id,
        drama_name=body.book_name,
        file_url=None,
        raw_payload=remote,
    )
    if product_id is not None:
        row.ocean_product_id = product_id
    library.uploaded_count = int(library.uploaded_count or 0) + 1
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return {
        "advertiser_id": body.advertiser_id,
        "library_no": int(library.library_no),
        "book_name": body.book_name,
        "product_id": int(row.ocean_product_id),
    }


async def upload_image(
    session: AsyncSession,
    advertiser_id: int,
    filename: str,
    content: bytes | None = None,
) -> dict[str, Any]:
    """上传产品主图。有字节时按 UPLOAD_BY_FILE 交给客户端。

    不传字节仍调用客户端：已装上的客户端自己决定发号还是拒绝。空字节是 400。
    不接受 URL。视频式 local- 号不能当主图。
    """
    if content is not None and len(content) == 0:
        raise ApiError(400, "图片文件为空")
    client = get_ocean_client()
    body: dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "upload_type": "UPLOAD_BY_FILE",
        "filename": filename,
    }
    if content:
        body["image_file"] = content
    remote = await client.upload_image(await _access_token(session), body)
    image_id = str((remote.get("data") or {}).get("id") or "")
    if not image_id or image_id.startswith("local-"):
        raise ApiError(502, "图片 id 无效")
    return {"advertiser_id": advertiser_id, "image_id": image_id}


async def update_promotions(
    session: AsyncSession, body: PromotionStatusBody
) -> list[dict[str, Any]]:
    """批量改广告启停，写入 oe_promotion。"""
    accepted, failures = await _push_promotion_status(session, body)
    results: list[dict[str, Any]] = []
    for promotion_id in accepted:
        await _upsert_promotion(session, body.advertiser_id, promotion_id, body.opt_status)
        results.append({"promotion_id": promotion_id, "opt_status": body.opt_status})
    await session.flush()
    if failures:
        raise ApiError(502, "；".join(failures))
    return results


def _project_remote_body(body: ProjectCreate) -> dict[str, Any]:
    """subject_id 只落本地。定向和出价从 template 原样提交。"""
    template = body.template if isinstance(body.template, dict) else {}
    delivery_range = template.get("delivery_range")
    delivery_setting = template.get("delivery_setting")
    if not isinstance(delivery_range, dict) or not isinstance(delivery_setting, dict):
        raise ApiError(422, "template 需要 delivery_range 和 delivery_setting")
    remote = {
        "advertiser_id": body.advertiser_id,
        "name": body.name,
        "landing_type": body.landing_type,
        "marketing_goal": body.marketing_goal,
        "ad_type": body.ad_type,
        "delivery_mode": body.delivery_mode,
        "delivery_range": delivery_range,
        "delivery_setting": delivery_setting,
    }
    for key in _PROJECT_TEMPLATE_KEYS:
        if template.get(key) is not None:
            remote[key] = template[key]
    return remote


async def _push_promotion_status(
    session: AsyncSession, body: PromotionStatusBody
) -> tuple[list[int], list[str]]:
    """每批最多 10 条。errors 里的广告不进入成功列表。"""
    client = get_ocean_client()
    token = await _access_token(session)
    accepted: list[int] = []
    messages: list[str] = []
    ids = list(body.promotion_ids)
    for start in range(0, len(ids), _PROMOTION_BATCH):
        chunk = ids[start : start + _PROMOTION_BATCH]
        remote = await client.update_promotion_status(
            token,
            {
                "advertiser_id": body.advertiser_id,
                "data": [
                    {"promotion_id": promotion_id, "opt_status": body.opt_status}
                    for promotion_id in chunk
                ],
            },
        )
        data = remote.get("data") or {}
        ok = [int(item) for item in data.get("promotion_ids") or []]
        failed = data.get("errors") or []
        if failed:
            accepted.extend(ok)
            for item in failed:
                if isinstance(item, dict):
                    messages.append(str(item.get("error_message") or item.get("promotion_id") or "更新失败"))
            continue
        accepted.extend(ok or chunk)
    return accepted, messages


async def _subject_row_id(session: AsyncSession, subject_id: int) -> int | None:
    row = await session.get(DeliverySubject, subject_id)
    if row is not None and row.is_deleted == 0:
        return int(row.id)
    found = await session.scalar(
        select(DeliverySubject.id).where(
            DeliverySubject.subject_no == subject_id,
            DeliverySubject.is_deleted == 0,
        )
    )
    if found is None:
        return None
    return int(found)


async def _upsert_promotion(
    session: AsyncSession, advertiser_id: int, promotion_id: int, opt_status: str
) -> None:
    found = await session.scalar(
        select(OePromotion).where(
            OePromotion.advertiser_id == advertiser_id,
            OePromotion.promotion_id == promotion_id,
        )
    )
    if found is None:
        session.add(
            OePromotion(
                advertiser_id=advertiser_id,
                promotion_id=promotion_id,
                opt_status=opt_status,
            )
        )
        return
    found.opt_status = opt_status
    found.is_deleted = 0
    found.deleted_at = None

