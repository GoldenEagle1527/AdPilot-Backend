"""巨量账户、授权、项目、上传、报表与关停。mock 读写夹具；关闭 mock 后走开放平台客户端。"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.modules.oceanengine.client import OceanEngineClient
from app.modules.oceanengine.fixtures import (
    ADVERTISERS,
    OAUTH_TOKEN,
    ORGANIZATIONS,
    REPORTS,
    append_product,
    append_project,
    append_video,
    remember_token,
    upsert_promotion,
)
from app.modules.oceanengine.schema import (
    AdvertiserQuery,
    AutoPauseBody,
    ProductCreate,
    ProjectCreate,
    PromotionStatusBody,
    VideoCreate,
)


async def list_organizations() -> list[dict[str, Any]]:
    """授权组织。mock 返回夹具；否则映射开放平台 data.list。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return [dict(row) for row in ORGANIZATIONS]
    client = _live_client()
    body = await client.list_authorized_accounts("")
    rows = (body.get("data") or {}).get("list") or []
    return [_organization(row) for row in rows]


async def list_advertisers(query: AdvertiserQuery) -> dict[str, Any]:
    """广告主分页。mock 返回夹具；否则按组织拉 EBP、余额和公司名后再筛选。"""
    settings = get_settings().oceanengine
    if settings.mock:
        rows = [dict(row) for row in ADVERTISERS]
    else:
        rows = await _live_advertisers()
    matched = [row for row in rows if _matches(row, query)]
    params = PageParams(page=query.page, page_size=query.page_size)
    page = matched[params.offset : params.offset + params.page_size]
    return page_data(page, len(matched), params)


def _live_client() -> OceanEngineClient:
    settings = get_settings().oceanengine
    if not settings.secret:
        raise ApiError(503, "巨量未配置")
    return OceanEngineClient(settings)


async def _live_advertisers() -> list[dict[str, Any]]:
    client = _live_client()
    token = ""
    authorized = await client.list_authorized_accounts(token)
    org_rows = (authorized.get("data") or {}).get("list") or []
    orgs = [
        row
        for row in org_rows
        if str(row.get("account_role") or "") == "CUSTOMER_ADMIN"
    ]
    advertisers: list[dict[str, Any]] = []
    for org in orgs:
        organization_id = int(org["advertiser_id"])
        listed = await client.list_ebp_advertisers(token, organization_id)
        accounts = (listed.get("data") or {}).get("account_list") or []
        for account in accounts:
            account_id = int(account["account_id"])
            fund = await client.fund_get(token, account_id)
            info = await client.advertiser_info_query(token, [account_id])
            balance = (fund.get("data") or {}).get("valid_balance")
            advertisers.append(
                {
                    "account_id": account_id,
                    "account_name": str(account.get("account_name") or ""),
                    "valid_balance": float(balance or 0),
                    "adv_company_name": _company_name(info, account_id),
                    "organization_id": organization_id,
                }
            )
    return advertisers


def _organization(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "advertiser_id": int(row["advertiser_id"]),
        "advertiser_name": str(row.get("advertiser_name") or ""),
        "account_role": str(row.get("account_role") or ""),
        "ocean_version": str(row.get("ocean_version") or ""),
    }


def _company_name(body: dict[str, Any], account_id: int) -> str:
    details = (body.get("data") or {}).get("account_detail_list") or []
    for item in details:
        if int(item.get("advertiser_id") or 0) == account_id:
            return str(item.get("adv_company_name") or "")
    return ""


_AUTHORIZE_URLS = {
    "third": (
        "https://open.oceanengine.com/audit/oauth.html?app_id=1870857293665690"
        "&state={%22agentId%22:%221%22}&material_auth=1&rid=tg29ccnkpzm"
    ),
    "self": (
        "https://open.oceanengine.com/audit/oauth.html?app_id=1870855836080240"
        "&state={%22agentId%22:%221%22,%22agency%22:true}&material_auth=1&rid=c9lb3o12qhm"
    ),
}


def authorize_url(channel: str) -> str:
    """按渠道返回巨量授权页。不请求开放平台。"""
    url = _AUTHORIZE_URLS.get(channel)
    if url is None:
        raise ApiError(422, "channel 只允许 third 或 self")
    return url


async def oauth_callback(auth_code: str, state: str = "") -> dict[str, str]:
    """用授权码换票。mock 写入夹具令牌。"""
    del state
    if not auth_code.strip():
        raise ApiError(422, "auth_code 不能为空")
    settings = get_settings().oceanengine
    if settings.mock:
        return remember_token("mock-access-token", "mock-refresh-token")
    client = _live_client()
    body = await client.exchange_token(auth_code)
    data = body.get("data") or {}
    return {
        "access_token": str(data.get("access_token") or ""),
        "refresh_token": str(data.get("refresh_token") or ""),
    }


async def create_project(body: ProjectCreate) -> dict[str, Any]:
    """创建项目。mock 写入 PROJECTS；否则调用开放平台。"""
    saved = body.model_dump()
    settings = get_settings().oceanengine
    if settings.mock:
        return append_project(saved)
    client = _live_client()
    remote = await client.create_project(
        _access_token(),
        {
            "advertiser_id": body.advertiser_id,
            "name": body.name,
            "landing_type": body.landing_type,
            "marketing_goal": body.marketing_goal,
            "ad_type": body.ad_type,
            "delivery_mode": body.delivery_mode,
            "subject_id": body.subject_id,
        },
    )
    project_id = int((remote.get("data") or {}).get("project_id") or 0)
    return {**saved, "project_id": project_id}


async def upload_video(body: VideoCreate) -> dict[str, Any]:
    """登记视频。mock 写入 VIDEOS。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return append_video(body.model_dump())
    client = _live_client()
    remote = await client.upload_video(_access_token(), body.model_dump())
    video_id = str((remote.get("data") or {}).get("video_id") or "")
    return {**body.model_dump(), "video_id": video_id, "status": "完成"}


async def upload_product(library_id: int, body: ProductCreate) -> dict[str, Any]:
    """商品入库。mock 写入 PRODUCTS。开放平台 path 未定。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return append_product({**body.model_dump(), "library_id": library_id})
    client = _live_client()
    remote = await client.upload_product(
        _access_token(),
        {**body.model_dump(), "library_id": library_id},
    )
    product_id = int((remote.get("data") or {}).get("product_id") or 0)
    return {**body.model_dump(), "library_id": library_id, "product_id": product_id}


async def list_reports() -> list[dict[str, Any]]:
    """自定义报表，不分页。mock 返回两条夹具。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return [dict(row) for row in REPORTS]
    client = _live_client()
    body = await client.custom_report(_access_token())
    rows = (body.get("data") or {}).get("list") or []
    return [_report_row(row) for row in rows]


async def update_promotions(body: PromotionStatusBody) -> list[dict[str, Any]]:
    """批量改广告启停。mock 更新 PROMOTIONS。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return [
            {
                "promotion_id": promotion_id,
                "opt_status": upsert_promotion(
                    body.advertiser_id, promotion_id, body.opt_status
                )["opt_status"],
            }
            for promotion_id in body.promotion_ids
        ]
    client = _live_client()
    await client.update_promotion_status(
        _access_token(),
        {
            "advertiser_id": body.advertiser_id,
            "data": [
                {"promotion_id": promotion_id, "opt_status": body.opt_status}
                for promotion_id in body.promotion_ids
            ],
        },
    )
    return [
        {"promotion_id": promotion_id, "opt_status": body.opt_status}
        for promotion_id in body.promotion_ids
    ]


async def run_auto_pause(body: AutoPauseBody) -> dict[str, list[int]]:
    """按报表阈值关停。指标值小于等于阈值时暂停。"""
    rows = await list_reports()
    paused: list[int] = []
    kept: list[int] = []
    for row in rows:
        promotion_id = int(row["promotion_id"])
        if _should_pause(body.metric, row, body.threshold):
            paused.append(promotion_id)
        else:
            kept.append(promotion_id)
    if paused:
        await update_promotions(
            PromotionStatusBody(
                advertiser_id=_pause_advertiser_id(rows, paused),
                promotion_ids=paused,
                opt_status="DISABLE",
            )
        )
    return {"paused": paused, "kept": kept}


def _should_pause(metric: str, row: dict[str, Any], threshold: float) -> bool:
    """operator 只有 lte：指标值小于等于阈值则暂停。"""
    if metric == "stat_cost":
        value = float(row["stat_cost"])
    else:
        value = float(row["attribution_micro_game_0d_roi"])
    return value <= threshold


def _pause_advertiser_id(rows: list[dict[str, Any]], paused: list[int]) -> int:
    wanted = set(paused)
    for row in rows:
        if int(row["promotion_id"]) in wanted and row.get("advertiser_id") is not None:
            return int(row["advertiser_id"])
    return 0


def _report_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "promotion_id": int(row["promotion_id"]),
        "stat_cost": float(row.get("stat_cost") or 0),
        "attribution_micro_game_0d_roi": float(row.get("attribution_micro_game_0d_roi") or 0),
        "advertiser_id": int(row.get("advertiser_id") or 0),
    }


def _access_token() -> str:
    return OAUTH_TOKEN.get("access_token") or ""


def _matches(row: dict[str, Any], query: AdvertiserQuery) -> bool:
    if query.account_id is not None and int(row["account_id"]) != query.account_id:
        return False
    name = (query.account_name or "").strip()
    if name and name.casefold() not in str(row["account_name"]).casefold():
        return False
    return True
