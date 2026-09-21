"""管理员重置用户密码。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.password import hash_password_async
from app.modules.system_admin.schemas.common import PasswordResetData
from app.modules.system_admin.schemas.users import ResetPasswordRequest

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


@router.post(
    "/users/{user_id}/password-reset",
    response_model=Envelope[PasswordResetData],
    summary="管理员重置用户密码",
)
async def reset_user_password(
    user_id: str,
    body: ResetPasswordRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """写入新密码；两次输入须一致。"""
    if body.password != body.password_confirm:
        raise ApiError(422, "VALIDATION_ERROR", "两次输入的密码不一致")
    user = await get_user(session, user_id)
    user.password_hash = await hash_password_async(body.password)
    await session.commit()
    return success({"reset": True})
