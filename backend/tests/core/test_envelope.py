"""信封与分页的形状自检。纯内存，不连库。"""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.envelope import ApiError, Envelope, register_exception_handlers, success
from app.core.pagination import PageData, PageParams, page_data


class Item(BaseModel):
    """自检用的列表元素。"""

    id: str


def build_app() -> FastAPI:
    """搭一个只用信封的小应用。"""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/one", response_model=Envelope[Item])
    async def one() -> dict:
        """成功信封。"""
        return success({"id": "1"})

    @app.get("/page", response_model=Envelope[PageData[Item]])
    async def page() -> dict:
        """分页信封。"""
        return success(page_data([Item(id="1")], 9, PageParams(page=2, page_size=20)))

    @app.get("/boom", response_model=Envelope[None])
    async def boom() -> dict:
        """业务失败。"""
        raise ApiError(409, "不能停用当前登录账号")

    @app.get("/crash", response_model=Envelope[None])
    async def crash() -> dict:
        """未捕获异常。"""
        raise RuntimeError("内部炸了")

    return app


class EnvelopeShapeTests(unittest.TestCase):
    """出参必须是 {code, message, data}，分页列表叫 list。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(build_app(), raise_server_exceptions=False)

    def test_success(self) -> None:
        """成功 code 为 200 且只有三个键。"""
        res = self.client.get("/one")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"code": 200, "message": "成功", "data": {"id": "1"}})

    def test_page(self) -> None:
        """分页出 list，不出 items。"""
        body = self.client.get("/page").json()
        self.assertEqual(
            body["data"],
            {"list": [{"id": "1"}], "total": 9, "page": 2, "page_size": 20},
        )

    def test_api_error(self) -> None:
        """ApiError 的 code 跟 HTTP 状态一致，data 为 null。"""
        res = self.client.get("/boom")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json(), {"code": 409, "message": "不能停用当前登录账号", "data": None})

    def test_unhandled(self) -> None:
        """未捕获异常收成 500，不外泄堆栈。"""
        res = self.client.get("/crash")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json(), {"code": 500, "message": "服务端未处理异常", "data": None})

    def test_not_found(self) -> None:
        """框架自己的 404 也走同一套信封。"""
        res = self.client.get("/nope")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], 404)
        self.assertIsNone(res.json()["data"])


if __name__ == "__main__":
    unittest.main()
