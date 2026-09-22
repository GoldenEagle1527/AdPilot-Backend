"""漫剧列表的时间展示和筛选条件。"""

from __future__ import annotations

import unittest
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.times import BEIJING
from app.modules.material.schema import ManhuaSeriesQuery
from app.modules.material.service import to_item


class StampParamTests(unittest.TestCase):
    def test_query_rejects_date_without_time(self) -> None:
        """入参不是 YYYY-MM-DD HH:MM:SS 时，请求在进业务前被拒绝。"""
        app = FastAPI()

        @app.get("/t")
        def _probe(query: Annotated[ManhuaSeriesQuery, Query()]) -> dict[str, str | None]:
            """试查询模型的时间入参。"""
            return {"value": query.estimate_publish_time_from}

        client = TestClient(app)
        rejected = client.get("/t", params={"estimate_publish_time_from": "2026-09-22"})
        self.assertEqual(rejected.status_code, 422)
        accepted = client.get("/t", params={"estimate_publish_time_from": "2026-09-22 10:00:00"})
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["value"], "2026-09-22 10:00:00")


class QueryRangeTests(unittest.TestCase):
    def test_reversed_time_and_episodes_are_rejected(self) -> None:
        """结束早于开始、集数上限小于下限，入参直接拒绝。"""
        with self.assertRaises(ValidationError):
            ManhuaSeriesQuery(
                estimate_publish_time_from="2026-09-22 10:00:00",
                estimate_publish_time_to="2026-09-21 10:00:00",
            )
        with self.assertRaises(ValidationError):
            ManhuaSeriesQuery(episode_amount_min=10, episode_amount_max=2)


class ItemTests(unittest.TestCase):
    def test_item_returns_tab_text(self) -> None:
        """列表项原样返回 IAA/IAP，部门恒空。"""

        class Row:
            id = 7
            playlet_id = 9
            book_id = 8
            category_text = "玄幻脑洞"
            tab_text = "IAP"
            single_price = "50"
            thumb_url = ""
            book_name = "剧"
            episode_amount = 12
            publish_status = 2
            delivery_status = True
            publish_time = "2026-09-22 01:00:00"
            estimate_publish_time = ""
            create_time = "坏的"
            collected_at = datetime(2026, 9, 22, 1, 0, tzinfo=BEIJING)
            douyin_nick_name = "号"

        item = to_item(Row())
        self.assertEqual(item["tab_text"], "IAP")
        self.assertEqual(item["publish_time"], "2026-09-22 01:00:00")
        self.assertEqual(item["create_time"], "坏的")
        self.assertIsNone(item["department_name"])
        self.assertEqual(item["id"], "7")
        self.assertEqual(item["collected_at"], "2026-09-22T01:00:00+08:00")
