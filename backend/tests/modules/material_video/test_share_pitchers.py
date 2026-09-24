"""一个接口里同时添加和取消共享，另一个接口里同时添加和取消投手。"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.modules.material_video.model import MaterialVideo, MaterialVideoPitcher, MaterialVideoShare
from app.modules.material_video.schema import PitcherChange, ShareChange
from app.modules.material_video.service import change_pitchers, change_shares


class FakeResult:
    """假 execute 结果，同时能回答 all、scalars 和 scalar_one_or_none。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        """原样返回预置行。"""
        return self._rows

    def scalars(self) -> FakeResult:
        """单列查询接着用这份结果。"""
        return self

    def scalar_one_or_none(self) -> Any:
        """有行就返回第一行，没有返回 None。"""
        return self._rows[0] if self._rows else None


class FakeSession:
    """假会话：execute 按顺序吐预置结果，记下插入并记录提交次数。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        return FakeResult(self.results.pop(0) if self.results else [])

    def add_all(self, rows: list[Any]) -> None:
        """一批插入。"""
        self.added.extend(rows)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1


def make_video(uploader_id: int = 5) -> MaterialVideo:
    """造一条未删除的视频。"""
    return MaterialVideo(
        id=8,
        name="甲_20260924",
        material_type="vertical_video",
        file_urls=["https://cdn.example.com/a.mp4"],
        series_id=3,
        platform="tomato",
        tag_id=1,
        ownership="private",
        uploader_id=uploader_id,
        is_deleted=0,
    )


class RequestTests(unittest.TestCase):
    def test_duplicate_users_are_rejected(self) -> None:
        """完整名单里的人不能重复。空数组表示清空，可以过。"""
        with self.assertRaises(ValidationError):
            ShareChange(user_ids=[7, 7])
        self.assertEqual(PitcherChange(user_ids=[]).user_ids, [])


class PitcherTests(unittest.TestCase):
    def test_uploader_assigns_pitchers(self) -> None:
        """上传者把素材分给投手，写入归属行，操作人是他自己。"""
        session = FakeSession([[make_video()], [], [(7, "投手甲")]])
        result = asyncio.run(change_pitchers(session, 8, PitcherChange(user_ids=[7]), 5))
        self.assertEqual(result["added"], [{"id": "7", "nickname": "投手甲"}])
        self.assertEqual(result["removed"], [])
        row = session.added[0]
        self.assertIsInstance(row, MaterialVideoPitcher)
        self.assertEqual(row.operator_id, 5)
        self.assertEqual(row.user_id, 7)
        self.assertEqual(session.commits, 1)

    def test_already_assigned_by_same_operator_is_skipped(self) -> None:
        """这个人已经分过的投手不再插一行。"""
        kept = MaterialVideoPitcher(video_id=8, operator_id=5, user_id=7, is_deleted=0)
        session = FakeSession([[make_video()], [kept], [(7, "投手甲")]])
        result = asyncio.run(change_pitchers(session, 8, PitcherChange(user_ids=[7]), 5))
        self.assertEqual(result["added"], [])
        self.assertEqual(session.added, [])
        self.assertEqual(kept.is_deleted, 0)

    def test_share_user_can_assign_and_remove(self) -> None:
        """仍在共享里的人提交自己的完整名单：名单里的新人加上，不在名单里的旧投手取消。"""
        share = MaterialVideoShare(id=1, video_id=8, user_id=9, is_deleted=0)
        old = MaterialVideoPitcher(video_id=8, operator_id=9, user_id=3, is_deleted=0)
        session = FakeSession([[make_video()], [share], [old], [(7, "投手甲"), (3, "投手乙")]])
        result = asyncio.run(change_pitchers(session, 8, PitcherChange(user_ids=[7]), 9))
        self.assertEqual(result["added"], [{"id": "7", "nickname": "投手甲"}])
        self.assertEqual(result["removed"], [{"id": "3", "nickname": "投手乙"}])
        self.assertEqual(session.added[0].operator_id, 9)
        self.assertEqual(old.is_deleted, 1)

    def test_outsider_is_rejected(self) -> None:
        """不是上传者、也不在共享里，按素材不存在拒绝，不写不提交。"""
        session = FakeSession([[make_video()], []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(change_pitchers(session, 8, PitcherChange(user_ids=[7]), 9))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)


class ShareTests(unittest.TestCase):
    def test_removing_share_keeps_pitchers(self) -> None:
        """提交的完整共享名单里没有的人被取消。取消只软删共享行，已有投手归属仍是未删。"""
        share = MaterialVideoShare(id=3, video_id=8, user_id=9, is_deleted=0)
        pitcher = MaterialVideoPitcher(id=4, video_id=8, operator_id=9, user_id=7, is_deleted=0)
        session = FakeSession([[make_video()], [share], [(9, "共享人"), (6, "新人")]])
        result = asyncio.run(change_shares(session, 8, ShareChange(user_ids=[6]), 5))
        self.assertEqual(result["added"], [{"id": "6", "nickname": "新人"}])
        self.assertEqual(result["removed"], [{"id": "9", "nickname": "共享人"}])
        self.assertEqual(share.is_deleted, 1)
        self.assertEqual(pitcher.is_deleted, 0)
        self.assertEqual(session.added[0].user_id, 6)
        self.assertEqual(session.commits, 1)
