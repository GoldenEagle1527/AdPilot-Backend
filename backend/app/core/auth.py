from __future__ import annotations

import json
import secrets
from typing import Annotated

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


async def get_token_user(token: str) -> dict[str, str] | None:
    raw = await get_redis().get(_token_key(token))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return {str(key): str(value) for key, value in data.items()}


async def require_token(
    token: Annotated[str | None, Depends(read_bearer_token)],
) -> str:
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    user = await get_token_user(token)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    return token


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

    token = secrets.token_urlsafe(32)
    ttl = get_settings().token_ttl_seconds
    await get_redis().set(_token_key(token), json.dumps(principal), ex=ttl)
    user = LoginUser(
        id=principal["id"],
        nickname=principal["nickname"],
        login_account=principal["login_account"],
        tenant=principal["tenant"],
    )
    payload = LoginData(token=token, token_type="bearer", user=user)
    return success(payload.model_dump())
