"""接收上传文件并转存到火山引擎 TOS。"""

from __future__ import annotations

import mimetypes
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.envelope import ApiError
from app.core.times import beijing_now
from app.storage.tos import put_object


def object_key(filename: str, user_id: str, now: datetime) -> str:
    """按 {项目名}/{年}/{月}/{日}/{用户}/{文件名_uuid 或 uuid}.后缀 拼对象键。没有后缀就拒绝。"""
    ext = os.path.splitext(filename)[1].lower()
    if len(ext) < 2 or not ext[1:].isalnum():
        raise ApiError(400, "文件缺少后缀")
    stem = os.path.splitext(os.path.basename(filename))[0].strip().replace("/", "").replace("\\", "")
    token = uuid4()
    name = f"{stem}_{token}" if stem else str(token)
    return f"{get_settings().app_name}/{now:%Y/%m/%d}/{user_id}/{name}{ext}"


def sniffed_type(filename: str, content_type: str | None) -> str:
    """优先用上传声明的类型，没有就按文件名猜，再不行用二进制流。"""
    return content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"


async def upload_file(file: UploadFile, user_id: str) -> dict[str, Any]:
    """读前端文件，转到 TOS，返回公网地址和对象键。"""
    # ponytail: 整文件读进内存再上传。大文件会顶满进程，要流式再改 put_object。
    key = object_key(file.filename or "", user_id, beijing_now())
    content = await file.read()
    if not content:
        raise ApiError(400, "文件内容为空")
    content_type = sniffed_type(file.filename or "", file.content_type)
    try:
        url = await put_object(content, key, content_type=content_type)
    except RuntimeError as exc:
        raise ApiError(503, "文件上传失败") from exc
    return {
        "url": url,
        "key": key,
        "original_name": file.filename or "",
        "size": len(content),
        "content_type": content_type,
    }
