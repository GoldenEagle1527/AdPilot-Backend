"""常读列表签名与请求头。"""

from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.core.config import ChangduSettings
from app.modules.material.service import ChangduClient, ChangduError
from app.notify.changdu import ChangduNotify
from app.notify.dingtalk import DingTalkWebhook

_SETTINGS = ChangduSettings(
    base_url="https://openapi.changdupingtai.com/novelsale/openapi/content/aweme_series/list/v1/",
    distributor_id=1,
    secret_key="k",
    sync_interval_seconds=1800,
)


class ChangduSignTests(unittest.TestCase):
    def test_sign_matches_sorted_values(self) -> None:
        """渠道、密钥、时间戳与升序参数值拼成固定 MD5。"""
        client = ChangduClient(_SETTINGS)
        params = {"distributor_id": 1, "page_index": 0, "page_size": 20}
        self.assertEqual(client.sign(100, params), "ab42ea1e45ba178f1c10f12331bfe979")

    def test_zero_gender_is_signed_and_missing_filter_is_not(self) -> None:
        """性别 0 要参与签名；没传的筛选项不参与。"""
        client = ChangduClient(_SETTINGS)
        with_gender = {"distributor_id": 1, "gender": 0, "page_index": 0, "page_size": 20}
        without = {"distributor_id": 1, "page_index": 0, "page_size": 20}
        self.assertNotEqual(client.sign(100, with_gender), client.sign(100, without))


class ChangduListTests(unittest.TestCase):
    def test_request_uses_sign_headers(self) -> None:
        """列表请求带 header-ts / header-sign，并解析 total 与 data。"""

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/novelsale/openapi/content/aweme_series/list/v1/")
            self.assertEqual(request.url.params["distributor_id"], "1")
            self.assertEqual(request.url.params["page_index"], "0")
            self.assertEqual(request.url.params["page_size"], "20")
            self.assertEqual(request.headers["header-ts"], "100")
            expected = ChangduClient(_SETTINGS).sign(100, {"distributor_id": 1, "page_index": 0, "page_size": 20})
            self.assertEqual(request.headers["header-sign"], expected)
            return httpx.Response(200, json={"code": 200, "message": "OPENAPI_OK", "total": 2, "data": [{"book_id": 1}]})

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as http:
                page = await ChangduClient(_SETTINGS, http).list_aweme_series(ts=100)
            self.assertEqual(page.total, 2)
            self.assertEqual(page.data, [{"book_id": 1}])

        asyncio.run(run())

    def test_http_error_pushes_dingtalk(self) -> None:
        """HTTP 失败时把同一段错误推到钉钉，并仍抛出常读错误。"""
        sent: dict[str, object] = {}

        def changdu_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(502, text="bad gateway")

        def ding_handler(request: httpx.Request) -> httpx.Response:
            sent["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"errcode": 0, "errmsg": "ok"})

        async def run() -> None:
            changdu_transport = httpx.MockTransport(changdu_handler)
            ding_transport = httpx.MockTransport(ding_handler)
            async with httpx.AsyncClient(transport=changdu_transport) as http:
                async with httpx.AsyncClient(transport=ding_transport) as ding:
                    client = ChangduClient(
                        _SETTINGS,
                        http,
                        notify=ChangduNotify(
                            DingTalkWebhook("https://oapi.dingtalk.com/robot/send?access_token=t", ding)
                        ),
                    )
                    with self.assertRaises(ChangduError) as caught:
                        await client.list_aweme_series(ts=100)
            self.assertIn("HTTP 失败：502", str(caught.exception))

        asyncio.run(run())
        body = sent["body"]
        assert isinstance(body, dict)
        self.assertEqual(body["msgtype"], "text")
        self.assertTrue(body["text"]["content"].startswith("AdPilot "))
        self.assertIn("HTTP 失败：502", body["text"]["content"])

    def test_http_status_failure(self) -> None:
        """HTTP 不是 200 时直接失败。"""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"code": 200, "message": "ok", "total": 0, "data": []})

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as http:
                with self.assertRaises(ChangduError):
                    await ChangduClient(_SETTINGS, http).list_aweme_series(ts=100)

        asyncio.run(run())

    def test_business_code_failure(self) -> None:
        """业务码不是 200 时抛出常读错误。"""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": 400, "message": "bad", "total": 0, "data": []})

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as http:
                with self.assertRaises(ChangduError):
                    await ChangduClient(_SETTINGS, http).list_aweme_series(ts=100)

        asyncio.run(run())
