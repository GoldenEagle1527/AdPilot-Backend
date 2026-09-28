"""巨量应用、访问令牌和开放平台客户端。各业务文件只从这里取运行时。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.modules.account.model import OeApp, OeToken
from app.modules.account.seed import ensure_oceanengine_seed
from app.modules.oceanengine.client import OceanEngineClient, OceanEngineError

_PAGE_SIZE = 100
_TOKEN_SKEW = timedelta(minutes=5)


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


def _page_count(data: dict[str, Any], batch_size: int) -> int:
    page_info = data.get("page_info") or {}
    total = page_info.get("total_page")
    if total is not None:
        return max(int(total), 1)
    if batch_size < _PAGE_SIZE:
        return 1
    return 10_000
