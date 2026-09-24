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
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]


class VideoCreate(BaseModel):
    """添加视频素材入参。名称后缀由后端按当日日期生成，标签名由前端传入。"""

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
    tag: TagName = Field(description="标签名，原样落库，如 甲剧0923。同一文案共用一条标签")
    ownership: Ownership = Field(description="归属：public 公有、private 私有")
    pitcher_ids: list[int] = Field(
        max_length=50,
        description="分配的投手用户 id，可空，一次最多 50 个，不得重复。公有时不决定谁能看见",
    )

    @field_validator("pitcher_ids")
    @classmethod
    def reject_duplicate_pitchers(cls, value: list[int]) -> list[int]:
        """同一次提交里不许重复投手，重复直接拒绝。"""
        if len(set(value)) != len(value):
            raise ValueError("投手不能重复")
        return value


class VideoQuery(BaseModel):
    """视频素材列表查询。归属不传为公有和私有都查，仍受当前用户可见范围限制。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    tag_id: int | None = Field(None, gt=0, description="视频标签 id，下拉选中的那一条")
    name: str | None = Field(None, description="视频名称，模糊")
    id: int | None = Field(None, gt=0, description="视频 id，精确")
    series_id: int | None = Field(None, gt=0, description="短剧 id，下拉选中的那一条")
    pitcher_id: int | None = Field(None, gt=0, description="归属投手用户 id，下拉选中的那一条")
    uploader_id: int | None = Field(None, gt=0, description="上传者用户 id，下拉选中的那一条")
    file_name: str | None = Field(None, description="上传文件名，按素材文件地址模糊匹配")
    ownership: Ownership | None = Field(None, description="归属：public 公有、private 私有，不传为全部")


class TagQuery(BaseModel):
    """视频标签下拉。名称模糊，只列出当前用户能看见的素材用过的标签。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="标签名，模糊")


class TagItem(BaseModel):
    """一条视频标签。"""

    id: str
    name: str


class PitcherItem(BaseModel):
    """一个投手归属。"""

    id: str
    nickname: str


class VideoItem(BaseModel):
    """一条视频素材。名称是后端拼好日期后缀的结果，标签是前端传入的文案。"""

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
