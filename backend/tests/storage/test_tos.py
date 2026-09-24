"""火山引擎 TOS 公网地址拼接，以及上传成功和失败两条路径。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.storage.tos import object_url, put_object


class _Tos:
    """测试用的 TOS 配置。"""

    access_key = "ak"
    secret_key = "sk"
    endpoint = "tos-cn-beijing.volces.com"
    region = "cn-beijing"
    bucket_name = "demo"


class _Settings:
    """只暴露 tos 段的假配置。"""

    tos = _Tos()


class _Result:
    """假的 TOS 响应，只带状态码。"""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _Client:
    """假客户端，记下 put_object 的参数并返回预置状态码。"""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.calls: list[tuple[str, str, bytes]] = []

    def put_object(
        self,
        bucket: str,
        key: str,
        content: bytes | None = None,
        content_type: str | None = None,
    ) -> _Result:
        """记录一次上传并返回预置状态码。"""
        self.calls.append((bucket, key, content or b""))
        return _Result(self.status_code)


class TosUploadTests(unittest.TestCase):
    def test_object_url_uses_bucket_host(self) -> None:
        """公网地址是 https://桶名.接入点/对象键。"""
        with patch("app.storage.tos.get_settings", return_value=_Settings()):
            self.assertEqual(
                object_url("a/b.mp4"),
                "https://demo.tos-cn-beijing.volces.com/a/b.mp4",
            )

    def test_put_object_returns_public_url(self) -> None:
        """状态码 200 时返回公网地址，并把字节交给客户端。"""
        client = _Client(200)
        with (
            patch("app.storage.tos.get_settings", return_value=_Settings()),
            patch("app.storage.tos.tos_client", return_value=client),
        ):
            url = _run(put_object(b"video", "a/b.mp4"))
        self.assertEqual(url, "https://demo.tos-cn-beijing.volces.com/a/b.mp4")
        self.assertEqual(client.calls, [("demo", "a/b.mp4", b"video")])

    def test_put_object_rejects_non_200(self) -> None:
        """状态码不是 200 时抛出上传失败。"""
        client = _Client(403)
        with (
            patch("app.storage.tos.get_settings", return_value=_Settings()),
            patch("app.storage.tos.tos_client", return_value=client),
        ):
            with self.assertRaises(RuntimeError) as caught:
                _run(put_object(b"video", "a/b.mp4"))
        self.assertIn("status_code=403", str(caught.exception))


def _run(awaitable):
    """把协程跑完。测试里没有事件循环。"""
    import asyncio

    return asyncio.run(awaitable)
