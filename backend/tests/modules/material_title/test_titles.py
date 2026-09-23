"""标题的入参约束、只看自己的过滤、批量新增与改标题。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.material_title.model import MaterialTitle
from app.modules.material_title.schema import TitleBatchCreate, TitleQuery, TitleUpdate
from app.modules.material_title.service import (
    batch_create_titles,
    title_filters,
    to_item,
    update_title,
)


class FakeResult:
    """假 execute 结果，按预置行回答 all / scalar_one_or_none / scalar_one。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        """原样返回预置行。"""
        return self._rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None


class FakeSession:
    """假会话：execute 按顺序吐预置结果，记录 add_all 和 commit。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        return FakeResult(self.results.pop(0) if self.results else [])

    def add_all(self, rows: list[Any]) -> None:
        """记下待插入行。"""
        self.added.extend(rows)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1


def make_row(**kwargs: Any) -> MaterialTitle:
    """造一条内存里的标题行，不进库。"""
    row = MaterialTitle(
        title=kwargs.get("title", "甲"),
        category=kwargs.get("category", "common"),
        uploader_id=kwargs.get("uploader_id", 7),
    )
    row.id = kwargs.get("id", 1)
    row.created_date = kwargs.get("created_date", datetime(2026, 9, 22, 19, 0, tzinfo=BEIJING))
    return row


class RequestTests(unittest.TestCase):
    def test_titles_are_stripped(self) -> None:
        """标题去首尾空白后入库。"""
        body = TitleBatchCreate(titles=[" 甲 ", "乙"], category="paid")
        self.assertEqual(body.titles, ["甲", "乙"])

    def test_duplicated_titles_are_rejected(self) -> None:
        """同一次提交里重名直接拒绝，去空白后相同也算重名。"""
        with self.assertRaises(ValidationError):
            TitleBatchCreate(titles=[" 甲 ", "甲"], category="paid")

    def test_bad_input_is_rejected(self) -> None:
        """空标题、空列表、未知分类都在进业务前被拒。"""
        with self.assertRaises(ValidationError):
            TitleBatchCreate(titles=["  "], category="paid")
        with self.assertRaises(ValidationError):
            TitleBatchCreate(titles=[], category="paid")
        with self.assertRaises(ValidationError):
            TitleBatchCreate(titles=["甲"], category="免费")

    def test_update_only_takes_title_and_category(self) -> None:
        """改标题只收标题名和分类，塞别的字段被拒。"""
        body = TitleUpdate(title=" 甲 ", category="paid")
        self.assertEqual(body.title, "甲")
        with self.assertRaises(ValidationError):
            TitleUpdate(title="甲", category="paid", uploader_id=9)


class FilterTests(unittest.TestCase):
    def _sql(self, query: TitleQuery, uploader_id: int) -> str:
        """把过滤条件编译成带字面量的 SQL 串，便于断言。"""
        return " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True}))
            for item in title_filters(query, uploader_id)
        )

    def test_always_limited_to_self(self) -> None:
        """不传任何筛选时，仍恒定只查自己未删除的标题。"""
        sql = self._sql(TitleQuery(), 7)
        self.assertIn("uploader_id = 7", sql)
        self.assertIn("is_deleted = 0", sql)
        self.assertNotIn("category =", sql)

    def test_category_and_title_are_applied(self) -> None:
        """分类精确匹配，标题名走模糊，通配符被转义。"""
        sql = self._sql(TitleQuery(category="paid", title=" 50%_甲 "), 7)
        self.assertIn("category = 'paid'", sql)
        self.assertIn("50\\%\\_甲", sql)


class BatchCreateTests(unittest.TestCase):
    def test_new_titles_are_inserted_in_one_go(self) -> None:
        """没有重名时整批插入，上传者写当前用户。"""
        session = FakeSession([[]])
        body = TitleBatchCreate(titles=["甲", "乙"], category="common")
        result = asyncio.run(batch_create_titles(session, body, 7))
        self.assertEqual(result, {"created": 2})
        self.assertEqual([row.title for row in session.added], ["甲", "乙"])
        self.assertEqual(session.added[0].uploader_id, 7)
        self.assertEqual(session.commits, 1)

    def test_existing_title_rejects_whole_batch(self) -> None:
        """自己同分类下已存在一条就整批 409，不写不提交。"""
        session = FakeSession([[("甲",)]])
        body = TitleBatchCreate(titles=["甲", "乙"], category="common")
        with self.assertRaises(ApiError) as caught:
            asyncio.run(batch_create_titles(session, body, 7))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("甲", caught.exception.message)
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 0)


class UpdateTests(unittest.TestCase):
    def test_other_uploader_row_is_not_found(self) -> None:
        """查不到自己名下那条就是 404，不提交。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(update_title(session, 1, TitleUpdate(title="甲", category="paid"), 7))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_rename_into_existing_title_is_rejected(self) -> None:
        """改成自己同分类下已有的标题名，409 且不落库。"""
        session = FakeSession([[make_row()], [("乙",)]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(update_title(session, 1, TitleUpdate(title="乙", category="common"), 7))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(session.commits, 0)

    def test_title_and_category_are_written(self) -> None:
        """标题名和分类都改到行上，提交一次，返回项带昵称。"""
        row = make_row()
        session = FakeSession([[row], [], [(7, "程浩2")]])
        result = asyncio.run(
            update_title(session, 1, TitleUpdate(title="乙", category="paid"), 7)
        )
        self.assertEqual(row.title, "乙")
        self.assertEqual(row.category, "paid")
        self.assertEqual(session.commits, 1)
        self.assertEqual(result["uploader_nickname"], "程浩2")
        self.assertEqual(result["id"], "1")


class ItemTests(unittest.TestCase):
    def test_item_shape(self) -> None:
        """出参 id 与 uploader_id 是十进制字符串，上传时间带 +08:00。"""
        item = to_item(make_row(), "程浩2")
        self.assertEqual(item["id"], "1")
        self.assertEqual(item["uploader_id"], "7")
        self.assertEqual(item["created_at"], "2026-09-22T19:00:00+08:00")
