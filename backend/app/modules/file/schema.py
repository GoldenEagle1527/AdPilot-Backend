"""文件上传出参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileUploadData(BaseModel):
    """一次上传的结果。url 可直接交给只收地址的业务接口。"""

    url: str = Field(description="公网访问地址")
    key: str = Field(description="对象键")
    original_name: str = Field(description="原始文件名")
    size: int = Field(description="字节数")
    content_type: str = Field(description="内容类型")
