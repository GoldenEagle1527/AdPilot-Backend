from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

DICT_CODE_DEFAULT_PASSWORD = "default_password"
_ITERATIONS = 120_000
_SCHEME = "pbkdf2_sha256"


def hash_password(plain: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return (
        f"{_SCHEME}${_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(dk).decode('ascii')}"
    )


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        scheme, iter_s, salt_b64, hash_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != _SCHEME:
        return False
    try:
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
    except (ValueError, OSError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


async def load_default_password(session: AsyncSession) -> str | None:
    """后续 create/reset 用户接库时用；本阶段登录仍走 core mock。"""
    from sqlalchemy import select

    from app.modules.system_admin.domain.models import DictItem

    result = await session.execute(
        select(DictItem.value).where(DictItem.dict_code == DICT_CODE_DEFAULT_PASSWORD)
    )
    return result.scalar_one_or_none()


async def hash_password_or_default(session: AsyncSession, plain: str | None) -> str:
    password = (plain or "").strip()
    if not password:
        configured = await load_default_password(session)
        if not configured:
            raise RuntimeError("缺少字典项 default_password（Q-PERM-5）")
        password = configured
    return hash_password(password)
