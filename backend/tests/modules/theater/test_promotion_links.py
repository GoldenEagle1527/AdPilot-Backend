"""端原生推广链：列表入参与过滤、出参回填；编辑入参约束和只改传了的字段。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.material.model import ManhuaSeries
from app.modules.theater.model import TheaterApp, TheaterPromotionLink
from app.modules.theater.schema import PromotionLinkQuery, PromotionLinkUpdate
from app.modules.theater.service import (
    list_promotion_links,
    promotion_link_filters,
    update_promotion_link,
)

SERVICE = "app.modules.theater.service"


def make_link(**kwargs) -> TheaterPromotionLink:
    """造一条内存里的推广链行。"""
    row = TheaterPromotionLink(
        series_id=8,
        theater_app_id=kwargs.get("theater_app_id"),
        promotion_url="https://x/1",
        recharge_template_name="中额",
        is_enabled=True,
        publish_time=datetime(2026, 9, 20, 10, tzinfo=BEIJING),
        promotion_create_time=kwargs.get("promotion_create_time"),
    )
    row.id = 5
    return row


class QueryTests(unittest.TestCase):
    def test_dates_order_and_unknown_params(self) -> None:
        """首发日期只收日期，止早于起拒绝；多传参数拒绝。"""
        with self.assertRaises(ValidationError):
            PromotionLinkQuery(publish_date_from="2026-09-20", publish_date_to="2026-09-19")
        with self.assertRaises(ValidationError):
            PromotionLinkQuery(book_name="甲剧")
        PromotionLinkQuery(publish_date_from="2026-09-20", publish_date_to="2026-09-20")


class FilterTests(unittest.TestCase):
    def test_publish_dates_cover_whole_days_and_exact_filters(self) -> None:
        """首发日期左闭右闭：止日期当天整天都算；剧场、剧名、启用状态精确匹配。"""
        query = PromotionLinkQuery(
            publish_date_from="2026-09-20",
            publish_date_to="2026-09-21",
            theater_app_id=3,
            series_id=8,
            is_enabled=False,
        )
        sql = " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True})) for item in promotion_link_filters(query)
        )
        self.assertIn("theater_promotion_links.is_deleted = 0", sql)
        self.assertIn("theater_promotion_links.publish_time >= '2026-09-20 00:00:00+08:00'", sql)
        self.assertIn("theater_promotion_links.publish_time < '2026-09-22 00:00:00+08:00'", sql)
        self.assertIn("theater_promotion_links.theater_app_id = 3", sql)
        self.assertIn("theater_promotion_links.series_id = 8", sql)
        self.assertIn("theater_promotion_links.is_enabled = false", sql)


class ListTests(unittest.TestCase):
    def test_items_fill_names_and_times(self) -> None:
        """剧名取剧库、剧场名取应用；对应不上剧场为 null；时间到秒、没有为 null。"""
        rows = [(make_link(theater_app_id=3), "甲剧", "番茄剧场"), (make_link(), "甲剧", None)]
        with patch(f"{SERVICE}.page_promotion_links", new=AsyncMock(return_value=(rows, 2))):
            data = asyncio.run(list_promotion_links(None, PromotionLinkQuery()))
        with_app, without_app = data["list"]
        self.assertEqual(data["total"], 2)
        self.assertEqual((with_app["theater_app_id"], with_app["theater_app_name"]), ("3", "番茄剧场"))
        self.assertEqual((without_app["theater_app_id"], without_app["theater_app_name"]), (None, None))
        self.assertEqual(with_app["book_name"], "甲剧")
        self.assertEqual(with_app["publish_time"], "2026-09-20T10:00:00+08:00")
        self.assertIsNone(with_app["promotion_create_time"])


class UpdateBodyTests(unittest.TestCase):
    def test_rules(self) -> None:
        """至少改一项；剧场可传 null 清空，其它字段不能传 null；剧名不在可改字段里。"""
        with self.assertRaises(ValidationError):
            PromotionLinkUpdate()
        with self.assertRaises(ValidationError):
            PromotionLinkUpdate(promotion_url=None)
        with self.assertRaises(ValidationError):
            PromotionLinkUpdate(book_name="乙剧")
        with self.assertRaises(ValidationError):
            PromotionLinkUpdate(promotion_url="  ")
        self.assertEqual(PromotionLinkUpdate(theater_app_id=None).model_dump(exclude_unset=True), {"theater_app_id": None})


class UpdateTests(unittest.TestCase):
    def _run(self, body: PromotionLinkUpdate, link: TheaterPromotionLink | None, app: TheaterApp | None):
        """用假会话编辑一条推广链。"""
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock(return_value=ManhuaSeries(book_name="甲剧"))
        with (
            patch(f"{SERVICE}.get_promotion_link", new=AsyncMock(return_value=link)),
            patch(f"{SERVICE}.get_app", new=AsyncMock(return_value=app)),
        ):
            return asyncio.run(update_promotion_link(session, 5, body))

    def test_only_given_fields_change(self) -> None:
        """只改传了的字段，没传的保持原值；换剧场回填剧场名。"""
        link = make_link()
        app = TheaterApp(name="番茄剧场")
        body = PromotionLinkUpdate(theater_app_id=3, is_enabled=False, publish_time="2026-09-21 08:00:00")
        item = self._run(body, link, app)
        self.assertEqual((link.theater_app_id, link.is_enabled), (3, False))
        self.assertEqual(link.publish_time, datetime(2026, 9, 21, 8, tzinfo=BEIJING))
        self.assertEqual((link.promotion_url, link.recharge_template_name), ("https://x/1", "中额"))
        self.assertEqual((item["theater_app_name"], item["book_name"]), ("番茄剧场", "甲剧"))

    def test_missing_link_or_app_is_404(self) -> None:
        """推广链不存在或换到不存在的剧场都是 404。"""
        with self.assertRaises(ApiError) as caught:
            self._run(PromotionLinkUpdate(is_enabled=False), None, None)
        self.assertEqual(caught.exception.message, "推广链不存在")
        with self.assertRaises(ApiError) as caught:
            self._run(PromotionLinkUpdate(theater_app_id=99), make_link(), None)
        self.assertEqual(caught.exception.message, "剧场不存在")


if __name__ == "__main__":
    unittest.main()
