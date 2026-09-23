from __future__ import annotations

import json
import secrets
from datetime import timedelta
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.times import beijing_now
from app.core.envelope import ApiError, Envelope, success
from app.core.redis_client import get_redis

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)
_USER_TOKENS_KEY = "adpilot:user-tokens:{user_id}"
_TOKEN_PREFIX = "adpilot:token:"
_CONFLICT_PREFIX = "adpilot:session-conflict:"
_CONFLICT_REASON = "login_elsewhere"
_PRINCIPAL_STR = ("id", "nickname", "login_account", "tenant")
_JWT_ALG = "HS256"
_SUPERSEDE_LUA = """
local index_key = KEYS[1]
local new_jti = ARGV[1]
local payload = ARGV[2]
local ttl = tonumber(ARGV[3])
local token_prefix = ARGV[4]
local conflict_prefix = ARGV[5]
local conflict_payload = ARGV[6]
local old = redis.call('SMEMBERS', index_key)
for _, jti in ipairs(old) do
  if jti ~= new_jti then
    local tkey = token_prefix .. jti
    local remain = redis.call('TTL', tkey)
    if remain > 0 then
      redis.call('SET', conflict_prefix .. jti, conflict_payload, 'EX', remain)
    elseif remain == -1 then
      redis.call('SET', conflict_prefix .. jti, conflict_payload, 'EX', ttl)
    end
    redis.call('DEL', tkey)
  end
end
redis.call('DEL', index_key)
redis.call('SET', token_prefix .. new_jti, payload, 'EX', ttl)
redis.call('SADD', index_key, new_jti)
redis.call('EXPIRE', index_key, ttl)
return 1
"""


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


def _token_key(jti: str) -> str:
    """会话主体在 Redis 里的键。"""
    return f"{_TOKEN_PREFIX}{jti}"


def _user_tokens_key(user_id: str) -> str:
    return _USER_TOKENS_KEY.format(user_id=user_id)


def _conflict_key(jti: str) -> str:
    """被顶掉的会话在 Redis 里的冲突键。"""
    return f"{_CONFLICT_PREFIX}{jti}"


def _conflict_state() -> str:
    """同账号再次登录时写入 Redis 的冲突状态。"""
    return json.dumps({"reason": _CONFLICT_REASON}, ensure_ascii=False)


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


def session_jti_from_jwt(token: str) -> str | None:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_JWT_ALG],
            options={"require": ["exp", "iat", "jti", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    jti = claims.get("jti")
    if not isinstance(jti, str) or not jti:
        return None
    return jti


async def get_token_user(token: str) -> dict[str, Any] | None:
    jti = session_jti_from_jwt(token)
    if jti is None:
        return None
    raw = await get_redis().get(_token_key(jti))
    if not raw:
        return None
    return parse_principal(raw)


async def _is_login_conflict(jti: str) -> bool:
    """该 jti 是否因同账号再次登录被标成冲突。"""
    raw = await get_redis().get(_conflict_key(jti))
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and data.get("reason") == _CONFLICT_REASON


async def require_token(
    token: Annotated[str | None, Depends(read_bearer_token)],
) -> dict[str, Any]:
    """校验 Bearer。被其他登录顶掉的会话单独返回冲突。"""
    if not token:
        raise ApiError(401, "未带或 Token 无效")
    user = await get_token_user(token)
    if user is not None:
        return user
    jti = session_jti_from_jwt(token)
    if jti is not None and await _is_login_conflict(jti):
        raise ApiError(401, "账号已在其他地方登录")
    raise ApiError(401, "未带或 Token 无效")


def _encode_access_jwt(*, user_id: str, principal: dict[str, Any], jti: str, ttl: int) -> str:
    now = beijing_now()
    claims = {
        "sub": user_id,
        "nickname": str(principal["nickname"]),
        "login_account": str(principal["login_account"]),
        "tenant": str(principal["tenant"]),
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=_JWT_ALG)


async def issue_session(principal: dict[str, Any]) -> str:
    """签发唯一会话：同账号旧 jti 标为登录冲突后只保留这一次。"""
    jti = secrets.token_urlsafe(32)
    ttl = get_settings().token_ttl_seconds
    user_id = str(principal["id"])
    await get_redis().eval(
        _SUPERSEDE_LUA,
        1,
        _user_tokens_key(user_id),
        jti,
        json.dumps(principal, ensure_ascii=False),
        str(ttl),
        _TOKEN_PREFIX,
        _CONFLICT_PREFIX,
        _conflict_state(),
    )
    return _encode_access_jwt(user_id=user_id, principal=principal, jti=jti, ttl=ttl)


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


@router.post("/login", response_model=Envelope[LoginData], summary="密码登录")
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """查库验密后签发 Token。同账号只保留最新会话，旧会话在 Redis 标为冲突。"""
    from app.modules.system_admin.domain.access import authenticate_password

    status, principal = await authenticate_password(
        session, body.login_account, body.password
    )
    if status == "disabled":
        raise ApiError(403, "账号停用")
    if status != "ok" or principal is None:
        raise ApiError(401, "账号或密码不对")

    token = await issue_session(principal)
    user = LoginUser(
        id=str(principal["id"]),
        nickname=str(principal["nickname"]),
        login_account=str(principal["login_account"]),
        tenant=str(principal["tenant"]),
    )
    payload = LoginData(token=token, token_type="bearer", user=user)
    return success(payload.model_dump())
