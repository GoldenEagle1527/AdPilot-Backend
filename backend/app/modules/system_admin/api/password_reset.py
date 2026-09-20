from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.api.users import get_user
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.password import hash_password_async, load_default_password
from app.modules.system_admin.schemas.common import PasswordResetData

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]


@router.post("/users/{user_id}/password-reset", response_model=Envelope[PasswordResetData])
async def reset_user_password(
    user_id: str,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    password = await load_default_password(session)
    if not password:
        raise ApiError(500, "INTERNAL_ERROR", "缺少字典项 default_password（Q-PERM-5）")
    user.password_hash = await hash_password_async(password)
    await session.commit()
    return success({"reset": True, "password": password})
