"""常读客户端签名、请求头、翻页和统一报错；常读失败的钉钉通知。"""

from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.clients.changdu import ChangduClient, ChangduError
from app.core.config import ChangduSettings
from app.notify.changdu import ChangduNotify
from app.notify.dingtalk import DingTalkWebhook

_SETTINGS = ChangduSettings(
    base_url="https://openapi.changdupingtai.com/novelsale/openapi/content/aweme_series/list/v1/",
    promotion_list_url="https://openapi.changdupingtai.com/novelsale/openapi/promotion/list/v2/",
    distributor_id=1,
    secret_key="k",
    sync_interval_seconds=1800,
)


def call(handler, method: str, **kwargs):
    """用假常读跑一次客户端方法。"""

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await getattr(ChangduClient(_SETTINGS, http), method)(ts=100, **kwargs)

    return asyncio.run(run())


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
            self.assertEqual(dict(request.url.params), {"distributor_id": "1", "page_index": "0", "page_size": "20"})
            self.assertEqual(request.headers["header-ts"], "100")
            expected = ChangduClient(_SETTINGS).sign(100, {"distributor_id": 1, "page_index": 0, "page_size": 20})
            self.assertEqual(request.headers["header-sign"], expected)
            return httpx.Response(200, json={"code": 200, "message": "OPENAPI_OK", "total": 2, "data": [{"book_id": 1}]})

        page = call(handler, "list_aweme_series")
        self.assertEqual(page.total, 2)
        self.assertEqual(page.data, [{"book_id": 1}])

    def test_failures_raise_changdu_error(self) -> None:
        """HTTP 不是 200、不是 JSON、业务码不是 200 都抛常读错误；业务失败正文是常读 message。"""
        cases = [
            (httpx.Response(502, text="bad gateway"), "常读 HTTP 失败：502"),
            (httpx.Response(200, text="oops"), "常读返回不是 JSON：HTTP 200"),
            (httpx.Response(200, json={"code": 400, "message": "bad"}), "bad"),
        ]
        for response, message in cases:
            with self.subTest(message=message), self.assertRaises(ChangduError) as caught:
                call(lambda request, r=response: r, "list_aweme_series")
            self.assertEqual(str(caught.exception), message)


class ChangduPromotionTests(unittest.TestCase):
    def test_pages_until_no_more_with_signed_params(self) -> None:
        """推广链带签名按 offset 翻页，has_more 为假就停，结果拼在一起。"""
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            params = dict(request.url.params)
            seen.append(params["offset"])
            self.assertEqual(request.url.path, "/novelsale/openapi/promotion/list/v2/")
            self.assertEqual(params["book_id"], "8")
            expected = ChangduClient(_SETTINGS).sign(
                100, {"book_id": "8", "distributor_id": 1, "limit": 100, "offset": int(params["offset"])}
            )
            self.assertEqual(request.headers["header-sign"], expected)
            if params["offset"] == "0":
                return httpx.Response(200, json={"code": 200, "has_more": True, "next_offset": 100, "result": [{"a": 1}]})
            return httpx.Response(200, json={"code": 200, "has_more": False, "result": [{"a": 2}]})

        self.assertEqual(call(handler, "list_promotions", book_id=8), [{"a": 1}, {"a": 2}])
        self.assertEqual(seen, ["0", "100"])

    def test_empty_page_stops_even_if_has_more(self) -> None:
        """常读 has_more 一直为真但本页为空时停下，不死循环。"""
        calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(200, json={"code": 200, "has_more": True, "next_offset": 100, "result": []})

        self.assertEqual(call(handler, "list_promotions", book_id=8), [])
        self.assertEqual(len(calls), 1)


class ChangduNotifyTests(unittest.TestCase):
    def _notify(self, handler) -> None:
        """用假钉钉推一条短剧列表拉取失败。"""

        async def run() -> None:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as ding:
                webhook = DingTalkWebhook("https://oapi.dingtalk.com/robot/send?access_token=t", ding)
                await ChangduNotify(webhook).sync_failed("常读 HTTP 失败：502")

        asyncio.run(run())

    def test_pushes_with_keyword(self) -> None:
        """通知带全局关键词和常读错误。"""
        sent: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            sent.update(json.loads(request.content.decode()))
            return httpx.Response(200, json={"errcode": 0, "errmsg": "ok"})

        self._notify(handler)
        content = sent["text"]["content"]  # type: ignore[index]
        self.assertTrue(content.startswith("AdPilot "))
        self.assertIn("常读短剧列表拉取失败：常读 HTTP 失败：502", content)

    def test_dingtalk_failure_is_swallowed(self) -> None:
        """钉钉报错或连不上都不抛，不盖住原来的常读错误。"""
        self._notify(lambda request: httpx.Response(200, json={"errcode": 310000, "errmsg": "keyword"}))

        def unreachable(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        self._notify(unreachable)


if __name__ == "__main__":
    unittest.main()
