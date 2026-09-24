"""视频素材的入参和出参。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.material_video.model import MaterialType, Ownership, Platform

FileUrl = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=1024, pattern=r"^https?://"
    ),
]
# 名称留出 _YYYYMMDD 后缀的 9 个字符，拼完不超列宽 512
VideoName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=480)]


class VideoCreate(BaseModel):
    """添加视频素材入参。名称后缀和素材标签由后端按当日日期生成，不收入参。"""

    model_config = ConfigDict(extra="forbid")

    name: VideoName = Field(description="素材名称，落库时后缀拼当日日期，如 甲 存成 甲_20260923")
    material_type: MaterialType = Field(
        description="素材类型：vertical_video 竖版视频、horizontal_video 横版视频、"
        "horizontal_image 大图横图、small_image 小图、vertical_image 大图竖图"
    )
    file_urls: list[FileUrl] = Field(
        min_length=1, max_length=50, description="素材文件 url 数组，一次最多 50 个"
    )
    series_id: int = Field(gt=0, description="短剧，漫剧库 manhua-series 列表里的 id")
    platform: Platform = Field(Platform.TOMATO, description="投放平台，暂时只有 tomato 番茄")
    ownership: Ownership = Field(description="归属：public 公有、private 私有")
    pitcher_ids: list[int] = Field(
        min_length=1, max_length=50, description="投手归属用户 id，可多个，不得重复"
    )

    @field_validator("pitcher_ids")
    @classmethod
    def reject_duplicate_pitchers(cls, value: list[int]) -> list[int]:
        """同一次提交里不许重复投手，重复直接拒绝。"""
        if len(set(value)) != len(value):
            raise ValueError("投手不能重复")
        return value


class PitcherItem(BaseModel):
    """一个投手归属。"""

    id: str
    nickname: str


class VideoItem(BaseModel):
    """一条视频素材。名称和标签是后端拼好的结果，上传时间为北京时间 +08:00。"""

    id: str
    name: str
    material_type: str
    file_urls: list[str]
    series_id: str
    book_name: str
    platform: str
    tag: str
    ownership: str
    pitchers: list[PitcherItem]
    uploader_id: str
    uploader_nickname: str
    created_at: str
