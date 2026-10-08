"""商品上传改用 library_no 和 book_name。假客户端不 503，并可写入 oe_product。"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.modules.account.model import OeProduct, ProductLibrary
from app.modules.oceanengine.delivery import upload_image, upload_product
from app.modules.oceanengine.runtime import install_ocean_client
from app.modules.oceanengine.schema import ProductCreate


class StubClient:
    """不连库、不发 HTTP。"""

    requires_stored_token = False

    def __init__(self, product_id: int = 9001, image_id: str = "img-abc") -> None:
        self.product_id = product_id
        self.image_id = image_id
        self.product_body: dict[str, Any] | None = None
        self.image_body: dict[str, Any] | None = None

    async def upload_product(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """按传入正文回一个商品号。"""
        self.product_body = body
        return {"data": {"product_id": self.product_id}}

    async def upload_image(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """按文件上传回一个图片号。"""
        self.image_body = body
        return {"data": {"id": self.image_id}}


class Sess:
    """只实现商品上传用到的会话方法。"""

    def __init__(self, library: ProductLibrary | None) -> None:
        self.library = library
        self.added: list[Any] = []

    async def scalar(self, _statement: Any) -> ProductLibrary | None:
        """按预置库返回。"""
        return self.library

    def add(self, row: Any) -> None:
        """记下商品行。"""
        self.added.append(row)

    async def flush(self) -> None:
        """不落库。"""

    async def refresh(self, row: Any) -> None:
        """保持调用方已经写上的商品号。"""
        row.id = row.id or 3


def _library() -> ProductLibrary:
    row = ProductLibrary(
        name="视频库",
        library_no=77001,
        library_kind="video",
        organization_id=1,
        library_role="fallback",
        uploaded_count=2,
    )
    row.id = 6
    return row


class ProductBodyTests(unittest.TestCase):
    def test_body_is_advertiser_library_no_and_book_name(self) -> None:
        """不再收 drama_name 和 file_url。"""
        body = ProductCreate(advertiser_id=90001, library_no=77001, book_name="甲剧")
        self.assertEqual(body.book_name, "甲剧")
        with self.assertRaises(ValidationError):
            ProductCreate(advertiser_id=90001, library_no=77001, book_name="甲剧", drama_name="甲剧")
        with self.assertRaises(ValidationError):
            ProductCreate(advertiser_id=90001, library_no=77001, book_name="甲剧", file_url="https://example.com/a")


class UploadTests(unittest.TestCase):
    def tearDown(self) -> None:
        install_ocean_client(None)

    def test_fake_path_writes_product_and_does_not_503(self) -> None:
        """假客户端回 9001 段的号，剧名写入 oe_product，不要求文件地址。"""
        client = StubClient()
        install_ocean_client(client)
        library = _library()
        session = Sess(library)
        item = asyncio.run(
            upload_product(
                session,
                ProductCreate(advertiser_id=90001, library_no=77001, book_name="甲剧"),
            )
        )
        self.assertEqual(item["product_id"], 9001)
        self.assertEqual(item["library_no"], 77001)
        self.assertEqual(item["book_name"], "甲剧")
        self.assertEqual(item["advertiser_id"], 90001)
        self.assertEqual(client.product_body["book_name"], "甲剧")
        self.assertNotIn("drama_name", client.product_body or {})
        self.assertNotIn("file_url", client.product_body or {})
        row = session.added[0]
        self.assertIsInstance(row, OeProduct)
        self.assertEqual(row.drama_name, "甲剧")
        self.assertIsNone(row.file_url)
        self.assertEqual(row.ocean_product_id, 9001)
        self.assertEqual(library.uploaded_count, 3)

    def test_missing_library_is_not_found(self) -> None:
        """library_no 对不上则 404，不写商品。"""
        install_ocean_client(StubClient())
        session = Sess(None)
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                upload_product(
                    session,
                    ProductCreate(advertiser_id=1, library_no=1, book_name="甲剧"),
                )
            )
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.added, [])

    def test_image_upload_uses_the_file_and_rejects_a_video_id(self) -> None:
        """本地文件走 UPLOAD_BY_FILE。视频式 local- 号不能当主图。"""
        client = StubClient()
        install_ocean_client(client)
        item = asyncio.run(upload_image(Sess(None), 90001, "cover.png", b"png"))
        self.assertEqual(item["image_id"], "img-abc")
        self.assertEqual(client.image_body["upload_type"], "UPLOAD_BY_FILE")
        self.assertNotIn("image_url", client.image_body or {})
        self.assertEqual(client.image_body["image_file"], b"png")
        with self.assertRaises(ApiError) as empty:
            asyncio.run(upload_image(Sess(None), 90001, "cover.png", b""))
        self.assertEqual(empty.exception.status_code, 400)
        install_ocean_client(StubClient(image_id="local-abc"))
        with self.assertRaises(ApiError) as video_like:
            asyncio.run(upload_image(Sess(None), 90001, "cover.png", b"png"))
        self.assertEqual(video_like.exception.status_code, 502)
