"""软删视频素材：只删自己上传的，别人的当不存在。"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from app.core.envelope import ApiError
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.service import delete_video


class FakeResult:
    """假 execute 结果，按预置行回答 scalar_one_or_none。"""

    def __init__(self, row: MaterialVideo | None) -> None:
        self._row = row

    def scalar_one_or_none(self) -> MaterialVideo | None:
        """原样返回预置行。"""
        return self._row


class FakeSession:
    """假会话：execute 吐预置行，记录提交次数。"""

    def __init__(self, row: MaterialVideo | None) -> None:
        self.row = row
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，返回预置行。"""
        return FakeResult(self.row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1


def make_video() -> MaterialVideo:
    """造一条当前用户上传的未删除视频。"""
    return MaterialVideo(
        id=8,
        name="甲_20260924",
        material_type="vertical_video",
        file_urls=["https://cdn.example.com/a.mp4"],
        series_id=3,
        platform="tomato",
        tag_id=1,
        ownership="public",
        uploader_id=5,
        is_deleted=0,
    )


class DeleteTests(unittest.TestCase):
    def test_own_video_is_soft_deleted(self) -> None:
        """自己的视频标成已删并提交一次。"""
        row = make_video()
        session = FakeSession(row)
        result = asyncio.run(delete_video(session, 8, 5))
        self.assertEqual(result, {"id": "8", "deleted": True})
        self.assertEqual(row.is_deleted, 1)
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(session.commits, 1)

    def test_missing_video_is_rejected(self) -> None:
        """查不到、已删或不是自己的，都是 404，不提交。"""
        session = FakeSession(None)
        with self.assertRaises(ApiError) as caught:
            asyncio.run(delete_video(session, 8, 5))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "视频素材不存在")
        self.assertEqual(session.commits, 0)
