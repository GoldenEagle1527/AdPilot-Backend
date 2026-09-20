from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.envelope import ApiError, Envelope, success

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)

# 本阶段 mock：协议与正式登录相同，不查库。
_MOCK_USERS: dict[str, dict[str, str]] = {
    "admin": {
        "password": "admin123",
        "id": "1",
        "nickname": "管理员",
        "login_account": "admin",
        "tenant": "default",
        "enabled": "1",
    },
    "disabled": {
        "password": "disabled123",
        "id": "2",
        "nickname": "已停用",
        "login_account": "disabled",
        "tenant": "default",
        "enabled": "0",
    },
    "pitcher": {
        "password": "pitcher123",
        "id": "3",
        "nickname": "短剧投手",
        "login_account": "pitcher",
        "tenant": "default",
        "enabled": "1",
    },
}

_tokens: dict[str, dict[str, str]] = {}


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


def require_token(
    token: Annotated[str | None, Depends(read_bearer_token)],
) -> str:
    if not token or token not in _tokens:
        raise ApiError(401, "UNAUTHORIZED", "未带或 Token 无效")
    return token


def get_token_user(token: str) -> dict[str, str] | None:
    return _tokens.get(token)


@router.post("/login", response_model=Envelope[LoginData])
async def login(body: LoginRequest) -> dict:
    account = _MOCK_USERS.get(body.login_account)
    if account is None or account["password"] != body.password:
        raise ApiError(401, "INVALID_CREDENTIALS", "账号或密码不对")
    if account["enabled"] != "1":
        raise ApiError(403, "ACCOUNT_DISABLED", "账号停用")

    token = secrets.token_urlsafe(32)
    user = LoginUser(
        id=account["id"],
        nickname=account["nickname"],
        login_account=account["login_account"],
        tenant=account["tenant"],
    )
    _tokens[token] = user.model_dump()
    payload = LoginData(token=token, token_type="bearer", user=user)
    return success(payload.model_dump())
