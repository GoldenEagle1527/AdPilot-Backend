"""平台列表的过滤、改开关的入参约束与只改传了的字段。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.theater.model import TheaterPlatform
from app.modules.theater.schema import PlatformQuery, PlatformUpdate
from app.modules.theater.service import platform_filters, platform_item, update_platform


class FakeResult:
    """假 execute 结果，只回答 scalar_one_or_none。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None


class FakeSession:
    """假会话：execute 按顺序吐预置结果，记录 commit 和 refresh。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.commits = 0
        self.refreshed: list[Any] = []

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        return FakeResult(self.results.pop(0) if self.results else [])

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """记下被重读的行。"""
        self.refreshed.append(row)


def make_platform() -> TheaterPlatform:
    """造一条内存里的番茄平台行，不进库。"""
    row = TheaterPlatform(
        name="番茄",
        code="1011",
        sort_order=1,
        is_enabled=True,
        supports_mini_program=False,
        supports_native=True,
    )
    row.id = 1
    row.created_date = datetime(2026, 9, 28, 12, 0, 0, 123456, tzinfo=BEIJING)
    row.updated_date = datetime(2026, 9, 28, 12, 30, 5, tzinfo=BEIJING)
    return row


class FilterTests(unittest.TestCase):
    def _sql(self, query: PlatformQuery) -> str:
        """把过滤条件编译成带字面量的 SQL 串，便于断言。"""
        return " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True})) for item in platform_filters(query)
        )

    def test_no_filter_only_hides_deleted(self) -> None:
        """不传筛选只排除软删。"""
        self.assertEqual(self._sql(PlatformQuery()), "theater_platforms.is_deleted = 0")

    def test_name_and_enabled_are_applied(self) -> None:
        """平台名称去空白后模糊匹配、通配符被转义，启用状态禁用也能筛。"""
        sql = self._sql(PlatformQuery(name=" 50%_鸥 ", is_enabled=False))
        self.assertIn("50\\%\\_鸥", sql)
        self.assertIn("theater_platforms.is_enabled = false", sql)

    def test_blank_name_is_ignored(self) -> None:
        """名称只有空白当没传。"""
        self.assertEqual(self._sql(PlatformQuery(name="  ")), "theater_platforms.is_deleted = 0")


class UpdateBodyTests(unittest.TestCase):
    def test_empty_or_all_null_is_rejected(self) -> None:
        """一个字段不传、或全传 null，都算没改。"""
        with self.assertRaises(ValidationError):
            PlatformUpdate()
        with self.assertRaises(ValidationError):
            PlatformUpdate(is_enabled=None)

    def test_name_and_code_cannot_be_changed(self) -> None:
        """平台名称和平台码写死，塞进来直接拒。"""
        with self.assertRaises(ValidationError):
            PlatformUpdate(is_enabled=False, name="改名")
        with self.assertRaises(ValidationError):
            PlatformUpdate(is_enabled=False, code="9999")


class UpdateTests(unittest.TestCase):
    def test_missing_platform_is_not_found(self) -> None:
        """查不到平台 404，不提交。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(update_platform(session, 99, PlatformUpdate(is_enabled=False)))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_only_given_fields_are_written(self) -> None:
        """只改传了的开关，没传的保持原值；提交后重读一次。"""
        row = make_platform()
        session = FakeSession([[row]])
        result = asyncio.run(update_platform(session, 1, PlatformUpdate(is_enabled=False)))
        self.assertFalse(row.is_enabled)
        self.assertTrue(row.supports_native)
        self.assertEqual(session.commits, 1)
        self.assertEqual(session.refreshed, [row])
        self.assertFalse(result["is_enabled"])


class ItemTests(unittest.TestCase):
    def test_item_shape(self) -> None:
        """id 是十进制字符串，时间带 +08:00 且截到秒。"""
        item = platform_item(make_platform())
        self.assertEqual(item["id"], "1")
        self.assertEqual(item["code"], "1011")
        self.assertEqual(item["created_at"], "2026-09-28T12:00:00+08:00")
        self.assertEqual(item["updated_at"], "2026-09-28T12:30:05+08:00")


if __name__ == "__main__":
    unittest.main()
