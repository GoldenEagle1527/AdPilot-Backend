"""应用的入参约束、列表过滤、新增时的平台与重名校验、只改状态。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.theater.model import TheaterApp, TheaterPlatform
from app.modules.theater.schema import AppCreate, AppQuery, AppStatusUpdate
from app.modules.theater.service import app_filters, create_app, set_app_status

CREATED = datetime(2026, 9, 28, 12, 0, 0, 500000, tzinfo=BEIJING)


class FakeResult:
    """假 execute 结果，只回答 scalar_one_or_none。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None


class FakeSession:
    """假会话：execute 按顺序吐预置结果；refresh 模拟库里补 id 和时间。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        return FakeResult(self.results.pop(0) if self.results else [])

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """补上库里才有的 id 和时间。"""
        row.id = row.id or 5
        row.created_date = row.created_date or CREATED
        row.updated_date = CREATED


def make_platform(**kwargs: Any) -> TheaterPlatform:
    """造一条内存里的平台行，默认启用、只支持端原生。"""
    row = TheaterPlatform(
        name=kwargs.get("name", "番茄"),
        code="1011",
        sort_order=1,
        is_enabled=kwargs.get("is_enabled", True),
        supports_mini_program=False,
        supports_native=kwargs.get("supports_native", True),
    )
    row.id = kwargs.get("id", 1)
    return row


def make_app(**kwargs: Any) -> TheaterApp:
    """造一条内存里的应用行，挂在番茄平台下。"""
    row = TheaterApp(
        platform_id=kwargs.get("platform_id", 1),
        name=kwargs.get("name", "甲剧场"),
        theater_type="native",
        delivery_mode="IAA",
        style="manhua",
        ad_source="甲来源",
        is_valid=kwargs.get("is_valid", True),
    )
    row.id = 3
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def create_body(**kwargs: Any) -> AppCreate:
    """拼一份合法的新增入参，可覆盖任意字段。"""
    data = {
        "platform_id": 1,
        "name": " 甲剧场 ",
        "theater_type": "native",
        "delivery_mode": "IAP",
        "style": "manhua",
        "ad_source": " 甲来源 ",
    }
    data.update(kwargs)
    return AppCreate(**data)


class BodyTests(unittest.TestCase):
    def test_create_is_stripped(self) -> None:
        """名称和广告来源去首尾空白。"""
        body = create_body()
        self.assertEqual(body.name, "甲剧场")
        self.assertEqual(body.ad_source, "甲来源")

    def test_mini_program_is_accepted(self) -> None:
        """入参不拦小程序，能不能用交给平台的小程序开关。"""
        self.assertEqual(create_body(theater_type="mini_program").theater_type, "mini_program")

    def test_mode_is_single_choice(self) -> None:
        """投放模式只收一个值，传数组或不认识的值都拒。"""
        for mode in (["IAA", "IAP"], ["IAA"], "CPS"):
            with self.assertRaises(ValidationError):
                create_body(delivery_mode=mode)

    def test_create_takes_no_status(self) -> None:
        """新增不收状态，塞进来直接拒。"""
        with self.assertRaises(ValidationError):
            create_body(is_valid=False)


class FilterTests(unittest.TestCase):
    def _sql(self, query: AppQuery) -> str:
        """把过滤条件编译成带字面量的 SQL 串，便于断言。"""
        return " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True})) for item in app_filters(query)
        )

    def test_no_filter_only_hides_deleted(self) -> None:
        """不传筛选只排除软删。"""
        self.assertEqual(self._sql(AppQuery()), "theater_apps.is_deleted = 0")

    def test_all_filters_are_applied(self) -> None:
        """五个筛选都精确匹配。"""
        sql = self._sql(
            AppQuery(platform_id=22, theater_type="native", delivery_mode="IAP", style="live_action", is_valid=False)
        )
        self.assertIn("theater_apps.platform_id = 22", sql)
        self.assertIn("theater_apps.theater_type = 'native'", sql)
        self.assertIn("theater_apps.delivery_mode = 'IAP'", sql)
        self.assertIn("theater_apps.style = 'live_action'", sql)
        self.assertIn("theater_apps.is_valid = false", sql)


class CreateTests(unittest.TestCase):
    def test_missing_platform_is_not_found(self) -> None:
        """平台不存在 404，不写。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_app(session, create_body()))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.added, [])

    def test_disabled_or_unsupported_platform_is_rejected(self) -> None:
        """平台禁用、或没勾端原生，都 400 不写。"""
        for platform in (make_platform(is_enabled=False), make_platform(supports_native=False)):
            session = FakeSession([[platform]])
            with self.assertRaises(ApiError) as caught:
                asyncio.run(create_app(session, create_body()))
            self.assertEqual(caught.exception.status_code, 400)
            self.assertEqual(session.commits, 0)

    def test_taken_name_is_rejected(self) -> None:
        """同平台已有同名应用 409 不写。"""
        session = FakeSession([[make_platform()], [9]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_app(session, create_body()))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(session.added, [])

    def test_new_app_is_valid_and_carries_platform_name(self) -> None:
        """新增一律有效，出参带平台名称，时间截到秒。"""
        session = FakeSession([[make_platform()], []])
        item = asyncio.run(create_app(session, create_body()))
        self.assertTrue(session.added[0].is_valid)
        self.assertEqual(session.commits, 1)
        self.assertEqual(item["platform_name"], "番茄")
        self.assertEqual(item["delivery_mode"], "IAP")
        self.assertEqual(item["id"], "5")
        self.assertEqual(item["created_at"], "2026-09-28T12:00:00+08:00")


class StatusTests(unittest.TestCase):
    def test_only_status_is_accepted(self) -> None:
        """只收 is_valid 且必填，塞别的字段或不传都拒。"""
        with self.assertRaises(ValidationError):
            AppStatusUpdate()
        with self.assertRaises(ValidationError):
            AppStatusUpdate(is_valid=False, name="乙剧场")

    def test_missing_app_is_not_found(self) -> None:
        """应用不存在 404，不提交。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(set_app_status(session, 3, AppStatusUpdate(is_valid=False)))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_status_is_written_even_if_platform_disabled(self) -> None:
        """只改状态不验平台：平台已禁用也能改，其它字段不动。"""
        row = make_app()
        session = FakeSession([[row], [make_platform(is_enabled=False)]])
        item = asyncio.run(set_app_status(session, 3, AppStatusUpdate(is_valid=False)))
        self.assertFalse(row.is_valid)
        self.assertEqual(row.name, "甲剧场")
        self.assertEqual(session.commits, 1)
        self.assertFalse(item["is_valid"])
        self.assertEqual(item["platform_name"], "番茄")


if __name__ == "__main__":
    unittest.main()
