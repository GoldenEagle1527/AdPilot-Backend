"""产品模板的保存和删除。标准和全域共用同一张表。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.standard_delivery.model import DeliveryProductSnapshot
from app.modules.standard_delivery.product_snapshot import create_snapshot, delete_snapshot
from app.modules.standard_delivery.schema import ProductSnapshotWrite

CREATED = datetime(2026, 10, 12, 11, 0, tzinfo=BEIJING)


class FakeSession:
    """按次序返回 scalar。"""

    def __init__(self, scalars: list[Any]) -> None:
        self.scalars = list(scalars)
        self.added: list[Any] = []
        self.commits = 0

    async def scalar(self, _statement: Any) -> Any:
        """返回下一份预置结果。"""
        return self.scalars.pop(0) if self.scalars else None

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """补上库里才有的主键和时间。"""
        row.id = row.id or 8
        row.created_date = row.created_date or CREATED
        row.updated_date = CREATED


def body() -> ProductSnapshotWrite:
    """一份和产品说明一致的产品模板。"""
    return ProductSnapshotWrite(
        name="甜宠预设",
        product_name="都市甜宠",
        product_image_id="img-cover",
        selling_points=["都市甜宠短剧"],
        call_to_action_buttons=["立即观看"],
    )


class SnapshotTests(unittest.TestCase):
    def test_create_stores_the_product_preset(self) -> None:
        """保存名称、主图、卖点和行动号召。"""
        session = FakeSession([None])
        item = asyncio.run(create_snapshot(session, body()))
        row = session.added[0]
        self.assertEqual(row.name, "甜宠预设")
        self.assertEqual(row.product_name, "都市甜宠")
        self.assertEqual(row.product_image_id, "img-cover")
        self.assertEqual(row.selling_points, ["都市甜宠短剧"])
        self.assertEqual(row.call_to_action_buttons, ["立即观看"])
        self.assertEqual(item["id"], "8")
        self.assertEqual(session.commits, 1)

    def test_delete_marks_the_row_and_missing_is_404(self) -> None:
        """删除只打软删。已经没有的再删是 404。"""
        row = DeliveryProductSnapshot(
            name="甜宠预设",
            product_name="都市甜宠",
            product_image_id="img-cover",
            selling_points=["都市甜宠短剧"],
            call_to_action_buttons=["立即观看"],
        )
        row.id = 8
        row.is_deleted = 0
        session = FakeSession([row])
        item = asyncio.run(delete_snapshot(session, 8))
        self.assertEqual(item, {"id": "8", "deleted": True})
        self.assertEqual(row.is_deleted, 1)
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(session.commits, 1)
        missing = FakeSession([None])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(delete_snapshot(missing, 8))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(missing.commits, 0)
