"""视频素材列表的可见范围和筛选条件。"""

from __future__ import annotations

import unittest

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.modules.material_video.model import MaterialVideo, MaterialVideoTag
from app.modules.material_video.schema import TagQuery, VideoQuery
from app.modules.material_video.service import like_text, tag_filters, video_filters


def compiled(query: VideoQuery, user_id: int = 5) -> str:
    """把筛选条件编译成 PostgreSQL 语句，方便断言列和匹配方式。"""
    statement = select(MaterialVideo.id).where(*video_filters(query, user_id))
    return str(statement.compile(dialect=postgresql.dialect()))


class VideoFilterTests(unittest.TestCase):
    def test_like_escapes_wildcards(self) -> None:
        """名称里的 % 和 _ 按字面量搜，不当通配符。"""
        self.assertEqual(like_text(" a_b% "), r"%a\_b\%%")

    def test_default_is_visible_set(self) -> None:
        """不传归属时仍限制为公有、自己创建、或私有且分配给自己。"""
        sql = compiled(VideoQuery())
        self.assertIn("material_videos.ownership", sql)
        self.assertIn("material_videos.uploader_id", sql)
        self.assertIn("material_video_pitchers", sql)
        self.assertNotIn("ILIKE", sql)

    def test_filters_are_applied(self) -> None:
        """标签 id 精确，名称和文件名模糊，id、短剧、投手、上传者、归属按选中值。"""
        sql = compiled(
            VideoQuery(
                tag_id=4,
                name="甲",
                id=9,
                series_id=3,
                pitcher_id=7,
                uploader_id=8,
                file_name="海报",
                ownership="private",
            )
        )
        self.assertIn("material_videos.tag_id", sql)
        self.assertIn("material_videos.name", sql)
        self.assertIn("ILIKE", sql)
        self.assertIn("material_videos.file_urls", sql)
        self.assertIn("material_videos.series_id", sql)
        self.assertGreaterEqual(sql.count("material_video_pitchers.user_id"), 2)

    def test_tag_dropdown_is_fuzzy_and_visible(self) -> None:
        """标签下拉按名称模糊，并且只挂在当前用户能看见的素材上。"""
        statement = select(MaterialVideoTag.id).where(*tag_filters(TagQuery(name="甲_剧"), 5))
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("material_video_tags.name", sql)
        self.assertIn("ILIKE", sql)
        self.assertIn("material_videos.tag_id", sql)
        self.assertIn("material_videos.ownership", sql)
