"""文件上传：缺后缀、空文件、成功转存、TOS 失败。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.file.service import upload_file

_NOW = datetime(2026, 9, 24, 10, 0, tzinfo=BEIJING)
_FILE_ID = UUID("018f0000-0000-7000-8000-000000000001")


class _File:
    """假的上传文件，只提供文件名、类型和 read。"""

    def __init__(self, filename: str | None, content: bytes, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        """返回预置字节。"""
        return self._content


class UploadTests(unittest.TestCase):
    def test_missing_extension_is_rejected(self) -> None:
        """没有后缀时 400，且不读内容、不上传。"""
        file = _File("poster", b"abc", "image/png")
        with self.assertRaises(ApiError) as caught:
            asyncio.run(upload_file(file, "5"))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "文件缺少后缀")

    def test_empty_file_is_rejected(self) -> None:
        """内容为空时 400。"""
        file = _File("a.mp4", b"", "video/mp4")
        with self.assertRaises(ApiError) as caught:
            asyncio.run(upload_file(file, "5"))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "文件内容为空")

    def test_upload_returns_public_url(self) -> None:
        """有文件名时对象键带项目、日期、用户和文件名_uuid。"""
        file = _File("海报.MP4", b"video", "video/mp4")
        put = AsyncMock(return_value="https://demo.example/adpilot/2026/09/24/5/海报.mp4")
        with (
            patch("app.modules.file.service.beijing_now", return_value=_NOW),
            patch("app.modules.file.service.uuid4", return_value=_FILE_ID),
            patch("app.modules.file.service.put_object", put),
        ):
            result = asyncio.run(upload_file(file, "5"))
        key = f"adpilot/2026/09/24/5/海报_{_FILE_ID}.mp4"
        self.assertEqual(result["key"], key)
        self.assertEqual(result["url"], put.return_value)
        self.assertEqual(result["original_name"], "海报.MP4")
        self.assertEqual(result["size"], 5)
        self.assertEqual(result["content_type"], "video/mp4")
        put.assert_awaited_once_with(b"video", key, content_type="video/mp4")

    def test_tos_failure_is_downstream(self) -> None:
        """TOS 上传失败按下游故障返回 503。"""
        file = _File("a.mp4", b"video", None)
        with (
            patch("app.modules.file.service.put_object", AsyncMock(side_effect=RuntimeError("status_code=403"))),
        ):
            with self.assertRaises(ApiError) as caught:
                asyncio.run(upload_file(file, "5"))
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.message, "文件上传失败")

    def test_blank_name_uses_uuid_only(self) -> None:
        """取不到文件名时最后一段只有 uuid。"""
        file = _File(" .mp4", b"video", "video/mp4")
        put = AsyncMock(return_value="https://demo.example/adpilot/2026/09/24/5/x.mp4")
        with (
            patch("app.modules.file.service.beijing_now", return_value=_NOW),
            patch("app.modules.file.service.uuid4", return_value=_FILE_ID),
            patch("app.modules.file.service.put_object", put),
        ):
            result = asyncio.run(upload_file(file, "5"))
        self.assertEqual(result["key"], f"adpilot/2026/09/24/5/{_FILE_ID}.mp4")
