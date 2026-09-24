"""文件上传 HTTP。不在接口层做菜单鉴权，只认登录态。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import require_token
from app.core.envelope import Envelope, success
from app.modules.file.schema import FileUploadData
from app.modules.file.service import upload_file

router = APIRouter(prefix="/api/v1/files", tags=["file"])

PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


@router.post(
    "/upload",
    response_model=Envelope[FileUploadData],
    summary="上传单个文件",
)
async def post_upload(
    file: Annotated[UploadFile, File(description="文件本体")],
    principal: PrincipalDep,
) -> dict[str, Any]:
    """接收前端上传的文件，转存到 TOS，返回公网地址。"""
    return success(await upload_file(file, str(principal["id"])))
