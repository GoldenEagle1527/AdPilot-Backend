"""视频素材的入参约束、名称与标签拼接、短剧和投手的存在性校验。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.material_video.model import MaterialVideo, MaterialVideoShare, MaterialVideoTag
from app.modules.material_video.schema import VideoCreate
from app.modules.material_video.service import create_video


class FakeResult:
    """假 execute 结果，按预置行回答 all。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        """原样返回预置行。"""
        return self._rows

    def scalars(self) -> FakeResult:
        """标签查询走 scalars().all()，这里原样接着用。"""
        return self


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
        row.id = len(self.added) + 1
        row.created_date = datetime(2026, 9, 23, 14, 30, tzinfo=BEIJING)
        self.added.append(row)

    def add_all(self, rows: list[Any]) -> None:
        """一批插入。"""
        for row in rows:
            self.add(row)

    async def flush(self) -> None:
        """主键已在 add 时补上。"""

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
            "tag": "甲剧0923",
            "ownership": "public",
            "share_user_ids": [7],
            **kwargs,
        }
    )


class RequestTests(unittest.TestCase):
    def test_platform_defaults_to_tomato(self) -> None:
        """不传平台默认番茄，传别的平台被拒。"""
        self.assertEqual(make_body().platform, "tomato")
        with self.assertRaises(ValidationError):
            make_body(platform="kuaishou")

    def test_duplicate_shares_are_rejected(self) -> None:
        """共享人重复直接拒绝，不去重。空列表可以。"""
        with self.assertRaises(ValidationError):
            make_body(share_user_ids=[7, 9, 7])
        self.assertEqual(make_body(share_user_ids=[]).share_user_ids, [])

    def test_bad_input_is_rejected(self) -> None:
        """非 http 链接、未知素材类型、空文件数组、空标签、多传字段都在进业务前被拒。"""
        with self.assertRaises(ValidationError):
            make_body(file_urls=["ftp://cdn.example.com/a.mp4"])
        with self.assertRaises(ValidationError):
            make_body(material_type="gif")
        with self.assertRaises(ValidationError):
            make_body(file_urls=[])
        with self.assertRaises(ValidationError):
            make_body(tag="  ")
        with self.assertRaises(ValidationError):
            make_body(uploader_id=9)


class CreateTests(unittest.TestCase):
    def test_name_and_tag_are_generated(self) -> None:
        """名称拼当日日期，标签用前端传入的文案，上传者取当前用户，提交一次。"""
        session = FakeSession([[(3, "甲剧")], [(7, "投手甲"), (5, "上传者")]])
        result = asyncio.run(create_video(session, make_body(), 5))
        today = datetime.now(BEIJING)
        self.assertEqual(result["name"], f"甲_{today:%Y%m%d}")
        self.assertEqual(result["tag"], "甲剧0923")
        self.assertEqual(result["book_name"], "甲剧")
        self.assertEqual(result["series_id"], "3")
        self.assertEqual(result["uploader_id"], "5")
        self.assertEqual(result["uploader_nickname"], "上传者")
        self.assertEqual(result["shares"], [{"id": "7", "nickname": "投手甲"}])
        self.assertEqual(result["pitchers"], [])
        tag_row, video_row, share_row = session.added
        self.assertIsInstance(tag_row, MaterialVideoTag)
        self.assertEqual(tag_row.name, "甲剧0923")
        self.assertIsInstance(video_row, MaterialVideo)
        self.assertEqual(video_row.uploader_id, 5)
        self.assertEqual(video_row.tag_id, tag_row.id)
        self.assertIsInstance(share_row, MaterialVideoShare)
        self.assertEqual(share_row.video_id, video_row.id)
        self.assertEqual(share_row.user_id, 7)
        self.assertEqual(session.commits, 1)

    def test_unknown_series_is_rejected(self) -> None:
        """短剧查不到就是 404，不写不提交。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_video(session, make_body(), 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_unknown_share_user_is_rejected(self) -> None:
        """有共享人查不到就是 404，且把缺的 id 报出来，不写不提交。"""
        session = FakeSession([[(3, "甲剧")], [(7, "投手甲"), (5, "上传者")]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_video(session, make_body(share_user_ids=[7, 9]), 5))
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

    def test_empty_shares_write_no_link_rows(self) -> None:
        """不共享时写标签和素材，不写共享行，投手为空。"""
        session = FakeSession([[(3, "甲剧")], [(5, "上传者")]])
        result = asyncio.run(create_video(session, make_body(share_user_ids=[]), 5))
        self.assertEqual(result["shares"], [])
        self.assertEqual(result["pitchers"], [])
        self.assertEqual(len(session.added), 2)
        self.assertIsInstance(session.added[0], MaterialVideoTag)
        self.assertIsInstance(session.added[1], MaterialVideo)
        self.assertEqual(session.commits, 1)
