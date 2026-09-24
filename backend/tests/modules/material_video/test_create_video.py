"""视频素材的入参约束、名称与标签拼接、短剧和投手的存在性校验。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.material_video.schema import VideoCreate
from app.modules.material_video.service import create_video


class FakeResult:
    """假 execute 结果，按预置行回答 all。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        """原样返回预置行。"""
        return self._rows


class FakeSession:
    """假会话：execute 按顺序吐预置结果，add 时补一个主键，记录提交次数。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        return FakeResult(self.results.pop(0) if self.results else [])

    def add(self, row: Any) -> None:
        """记下待插入行，并补上库里会回填的主键和创建时间。"""
        row.id = 1
        row.created_date = datetime(2026, 9, 23, 14, 30, tzinfo=BEIJING)
        self.added.append(row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1


def make_body(**kwargs: Any) -> VideoCreate:
    """造一份合法的添加入参，按需覆盖字段。"""
    return VideoCreate(
        **{
            "name": "甲",
            "material_type": "vertical_video",
            "file_urls": ["https://cdn.example.com/a.mp4"],
            "series_id": 3,
            "ownership": "public",
            "pitcher_ids": [7],
            **kwargs,
        }
    )


class RequestTests(unittest.TestCase):
    def test_platform_defaults_to_tomato(self) -> None:
        """不传平台默认番茄，传别的平台被拒。"""
        self.assertEqual(make_body().platform, "tomato")
        with self.assertRaises(ValidationError):
            make_body(platform="kuaishou")

    def test_duplicate_pitchers_are_rejected(self) -> None:
        """投手重复直接拒绝，不去重；空列表同样被拒。"""
        with self.assertRaises(ValidationError):
            make_body(pitcher_ids=[7, 9, 7])
        with self.assertRaises(ValidationError):
            make_body(pitcher_ids=[])

    def test_bad_input_is_rejected(self) -> None:
        """非 http 链接、未知素材类型、空文件数组、多传字段都在进业务前被拒。"""
        with self.assertRaises(ValidationError):
            make_body(file_urls=["ftp://cdn.example.com/a.mp4"])
        with self.assertRaises(ValidationError):
            make_body(material_type="gif")
        with self.assertRaises(ValidationError):
            make_body(file_urls=[])
        with self.assertRaises(ValidationError):
            make_body(uploader_id=9)


class CreateTests(unittest.TestCase):
    def test_name_and_tag_are_generated(self) -> None:
        """名称拼当日日期、标签拼短剧名加月日，上传者取当前用户，提交一次。"""
        session = FakeSession([[(3, "甲剧")], [(7, "投手甲"), (5, "上传者")]])
        result = asyncio.run(create_video(session, make_body(), 5))
        today = datetime.now(BEIJING)
        self.assertEqual(result["name"], f"甲_{today:%Y%m%d}")
        self.assertEqual(result["tag"], f"甲剧{today:%m%d}")
        self.assertEqual(result["book_name"], "甲剧")
        self.assertEqual(result["series_id"], "3")
        self.assertEqual(result["uploader_id"], "5")
        self.assertEqual(result["uploader_nickname"], "上传者")
        self.assertEqual(result["pitchers"], [{"id": "7", "nickname": "投手甲"}])
        self.assertEqual(session.added[0].uploader_id, 5)
        self.assertEqual(session.commits, 1)

    def test_unknown_series_is_rejected(self) -> None:
        """短剧查不到就是 404，不写不提交。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_video(session, make_body(), 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_unknown_pitcher_is_rejected(self) -> None:
        """有投手查不到就是 404，且把缺的 id 报出来，不写不提交。"""
        session = FakeSession([[(3, "甲剧")], [(7, "投手甲"), (5, "上传者")]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_video(session, make_body(pitcher_ids=[7, 9]), 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertIn("9", caught.exception.message)
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 0)

    def test_deleted_uploader_is_rejected(self) -> None:
        """登录用户已被删（Token 还在）时是 404，不落一条昵称为空的脏数据。"""
        session = FakeSession([[(3, "甲剧")], [(7, "投手甲")]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_video(session, make_body(), 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertIn("5", caught.exception.message)
        self.assertEqual(session.commits, 0)
