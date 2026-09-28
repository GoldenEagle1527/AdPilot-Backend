"""巨量账户、授权、项目、上传、报表与关停。读写数据库；mock 不打开放平台。

授权链接最终签名：async def authorize_url(session: AsyncSession, channel: str) -> str
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, unquote

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_now
from app.modules.account.commands import sign_oauth_state
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    OeApp,
    OeOrganization,
    OeProduct,
    OeProject,
    OePromotion,
    OeReportSnapshot,
    OeToken,
    OeVideo,
    ProductLibrary,
)
from app.modules.account.seed import ensure_oceanengine_seed
from app.modules.oceanengine.client import OceanEngineClient, OceanEngineError
from app.modules.oceanengine.schema import (
    AdvertiserQuery,
    AutoPauseBody,
    ProductCreate,
    ProjectCreate,
    PromotionStatusBody,
    VideoCreate,
)
from app.modules.system_admin.domain.models import User

_OAUTH_PAGE = "https://open.oceanengine.com/audit/oauth.html"
_EBP_ROLES = frozenset(
    {
        "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN",
        "PLATFORM_ROLE_ENTERPRISE_BP_OPERATOR",
    }
)
_CUSTOMER_ADMIN = "CUSTOMER_ADMIN"
_ORG_ROLES = _EBP_ROLES | {_CUSTOMER_ADMIN}
_PAGE_SIZE = 100
_LIST_CAP = 10_000
_BALANCE_BATCH = 200
_BALANCE_TTL = timedelta(days=1)
_TOKEN_SKEW = timedelta(minutes=5)
_TASK_POLLS = 3
_PROJECT_TEMPLATE_KEYS = (
    "optimize_goal",
    "related_product",
    "audience",
    "micro_promotion_type",
)
_PROMOTION_BATCH = 10


def _configured_ocean_app_id() -> int | None:
    """关闭 mock 且配置了数字 app_id 时，列表只看这个应用。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return None
    text = settings.app_id.strip()
    if text.isdigit():
        return int(text)
    return None


def organization_token_valid(
    *,
    access_token: str | None,
    last_error: str | None,
    access_expire_at: datetime | None,
    now: datetime,
) -> bool:
    """有访问令牌、没有刷新失败，且未过期。"""
    if not access_token or (last_error or "").strip():
        return False
    if access_expire_at is not None and access_expire_at <= now:
        return False
    return True


async def list_organizations(session: AsyncSession) -> list[dict[str, Any]]:
    """授权组织。只读表。关闭 mock 时只返回配置里的那个应用。"""
    await _prepare(session)
    now = beijing_now()
    stmt = (
        select(
            OeOrganization.id,
            OeOrganization.ocean_account_id,
            OeOrganization.name,
            OeOrganization.account_role,
            OeOrganization.ocean_version,
            OeOrganization.status,
            OeApp.channel,
            OeToken.access_token,
            OeToken.last_error,
            OeToken.access_expire_at,
        )
        .join(OeApp, OeOrganization.oe_app_id == OeApp.id)
        .outerjoin(
            OeToken,
            (OeToken.oe_app_id == OeApp.id) & (OeToken.is_deleted == 0),
        )
        .where(OeOrganization.is_deleted == 0, OeApp.is_deleted == 0)
        .order_by(OeOrganization.id)
    )
    app_id = _configured_ocean_app_id()
    if app_id is not None:
        stmt = stmt.where(OeApp.app_id == app_id)
    rows = await session.execute(stmt)
    return [
        {
            "id": int(row_id),
            "advertiser_id": int(ocean_account_id),
            "advertiser_name": name,
            "account_role": account_role,
            "ocean_version": ocean_version,
            "channel": channel,
            "status": status,
            "token_valid": organization_token_valid(
                access_token=access_token,
                last_error=last_error,
                access_expire_at=access_expire_at,
                now=now,
            ),
        }
        for (
            row_id,
            ocean_account_id,
            name,
            account_role,
            ocean_version,
            status,
            channel,
            access_token,
            last_error,
            access_expire_at,
        ) in rows.all()
    ]


async def list_advertisers(session: AsyncSession, query: AdvertiserQuery) -> dict[str, Any]:
    """广告主分页。只读表。mock 时先落种子，不打开放平台。"""
    await _prepare(session)
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = [AdvertiserAccount.is_deleted == 0, OeOrganization.is_deleted == 0]
    app_id = _configured_ocean_app_id()
    if app_id is not None:
        filters.append(OeApp.app_id == app_id)
        filters.append(OeApp.is_deleted == 0)
    if query.account_id is not None:
        filters.append(AdvertiserAccount.advertiser_id == query.account_id)
    if query.organization_id is not None:
        filters.append(OeOrganization.ocean_account_id == query.organization_id)
    if query.only_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.only_user_id)
        filters.append(AdvertiserAccount.sync_status == "active")
    elif query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    name = (query.account_name or "").strip()
    if name:
        pattern = _like(name)
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    joined = (
        select(
            AdvertiserAccount.advertiser_id,
            AdvertiserAccount.name,
            AdvertiserAccount.local_name,
            AdvertiserAccount.valid_balance,
            AdvertiserAccount.company_name,
            AdvertiserAccount.sync_status,
            OeOrganization.ocean_account_id,
            OeOrganization.name.label("manager_name"),
            User.nickname,
        )
        .join(OeOrganization, AdvertiserAccount.organization_id == OeOrganization.id)
        .join(OeApp, AdvertiserAccount.oe_app_id == OeApp.id)
        .outerjoin(
            User,
            (AdvertiserAccount.pitcher_user_id == User.id) & (User.is_deleted == 0),
        )
        .where(*filters)
    )
    total = int(await session.scalar(select(func.count()).select_from(joined.subquery())) or 0)
    page_rows = await session.execute(
        joined.order_by(AdvertiserAccount.id).offset(params.offset).limit(params.page_size)
    )
    items = [_advertiser_item(row) for row in page_rows.all()]
    return page_data(items, total, params)


async def authorize_url(session: AsyncSession, channel: str) -> str:
    """按渠道拼授权页。mock 用种子应用；关闭 mock 时用配置里的 app_id。"""
    await _prepare(session)
    if channel not in ("third", "self"):
        raise ApiError(422, "channel 只允许 third 或 self")
    settings = get_settings().oceanengine
    if not settings.mock and settings.app_id.strip().isdigit():
        app = await _ensure_configured_app(session)
    else:
        app = await session.scalar(
            select(OeApp)
            .where(OeApp.channel == channel, OeApp.status == "active", OeApp.is_deleted == 0)
            .order_by(OeApp.id)
            .limit(1)
        )
    if app is None:
        raise ApiError(404, "该渠道没有有效应用")
    state = _authorize_state(app)
    parts = [
        f"app_id={app.app_id}",
        f"state={state}",
        f"material_auth={app.material_auth}",
    ]
    redirect_uri = settings.redirect_uri.strip()
    if redirect_uri:
        parts.append("redirect_uri=" + quote(redirect_uri, safe=""))
    if app.oauth_rid and app.oauth_rid not in {"local", "configured"}:
        parts.append(f"rid={app.oauth_rid}")
    return f"{_OAUTH_PAGE}?{'&'.join(parts)}"


async def _ensure_configured_app(session: AsyncSession) -> OeApp:
    """把配置里的 app_id 落成一条自研应用。secret 只记配置键名。"""
    settings = get_settings().oceanengine
    app_id = int(settings.app_id.strip())
    found = await session.scalar(select(OeApp).where(OeApp.app_id == app_id))
    if found is None:
        found = OeApp(
            channel="self",
            name="配置的巨量应用",
            app_id=app_id,
            secret="oceanengine.secret",
            agent_key="1",
            agency=True,
            material_auth=1,
            oauth_rid="configured",
            status="active",
        )
        session.add(found)
    else:
        found.channel = "self"
        found.agency = True
        found.status = "active"
        found.is_deleted = 0
        found.deleted_at = None
    await session.flush()
    return found


async def oauth_callback(
    session: AsyncSession, auth_code: str, state: str = ""
) -> dict[str, str]:
    """用授权码换票并写入 oe_token。mock 写假 token，不打开放平台。"""
    await _prepare(session)
    if not auth_code.strip():
        raise ApiError(422, "auth_code 不能为空")
    app = await _app_for_callback(session, state)
    if get_settings().oceanengine.mock:
        access_token = "mock-access-token"
        refresh_token = "mock-refresh-token"
        remote: dict[str, Any] = {}
    else:
        client = _live_client()
        body = await client.exchange_token(auth_code)
        remote = body.get("data") or {}
        access_token = str(remote.get("access_token") or "")
        refresh_token = str(remote.get("refresh_token") or "")
    await _save_token(session, app, access_token, refresh_token, remote)
    if not get_settings().oceanengine.mock and access_token:
        await sync_from_oceanengine(session, app)
    return {"access_token": access_token, "refresh_token": refresh_token}


async def create_project(session: AsyncSession, body: ProjectCreate) -> dict[str, Any]:
    """创建项目。mock 用 oe_project 序列发号；否则开放平台成功后写入。"""
    await _prepare(session)
    saved = body.model_dump()
    subject_fk = await _subject_row_id(session, body.subject_id)
    project_id: int | None = None
    raw_payload: dict[str, Any] | None = None
    if not get_settings().oceanengine.mock:
        client = _live_client()
        remote = await client.create_project(
            await _access_token(session),
            _project_remote_body(body),
        )
        raw_payload = remote
        project_id = int((remote.get("data") or {}).get("project_id") or 0) or None
    row = OeProject(
        advertiser_id=body.advertiser_id,
        name=body.name,
        landing_type=body.landing_type,
        marketing_goal=body.marketing_goal,
        ad_type=body.ad_type,
        delivery_mode=body.delivery_mode,
        subject_id=subject_fk,
        template=body.template,
        raw_payload=raw_payload,
    )
    if project_id is not None:
        row.ocean_project_id = project_id
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return {**saved, "project_id": int(row.ocean_project_id)}


async def upload_video(session: AsyncSession, body: VideoCreate) -> dict[str, Any]:
    """登记视频。mock 用 oe_video 序列发号。"""
    await _prepare(session)
    saved = body.model_dump()
    video_id = ""
    raw_payload: dict[str, Any] | None = None
    if not get_settings().oceanengine.mock:
        client = _live_client()
        remote = await client.upload_video(await _access_token(session), saved)
        raw_payload = remote
        video_id = str((remote.get("data") or {}).get("video_id") or "")
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
    return {**saved, "video_id": video_id, "status": "完成"}


async def upload_product(
    session: AsyncSession, library_id: int, body: ProductCreate
) -> dict[str, Any]:
    """写入 oe_product。库不存在则 404。同一事务把 uploaded_count 加 1。

    兜底库怎么选由商品库服务决定。这里不改派库：标准库且调用方没传投手时，
    仍按传入的库 id 写入。
    """
    await _prepare(session)
    library = await session.scalar(
        select(ProductLibrary)
        .where(ProductLibrary.id == library_id, ProductLibrary.is_deleted == 0)
        .with_for_update()
    )
    if library is None:
        raise ApiError(404, "商品库不存在")
    product_id: int | None = None
    raw_payload: dict[str, Any] | None = None
    if not get_settings().oceanengine.mock:
        client = _live_client()
        remote = await client.upload_product(
            await _access_token(session),
            {**body.model_dump(), "library_id": library_id},
        )
        raw_payload = remote
        product_id = int((remote.get("data") or {}).get("product_id") or 0) or None
    row = OeProduct(
        product_library_id=library.id,
        drama_name=body.drama_name,
        file_url=body.file_url,
        raw_payload=raw_payload,
    )
    if product_id is not None:
        row.ocean_product_id = product_id
    library.uploaded_count = int(library.uploaded_count or 0) + 1
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return {
        "library_id": library_id,
        "product_id": int(row.ocean_product_id),
        "drama_name": body.drama_name,
        "file_url": body.file_url,
    }


async def list_reports(session: AsyncSession) -> list[dict[str, Any]]:
    """报表不分页。关闭 mock 时先拉当天自定义报表再读快照。"""
    await _prepare(session)
    if not get_settings().oceanengine.mock:
        await _sync_reports(session)
    return await _report_rows(session)


async def sync_from_oceanengine(session: AsyncSession, app: OeApp | None = None) -> None:
    """手动同步或回调之后调用。先组织，再广告主。传入的应用优先于配置里的应用。"""
    target = app or await _app_for_live(session)
    await _sync_organizations(session, target)
    await _sync_advertisers(session, target)


async def update_promotions(
    session: AsyncSession, body: PromotionStatusBody
) -> list[dict[str, Any]]:
    """批量改广告启停，写入 oe_promotion。"""
    await _prepare(session)
    accepted = list(body.promotion_ids)
    failures: list[str] = []
    if not get_settings().oceanengine.mock:
        accepted, failures = await _push_promotion_status(session, body)
    results: list[dict[str, Any]] = []
    for promotion_id in accepted:
        await _upsert_promotion(session, body.advertiser_id, promotion_id, body.opt_status)
        results.append({"promotion_id": promotion_id, "opt_status": body.opt_status})
    await session.flush()
    if failures:
        raise ApiError(502, "；".join(failures))
    return results


async def run_auto_pause(session: AsyncSession, body: AutoPauseBody) -> dict[str, list[int]]:
    """按报表阈值关停。关闭 mock 时先拉当天自定义报表。"""
    await _prepare(session)
    if not get_settings().oceanengine.mock:
        await _sync_reports(session)
    rows = await _report_rows(session)
    paused: list[int] = []
    kept: list[int] = []
    grouped: dict[int, list[int]] = {}
    order: list[int] = []
    for row in rows:
        promotion_id = int(row["promotion_id"])
        if _should_pause(body.metric, row, body.threshold):
            paused.append(promotion_id)
            advertiser_id = int(row["advertiser_id"])
            if advertiser_id not in grouped:
                order.append(advertiser_id)
            grouped.setdefault(advertiser_id, []).append(promotion_id)
        else:
            kept.append(promotion_id)
    for advertiser_id in order:
        await update_promotions(
            session,
            PromotionStatusBody(
                advertiser_id=advertiser_id,
                promotion_ids=grouped[advertiser_id],
                opt_status="DISABLE",
            ),
        )
    return {"paused": paused, "kept": kept}


async def _prepare(session: AsyncSession) -> None:
    """mock 时先幂等写入种子，不请求开放平台。"""
    if get_settings().oceanengine.mock:
        await ensure_oceanengine_seed(session)


def _live_client() -> OceanEngineClient:
    settings = get_settings().oceanengine
    if not settings.secret:
        raise ApiError(503, "巨量未配置")
    return OceanEngineClient(settings)


def token_needs_refresh(
    *,
    access_token: str | None,
    refresh_token: str | None,
    access_expire_at: datetime | None,
    now: datetime,
) -> bool:
    """有 refresh 且访问令牌缺失或 5 分钟内过期时需要续期。"""
    if not refresh_token:
        return False
    if not access_token:
        return True
    if access_expire_at is None:
        return False
    return access_expire_at <= now + _TOKEN_SKEW


async def _access_token(session: AsyncSession, app: OeApp | None = None) -> str:
    """取出访问令牌。快过期时先用 refresh_token 续期并立刻提交。"""
    if app is None:
        app = await _app_for_live(session)
    row = await session.scalar(
        select(OeToken).where(OeToken.oe_app_id == app.id, OeToken.is_deleted == 0)
    )
    if row is None:
        raise ApiError(503, "巨量未配置")
    if not get_settings().oceanengine.mock and token_needs_refresh(
        access_token=row.access_token,
        refresh_token=row.refresh_token,
        access_expire_at=row.access_expire_at,
        now=beijing_now(),
    ):
        await _refresh_stored_token(session, row)
    if not row.access_token:
        raise ApiError(503, "巨量未配置")
    return str(row.access_token)


async def _refresh_stored_token(session: AsyncSession, row: OeToken) -> None:
    """用库里的 refresh_token 换票。成功后立即提交，避免轮换后的新票被回滚。"""
    client = _live_client()
    try:
        body = await client.refresh_token(str(row.refresh_token or ""))
    except OceanEngineError as exc:
        row.last_error = str(exc)[:500]
        await session.flush()
        raise ApiError(503, "巨量令牌刷新失败") from exc
    remote = body.get("data") or {}
    access_token = str(remote.get("access_token") or "")
    refresh_token = str(remote.get("refresh_token") or "")
    if not access_token or not refresh_token:
        row.last_error = "刷新令牌没有返回 access_token 或 refresh_token"
        await session.flush()
        raise ApiError(503, "巨量令牌刷新失败")
    now = beijing_now()
    row.access_token = access_token
    row.refresh_token = refresh_token
    row.last_refresh_at = now
    row.last_error = None
    expires_in = remote.get("expires_in")
    refresh_expires_in = remote.get("refresh_token_expires_in")
    if expires_in is not None:
        row.access_expire_at = now + timedelta(seconds=int(expires_in))
    if refresh_expires_in is not None:
        row.refresh_expire_at = now + timedelta(seconds=int(refresh_expires_in))
    await session.commit()


async def _app_for_live(session: AsyncSession) -> OeApp:
    settings = get_settings().oceanengine
    if not settings.mock and settings.app_id.strip().isdigit():
        return await _ensure_configured_app(session)
    stmt = select(OeApp).where(OeApp.is_deleted == 0, OeApp.status == "active").order_by(OeApp.id)
    app_id = settings.app_id.strip()
    if app_id.isdigit():
        matched = await session.scalar(stmt.where(OeApp.app_id == int(app_id)).limit(1))
        if matched is not None:
            return matched
    found = await session.scalar(stmt.limit(1))
    if found is None:
        raise ApiError(503, "巨量未配置")
    return found


async def _app_for_callback(session: AsyncSession, state: str) -> OeApp:
    app_row_id = _callback_app_row_id(state)
    if app_row_id is not None:
        app = await session.get(OeApp, app_row_id)
        if app is None or app.is_deleted:
            raise ApiError(422, "state 无法对应应用")
        return app
    channel, agent_key = _callback_state(state)
    stmt = select(OeApp).where(OeApp.is_deleted == 0, OeApp.status == "active")
    if channel is not None:
        stmt = stmt.where(OeApp.channel == channel)
        if agent_key:
            stmt = stmt.where(OeApp.agent_key == agent_key)
    elif state.strip():
        raise ApiError(422, "state 无法对应应用")
    app = await session.scalar(stmt.order_by(OeApp.id).limit(1))
    if app is None:
        if state.strip():
            raise ApiError(422, "state 无法对应应用")
        raise ApiError(503, "巨量未配置")
    return app


def _callback_payload(state: str) -> dict[str, Any] | None:
    text = unquote(state).strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _callback_app_row_id(state: str) -> int | None:
    payload = _callback_payload(state)
    if payload is None:
        return None
    app_row_id = payload.get("appRowId")
    if isinstance(app_row_id, bool) or not isinstance(app_row_id, int):
        return None
    return app_row_id


def _callback_state(state: str) -> tuple[str | None, str]:
    payload = _callback_payload(state)
    if payload is None:
        return None, ""
    channel = "self" if payload.get("agency") is True else "third"
    return channel, str(payload.get("agentId") or "")


def _authorize_state(app: OeApp) -> str:
    """签名 state，再把双引号写成 %22。花括号保持原样。"""
    payload: dict[str, Any] = {"appRowId": int(app.id), "agentId": app.agent_key}
    if app.agency:
        payload["agency"] = True
    return sign_oauth_state(payload).replace('"', "%22")


async def _save_token(
    session: AsyncSession,
    app: OeApp,
    access_token: str,
    refresh_token: str,
    remote: dict[str, Any],
) -> None:
    row = await session.scalar(select(OeToken).where(OeToken.oe_app_id == app.id))
    if row is None:
        row = OeToken(oe_app_id=app.id)
        session.add(row)
    now = beijing_now()
    row.access_token = access_token
    row.refresh_token = refresh_token
    row.last_refresh_at = now
    row.last_error = None
    row.is_deleted = 0
    row.deleted_at = None
    expires_in = remote.get("expires_in")
    refresh_expires_in = remote.get("refresh_token_expires_in")
    if expires_in is not None:
        row.access_expire_at = now + timedelta(seconds=int(expires_in))
    if refresh_expires_in is not None:
        row.refresh_expire_at = now + timedelta(seconds=int(refresh_expires_in))
    await session.flush()


async def _sync_organizations(session: AsyncSession, app: OeApp) -> OeApp:
    client = _live_client()
    body = await client.list_authorized_accounts(await _access_token(session, app))
    rows = (body.get("data") or {}).get("list") or []
    seen: list[int] = []
    for raw in rows:
        if not isinstance(raw, dict) or raw.get("is_valid") is False:
            continue
        identity = _organization_identity(raw)
        if identity is None:
            continue
        ocean_account_id, name, role = identity
        seen.append(ocean_account_id)
        found = await session.scalar(
            select(OeOrganization).where(
                OeOrganization.oe_app_id == app.id,
                OeOrganization.ocean_account_id == ocean_account_id,
            )
        )
        version = str(raw.get("ocean_version") or "").strip()
        if found is None:
            session.add(
                OeOrganization(
                    oe_app_id=app.id,
                    ocean_account_id=ocean_account_id,
                    name=name,
                    account_role=role,
                    ocean_version=version,
                    status="active",
                    raw_payload=raw,
                )
            )
            continue
        found.name = name or found.name
        found.account_role = role or found.account_role
        if version:
            found.ocean_version = version
        found.status = "active"
        found.is_deleted = 0
        found.deleted_at = None
        found.raw_payload = raw
    missing = update(OeOrganization).where(
        OeOrganization.oe_app_id == app.id,
        OeOrganization.is_deleted == 0,
    )
    if seen:
        missing = missing.where(OeOrganization.ocean_account_id.not_in(seen))
    await session.execute(missing.values(status="invalid"))
    await session.flush()
    return app


async def _sync_advertisers(session: AsyncSession, app: OeApp) -> None:
    client = _live_client()
    token = await _access_token(session, app)
    orgs = (
        await session.scalars(
            select(OeOrganization).where(
                OeOrganization.oe_app_id == app.id,
                OeOrganization.is_deleted == 0,
                OeOrganization.account_role.in_(_ORG_ROLES),
            )
        )
    ).all()
    for org in orgs:
        accounts, complete = await _list_org_advertisers(client, token, session, org)
        for account in accounts:
            await _upsert_advertiser_name(
                session,
                app=app,
                org=org,
                account_id=int(account["account_id"]),
                account_name=str(account.get("account_name") or ""),
                raw_payload={"account": account},
            )
        if complete:
            seen = [int(account["account_id"]) for account in accounts]
            stale = update(AdvertiserAccount).where(
                AdvertiserAccount.organization_id == org.id,
                AdvertiserAccount.is_deleted == 0,
            )
            if seen:
                stale = stale.where(AdvertiserAccount.advertiser_id.not_in(seen))
            await session.execute(stale.values(sync_status="missing"))
        await _refresh_balance_batch(session, client, token, org)
    await session.flush()


async def _upsert_advertiser(
    session: AsyncSession,
    *,
    app: OeApp,
    org: OeOrganization,
    account_id: int,
    account_name: str,
    balance: Decimal,
    company_name: str,
    raw_payload: dict[str, Any],
) -> None:
    found = await session.scalar(
        select(AdvertiserAccount)
        .where(AdvertiserAccount.advertiser_id == account_id)
        .order_by(AdvertiserAccount.is_deleted, AdvertiserAccount.id)
        .limit(1)
    )
    now = beijing_now()
    if found is None:
        session.add(
            AdvertiserAccount(
                organization_id=org.id,
                oe_app_id=app.id,
                advertiser_id=account_id,
                name=account_name,
                valid_balance=balance,
                company_name=company_name,
                balance_synced_at=now,
                company_synced_at=now,
                sync_status="active",
                raw_payload=raw_payload,
            )
        )
        return
    found.organization_id = org.id
    found.oe_app_id = app.id
    found.name = account_name or found.name
    found.valid_balance = balance
    found.company_name = company_name
    found.balance_synced_at = now
    found.company_synced_at = now
    found.sync_status = "active"
    found.is_deleted = 0
    found.deleted_at = None
    found.raw_payload = raw_payload


def _balance_amount(data: dict[str, Any]) -> Decimal:
    """开放平台可能给 account_valid 或 valid_balance，都写入 valid_balance。"""
    raw = data.get("account_valid")
    if raw is None:
        raw = data.get("valid_balance")
    if raw is None:
        return Decimal("0.00")
    return Decimal(str(raw)).quantize(Decimal("0.01"))


def _company_name(body: dict[str, Any], account_id: int) -> str:
    """公开信息的公司名在 data[].company，或包在 data.advertisers 里。"""
    data = body.get("data")
    if isinstance(data, list):
        details = data
    elif isinstance(data, dict):
        details = data.get("advertisers") or []
    else:
        details = []
    for item in details:
        if not isinstance(item, dict):
            continue
        if int(item.get("id") or item.get("advertiser_id") or 0) == account_id:
            return str(item.get("company") or item.get("adv_company_name") or "")
    return ""


def _organization_identity(raw: dict[str, Any]) -> tuple[int, str, str] | None:
    """优先现行字段 account_id / account_name / account_type。"""
    account_id = raw.get("account_id")
    if account_id is None:
        account_id = raw.get("advertiser_id")
    if account_id is None:
        return None
    name = str(raw.get("account_name") or raw.get("advertiser_name") or "")
    role = str(raw.get("account_type") or raw.get("account_role") or "")
    return int(account_id), name, role


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
    client = _live_client()
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


def _page_count(data: dict[str, Any], batch_size: int) -> int:
    page_info = data.get("page_info") or {}
    total = page_info.get("total_page")
    if total is not None:
        return max(int(total), 1)
    if batch_size < _PAGE_SIZE:
        return 1
    return 10_000


def _account_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    account_id = raw.get("account_id")
    if account_id is None:
        account_id = raw.get("advertiser_id")
    if account_id is None:
        return None
    name = raw.get("account_name")
    if not name:
        name = raw.get("advertiser_name") or ""
    return {"account_id": int(account_id), "account_name": str(name)}


def list_exceeds_cap(data: dict[str, Any], page_size: int) -> bool:
    """名单超过开放平台实时接口的 1 万条上限。"""
    page_info = data.get("page_info") or {}
    total = page_info.get("total_number")
    if total is not None:
        return int(total) > _LIST_CAP
    pages = page_info.get("total_page")
    if pages is not None:
        return int(pages) * page_size > _LIST_CAP
    return False


def accounts_from_download(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把导出结果收成 account_id / account_name。"""
    data = payload.get("data")
    rows: list[Any] = []
    if isinstance(data, dict):
        nested = data.get("account_list") or data.get("list") or []
        if isinstance(nested, list):
            rows = nested
    elif isinstance(data, list):
        rows = data
    text = payload.get("raw_text")
    if not rows and isinstance(text, str) and text.strip():
        rows = _csv_account_rows(text)
    found: list[dict[str, Any]] = []
    for raw in rows:
        if isinstance(raw, dict):
            row = _account_row(raw)
            if row is not None:
                found.append(row)
    return found


def _csv_account_rows(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(item) for item in reader]


async def _list_org_advertisers(
    client: OceanEngineClient, token: str, session: AsyncSession, org: OeOrganization
) -> tuple[list[dict[str, Any]], bool]:
    """返回广告主名单，以及这份名单是否完整。"""
    org_id = int(org.ocean_account_id)
    if org.account_role == _CUSTOMER_ADMIN:
        return await _collect_capped(
            lambda page: client.list_customer_center_advertisers(
                token, org_id, page=page, page_size=_PAGE_SIZE
            )
        )
    first = await client.list_ebp_advertisers(token, org_id, page=1, page_size=_PAGE_SIZE)
    data = first.get("data") or {}
    if list_exceeds_cap(data, _PAGE_SIZE):
        return await _ebp_account_export(client, token, session, org)
    return await _collect_capped(
        lambda page: client.list_ebp_advertisers(token, org_id, page=page, page_size=_PAGE_SIZE)
    )


async def _collect_capped(fetch: Any) -> tuple[list[dict[str, Any]], bool]:
    """按页收集，不超过 1 万条。超过则名单不完整。"""
    page = 1
    found: list[dict[str, Any]] = []
    complete = True
    while page < 10_000 and len(found) < _LIST_CAP:
        body = await fetch(page)
        data = body.get("data") or {}
        if list_exceeds_cap(data, _PAGE_SIZE):
            complete = False
        batch = data.get("account_list") or data.get("list") or []
        if not isinstance(batch, list):
            break
        for raw in batch:
            if isinstance(raw, dict):
                row = _account_row(raw)
                if row is not None:
                    found.append(row)
        if len(found) >= _LIST_CAP and page < _page_count(data, len(batch)):
            complete = False
            break
        if page >= _page_count(data, len(batch)):
            break
        page += 1
    return found[:_LIST_CAP], complete


async def _ebp_account_export(
    client: OceanEngineClient, token: str, session: AsyncSession, org: OeOrganization
) -> tuple[list[dict[str, Any]], bool]:
    """超过 1 万条时创建或接着查异步导出。未完成则名单不完整。"""
    task_id = org.ebp_account_task_id
    status = org.ebp_account_task_status or ""
    if task_id is None or status in {"FAILED", "EXPIRED"}:
        created = await client.create_ebp_advertiser_task(token, int(org.ocean_account_id))
        task_id = int((created.get("data") or {}).get("task_id") or 0) or None
        org.ebp_account_task_id = task_id
        org.ebp_account_task_status = "EXECUTING"
        await session.commit()
    if task_id is None:
        return [], False
    for attempt in range(_TASK_POLLS):
        listed = await client.list_ebp_advertiser_tasks(
            token, int(org.ocean_account_id), [int(task_id)]
        )
        items = (listed.get("data") or {}).get("list") or []
        current = items[0] if items and isinstance(items[0], dict) else {}
        status = str(current.get("task_status") or "EXECUTING")
        org.ebp_account_task_status = status
        if status == "COMPLETED":
            payload = await client.download_ebp_advertiser_task(
                token, int(org.ocean_account_id), int(task_id)
            )
            rows = accounts_from_download(payload)
            await session.flush()
            if not rows:
                return [], False
            return rows, True
        if status in {"FAILED", "EXPIRED"}:
            await session.flush()
            return [], False
        if attempt + 1 < _TASK_POLLS:
            await asyncio.sleep(2)
    await session.flush()
    return [], False


async def _upsert_advertiser_name(
    session: AsyncSession,
    *,
    app: OeApp,
    org: OeOrganization,
    account_id: int,
    account_name: str,
    raw_payload: dict[str, Any],
) -> None:
    """只写名单。余额和公司名留给按批补齐。"""
    found = await session.scalar(
        select(AdvertiserAccount)
        .where(AdvertiserAccount.advertiser_id == account_id)
        .order_by(AdvertiserAccount.is_deleted, AdvertiserAccount.id)
        .limit(1)
    )
    if found is None:
        session.add(
            AdvertiserAccount(
                organization_id=org.id,
                oe_app_id=app.id,
                advertiser_id=account_id,
                name=account_name,
                sync_status="active",
                raw_payload=raw_payload,
            )
        )
        return
    found.organization_id = org.id
    found.oe_app_id = app.id
    found.name = account_name or found.name
    found.sync_status = "active"
    found.is_deleted = 0
    found.deleted_at = None
    found.raw_payload = raw_payload


async def _refresh_balance_batch(
    session: AsyncSession, client: OceanEngineClient, token: str, org: OeOrganization
) -> None:
    """给过期或未同步的户补余额和公司名。单户失败不影响名单。"""
    cutoff = beijing_now() - _BALANCE_TTL
    rows = (
        await session.scalars(
            select(AdvertiserAccount)
            .where(
                AdvertiserAccount.organization_id == org.id,
                AdvertiserAccount.is_deleted == 0,
                or_(
                    AdvertiserAccount.balance_synced_at.is_(None),
                    AdvertiserAccount.balance_synced_at < cutoff,
                ),
            )
            .order_by(AdvertiserAccount.id)
            .limit(_BALANCE_BATCH)
        )
    ).all()
    now = beijing_now()
    for row in rows:
        try:
            fund = await client.fund_get(token, int(row.advertiser_id))
            info = await client.advertiser_public_info(token, [int(row.advertiser_id)])
        except OceanEngineError:
            continue
        fund_data = fund.get("data") or {}
        row.valid_balance = _balance_amount(fund_data)
        row.company_name = _company_name(info, int(row.advertiser_id))
        row.balance_synced_at = now
        row.company_synced_at = now


def _advertiser_item(row: Any) -> dict[str, Any]:
    local_name = str(row.local_name or "").strip()
    balance = row.valid_balance
    return {
        "account_id": int(row.advertiser_id),
        "account_name": local_name or str(row.name or ""),
        "valid_balance": float(balance if balance is not None else 0),
        "adv_company_name": str(row.company_name or ""),
        "organization_id": int(row.ocean_account_id),
        "pitcher_nickname": str(row.nickname or ""),
        "manager_name": str(row.manager_name or ""),
        "sync_status": str(row.sync_status or "active"),
    }


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


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


def _report_metric(raw: dict[str, Any], name: str) -> Any:
    metrics = raw.get("metrics")
    if isinstance(metrics, dict) and name in metrics:
        return metrics.get(name)
    return raw.get(name)


def _report_promotion_id(raw: dict[str, Any]) -> int | None:
    dimensions = raw.get("dimensions")
    if isinstance(dimensions, dict):
        value = dimensions.get("cdp_promotion_id") or dimensions.get("promotion_id")
        if value is not None and str(value).isdigit():
            return int(value)
    value = raw.get("promotion_id")
    if value is None:
        return None
    return int(value)


async def _sync_reports(session: AsyncSession) -> None:
    client = _live_client()
    app = await _app_for_live(session)
    token = await _access_token(session, app)
    advertiser_ids = (
        await session.scalars(
            select(AdvertiserAccount.advertiser_id).where(
                AdvertiserAccount.oe_app_id == app.id,
                AdvertiserAccount.is_deleted == 0,
            )
        )
    ).all()
    now = beijing_now()
    day = now.strftime("%Y-%m-%d")
    rows: list[tuple[dict[str, Any], int]] = []
    for advertiser_id in advertiser_ids:
        page = 1
        while page < 10_000:
            body = await client.custom_report(
                token,
                {
                    "advertiser_id": int(advertiser_id),
                    "dimensions": json.dumps(["cdp_promotion_id"]),
                    "metrics": json.dumps(["stat_cost", "attribution_micro_game_0d_roi"]),
                    "filters": json.dumps([]),
                    "start_time": f"{day} 00:00:00",
                    "end_time": f"{day} 23:59:59",
                    "order_by": json.dumps([{"field": "stat_cost", "type": "DESC"}]),
                    "page": page,
                    "page_size": _PAGE_SIZE,
                },
            )
            data = body.get("data") or {}
            batch = data.get("rows") or data.get("list") or []
            if not isinstance(batch, list) or not batch:
                break
            for raw in batch:
                if isinstance(raw, dict):
                    rows.append((raw, int(advertiser_id)))
            if page >= _page_count(data, len(batch)):
                break
            page += 1
    for raw, advertiser_id in rows:
        promotion_id = _report_promotion_id(raw)
        if promotion_id is None:
            continue
        if raw.get("advertiser_id") is not None:
            advertiser_id = int(raw["advertiser_id"])
        stat_cost = Decimal(str(_report_metric(raw, "stat_cost") or 0)).quantize(Decimal("0.01"))
        roi = Decimal(str(_report_metric(raw, "attribution_micro_game_0d_roi") or 0)).quantize(
            Decimal("0.001")
        )
        found = await session.scalar(
            select(OeReportSnapshot).where(
                OeReportSnapshot.advertiser_id == advertiser_id,
                OeReportSnapshot.promotion_id == promotion_id,
            )
        )
        if found is None:
            session.add(
                OeReportSnapshot(
                    advertiser_id=advertiser_id,
                    promotion_id=promotion_id,
                    stat_cost=stat_cost,
                    attribution_micro_game_0d_roi=roi,
                    synced_at=now,
                    raw_payload=raw,
                )
            )
            continue
        found.stat_cost = stat_cost
        found.attribution_micro_game_0d_roi = roi
        found.synced_at = now
        found.raw_payload = raw
        found.is_deleted = 0
        found.deleted_at = None
    await session.flush()


async def _report_rows(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(
            OeReportSnapshot.promotion_id,
            OeReportSnapshot.stat_cost,
            OeReportSnapshot.attribution_micro_game_0d_roi,
            OeReportSnapshot.advertiser_id,
        )
        .where(OeReportSnapshot.is_deleted == 0)
        .order_by(OeReportSnapshot.promotion_id)
    )
    return [
        {
            "promotion_id": int(promotion_id),
            "stat_cost": float(stat_cost),
            "attribution_micro_game_0d_roi": float(roi),
            "advertiser_id": int(advertiser_id),
        }
        for promotion_id, stat_cost, roi, advertiser_id in rows.all()
    ]


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


def _should_pause(metric: str, row: dict[str, Any], threshold: float) -> bool:
    """operator 只有 lte：指标值小于等于阈值则暂停。"""
    if metric == "stat_cost":
        value = float(row["stat_cost"])
    else:
        value = float(row["attribution_micro_game_0d_roi"])
    return value <= threshold
