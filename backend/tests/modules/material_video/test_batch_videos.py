"""批量删、批量共享、批量转公有、批量投手归属。对不上的整批不写。"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.modules.material_video.model import MaterialVideo, MaterialVideoPitcher, MaterialVideoShare
from app.modules.material_video.schema import BatchPitcherBody, BatchShareBody, VideoIdsBody
from app.modules.material_video.service import (
    batch_assign_pitchers,
    batch_delete_videos,
    batch_make_public,
    batch_share_videos,
)


class FakeResult:
    """假 execute 结果，同时能回答 all 和 scalars。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        """原样返回预置行。"""
        return self._rows

    def scalars(self) -> FakeResult:
        """单列查询接着用这份结果。"""
        return self


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


def make_video(video_id: int, uploader_id: int = 5) -> MaterialVideo:
    """造一条未删除的视频。"""
    return MaterialVideo(
        id=video_id,
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
    def test_empty_or_duplicate_ids_are_rejected(self) -> None:
        """空名单和重复 id 直接 422，共享人不设人数上限。"""
        with self.assertRaises(ValidationError):
            VideoIdsBody(video_ids=[])
        with self.assertRaises(ValidationError):
            BatchShareBody(video_ids=[8, 8], user_ids=[7])
        body = BatchShareBody(video_ids=[8], user_ids=list(range(1, 60)))
        self.assertEqual(len(body.user_ids), 59)
        with self.assertRaises(ValidationError):
            BatchPitcherBody(video_ids=[8], user_ids=list(range(1, 52)))


class DeleteTests(unittest.TestCase):
    def test_own_videos_are_soft_deleted(self) -> None:
        """自己的多条一起标成已删，只提交一次。"""
        first, second = make_video(8), make_video(9)
        session = FakeSession([[first, second]])
        result = asyncio.run(batch_delete_videos(session, VideoIdsBody(video_ids=[8, 9]), 5))
        self.assertEqual(result, {"ids": ["8", "9"], "deleted": True})
        self.assertEqual(first.is_deleted, 1)
        self.assertEqual(second.is_deleted, 1)
        self.assertEqual(session.commits, 1)

    def test_one_missing_rejects_the_batch(self) -> None:
        """有一条不是自己的，整批不删。"""
        kept = make_video(8)
        session = FakeSession([[kept]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(batch_delete_videos(session, VideoIdsBody(video_ids=[8, 9]), 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "视频素材不存在：9")
        self.assertEqual(kept.is_deleted, 0)
        self.assertEqual(session.commits, 0)


class ShareTests(unittest.TestCase):
    def test_adds_and_restores_without_removing_others(self) -> None:
        """没有的补上，取消过的恢复，已经共享的不动。"""
        restored = MaterialVideoShare(video_id=8, user_id=7, is_deleted=1)
        kept = MaterialVideoShare(video_id=9, user_id=7, is_deleted=0)
        session = FakeSession([[make_video(8), make_video(9)], [(7, "甲")], [restored, kept]])
        result = asyncio.run(
            batch_share_videos(session, BatchShareBody(video_ids=[8, 9], user_ids=[7]), 5)
        )
        self.assertEqual(result["ids"], ["8", "9"])
        self.assertEqual(result["user_ids"], ["7"])
        self.assertEqual(restored.is_deleted, 0)
        self.assertEqual(kept.is_deleted, 0)
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 1)


class PublicTests(unittest.TestCase):
    def test_own_videos_become_public(self) -> None:
        """自己的多条一次改成公有。"""
        row = make_video(8)
        session = FakeSession([[row]])
        result = asyncio.run(batch_make_public(session, VideoIdsBody(video_ids=[8]), 5))
        self.assertEqual(result, {"ids": ["8"], "ownership": "public"})
        self.assertEqual(row.ownership, "public")
        self.assertEqual(session.commits, 1)


class PitcherTests(unittest.TestCase):
    def test_share_user_adds_pitchers_on_each_video(self) -> None:
        """共享人把同一批投手加到多条素材上，操作人记他自己。"""
        mine = make_video(8, uploader_id=5)
        shared = make_video(9, uploader_id=4)
        old = MaterialVideoPitcher(video_id=8, operator_id=6, user_id=3, is_deleted=0)
        session = FakeSession([[mine, shared], [8, 9], [(7, "投手甲")], []])
        result = asyncio.run(
            batch_assign_pitchers(session, BatchPitcherBody(video_ids=[8, 9], user_ids=[7]), 6)
        )
        self.assertEqual(result["user_ids"], ["7"])
        self.assertEqual(len(session.added), 2)
        self.assertEqual({row.video_id for row in session.added}, {8, 9})
        self.assertTrue(all(row.operator_id == 6 and row.user_id == 7 for row in session.added))
        self.assertEqual(old.is_deleted, 0)
        self.assertEqual(session.commits, 1)

    def test_outsider_rejects_the_batch(self) -> None:
        """有一条既不是自己的、也没共享给自己，整批不写。"""
        session = FakeSession([[make_video(8), make_video(9, uploader_id=4)], [8]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                batch_assign_pitchers(session, BatchPitcherBody(video_ids=[8, 9], user_ids=[7]), 6)
            )
        self.assertEqual(caught.exception.message, "视频素材不存在：9")
        self.assertEqual(session.commits, 0)
        self.assertEqual(session.added, [])
