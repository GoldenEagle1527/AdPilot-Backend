"""火山引擎 TOS：把文件传到对象存储，返回公网地址。"""

from __future__ import annotations

import asyncio

import tos

from app.core.config import get_settings

_client: tos.TosClientV2 | None = None


def tos_client() -> tos.TosClientV2:
    """惰性创建 TOS 客户端。"""
    global _client
    if _client is None:
        settings = get_settings().tos
        _client = tos.TosClientV2(
            settings.access_key,
            settings.secret_key,
            settings.endpoint,
            settings.region,
        )
    return _client


def object_url(object_key: str) -> str:
    """拼接对象的公网访问地址。"""
    settings = get_settings().tos
    return f"https://{settings.bucket_name}.{settings.endpoint}/{object_key}"


async def put_object(content: bytes, object_key: str, content_type: str | None = None) -> str:
    """上传字节内容到 TOS，返回公网访问地址。"""
    settings = get_settings().tos
    result = await asyncio.to_thread(
        tos_client().put_object,
        settings.bucket_name,
        object_key,
        content=content,
        content_type=content_type,
    )
    if result.status_code != 200:
        raise RuntimeError(f"TOS 上传失败，status_code={result.status_code}")
    return object_url(object_key)
