"""素材标题的入参和出参。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.material_title.model import TitleCategory

TitleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class TitleBatchCreate(BaseModel):
    """批量添加标题入参：一批标题名共用一个分类。"""

    model_config = ConfigDict(extra="forbid")

    titles: list[TitleName] = Field(
        min_length=1, max_length=200, description="标题名，去首尾空白，一次最多 200 条"
    )
    category: TitleCategory = Field(description="标题分类：paid 付费标题、common 通用标题")

    @field_validator("titles")
    @classmethod
    def reject_duplicate_titles(cls, value: list[str]) -> list[str]:
        """同一次提交里不许重名（去空白后比），重复直接拒绝。"""
        if len(set(value)) != len(value):
            raise ValueError("标题名不能重复")
        return value


class TitleBatchCreated(BaseModel):
    """批量添加结果。整批成功才返回，条数等于请求里的标题数。"""

    created: int


class TitleQuery(BaseModel):
    """标题列表查询。只看当前登录用户自己上传的，分类不传为全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    category: TitleCategory | None = Field(
        None, description="标题分类：paid 付费标题、common 通用标题，不传为全部"
    )
    title: str | None = Field(None, description="标题名称，模糊")


class TitleItem(BaseModel):
    """一条标题。上传者即创建人，上传时间为北京时间 +08:00。"""

    id: str
    title: str
    category: str
    uploader_id: str
    uploader_nickname: str
    created_at: str


class TitleIdsBody(BaseModel):
    """一批标题 id。不得重复。"""

    model_config = ConfigDict(extra="forbid")

    title_ids: list[int] = Field(min_length=1, description="要删除的标题 id。放一个是单删，放多个是批量删，不得重复")

    @field_validator("title_ids")
    @classmethod
    def reject_duplicate_titles(cls, value: list[int]) -> list[int]:
        """同一次提交里不许重复标题。"""
        if len(set(value)) != len(value):
            raise ValueError("标题不能重复")
        return value


class TitlesDeleted(BaseModel):
    """删除标题的出参。一条和多条都用 ids。"""

    ids: list[str]
    deleted: bool


class TitleUpdate(BaseModel):
    """改标题入参：只准改标题名和分类。"""

    model_config = ConfigDict(extra="forbid")

    title: TitleName
    category: TitleCategory
