"""免费和付费漫剧端原生机器人 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.modules.standard_robot.schema import RobotItem, RobotWrite
from app.modules.standard_robot.service import create_robot_rule
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/standard-native-robots", tags=["standard-native-robot"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


@router.post("/free", response_model=Envelope[RobotItem], summary="新增免费漫剧端原生机器人")
async def post_free_robot(
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """免费机器人使用免费端原生模板，执行留在当前投手。"""
    return success(await create_robot_rule(session, body, int(principal["id"]), "IAA"))


@router.post("/paid", response_model=Envelope[RobotItem], summary="新增付费漫剧端原生机器人")
async def post_paid_robot(
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """付费机器人使用付费端原生模板，执行留在当前投手。"""
    return success(await create_robot_rule(session, body, int(principal["id"]), "IAP"))
