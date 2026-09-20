from __future__ import annotations

import json
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.envelope import ApiError, Envelope, success
from app.core.redis_client import get_redis

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)
_TOKEN_KEY = "adpilot:token:{token}"
_USER_TOKENS_KEY = "adpilot:user-tokens:{user_id}"
_PRINCIPAL_STR = ("id", "nickname", "login_account", "tenant")


class LoginRequest(BaseModel):
    login_account: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginUser(BaseModel):
    id: str
    nickname: str
    login_account: str
    tenant: str


class LoginData(BaseModel):
    token: str
    token_type: str
    user: LoginUser


def read_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials


def _token_key(token: str) -> str:
    return _TOKEN_KEY.format(token=token)


def _user_tokens_key(user_id: str) -> str:
    return _USER_TOKENS_KEY.format(user_id=user_id)


def parse_principal(raw: str) -> dict[str, Any] | None:
    """Redis 会话 JSON → 主体。身份字段为 str；其余键原样保留（含 menu_ids list）。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if any(key not in data for key in _PRINCIPAL_STR):
        return None
    principal: dict[str, Any] = {key: str(data[key]) for key in _PRINCIPAL_STR}
    for key, value in data.items():
        if key in _PRINCIPAL_STR:
            continue
        principal[key] = value
    return principal


async def get_token_user(token: str) -> dict[str, Any] | None:
    raw = await get_redis().get(_token_key(token))
    if not raw:
        return None
    return parse_principal(raw)


async def require_token(
    token: Annotated[str | None, Depends(read_bearer_token)],
) -> dict[str, Any]:
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    user = await get_token_user(token)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    return user


async def issue_session(principal: dict[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    ttl = get_settings().token_ttl_seconds
    user_id = str(principal["id"])
    redis = get_redis()
    pipe = redis.pipeline()
    pipe.set(_token_key(token), json.dumps(principal, ensure_ascii=False), ex=ttl)
    pipe.sadd(_user_tokens_key(user_id), token)
    pipe.expire(_user_tokens_key(user_id), ttl)
    await pipe.execute()
    return token


async def drop_user_sessions(user_id: str) -> None:
    redis = get_redis()
    index_key = _user_tokens_key(user_id)
    tokens = await redis.smembers(index_key)
    if tokens:
        pipe = redis.pipeline()
        for token in tokens:
            pipe.delete(_token_key(str(token)))
        pipe.delete(index_key)
        await pipe.execute()
        return
    await redis.delete(index_key)


async def rewrite_user_sessions(user_id: str, principal: dict[str, Any]) -> None:
    """角色/菜单变更后刷新该用户未过期会话。幽灵 token 从索引里摘掉。"""
    redis = get_redis()
    index_key = _user_tokens_key(user_id)
    tokens = await redis.smembers(index_key)
    if not tokens:
        return
    payload = json.dumps(principal, ensure_ascii=False)
    default_ttl = get_settings().token_ttl_seconds
    for token in tokens:
        token_str = str(token)
        tkey = _token_key(token_str)
        ttl = await redis.ttl(tkey)
        if ttl == -2:
            await redis.srem(index_key, token_str)
            continue
        ex = ttl if ttl > 0 else default_ttl
        await redis.set(tkey, payload, ex=ex)


@router.post("/login", response_model=Envelope[LoginData])
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    from app.modules.system_admin.domain.access import authenticate_password

    status, principal = await authenticate_password(
        session, body.login_account, body.password
    )
    if status == "disabled":
        raise ApiError(403, "ACCOUNT_DISABLED", "账号停用")
    if status != "ok" or principal is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "账号或密码不对")

    token = await issue_session(principal)
    user = LoginUser(
        id=str(principal["id"]),
        nickname=str(principal["nickname"]),
        login_account=str(principal["login_account"]),
        tenant=str(principal["tenant"]),
    )
    payload = LoginData(token=token, token_type="bearer", user=user)
    return success(payload.model_dump())
