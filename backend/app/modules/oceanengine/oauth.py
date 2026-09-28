"""授权链接、回调换票。换票成功后拉取组织和广告主。"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from urllib.parse import quote, unquote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.modules.account.commands import sign_oauth_state
from app.modules.account.model import OeApp, OeToken
from app.modules.oceanengine.runtime import _live_client, _prepare
from app.modules.oceanengine.sync import sync_from_oceanengine

_OAUTH_PAGE = "https://open.oceanengine.com/audit/oauth.html"


async def authorize_url(session: AsyncSession, channel: str) -> str:
    """按渠道拼授权页。取该渠道有效应用里 id 最小的一套，不用配置里的 app_id 顶替。"""
    await _prepare(session)
    if channel not in ("third", "self"):
        raise ApiError(422, "channel 只允许 third 或 self")
    settings = get_settings().oceanengine
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
