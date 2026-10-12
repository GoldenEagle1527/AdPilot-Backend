"""免费和付费漫剧端原生机器人 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.standard_robot.schema import RobotDeleted, RobotItem, RobotQuery, RobotSwitchWrite, RobotWrite
from app.modules.standard_robot.service import (
    create_robot_rule,
    delete_robot_rule,
    list_robot_rules,
    set_robot_enabled,
    update_robot_rule,
)
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/standard-native-robots", tags=["standard-native-robot"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


def _user_id(principal: dict[str, Any]) -> int:
    """当前登录用户。"""
    return int(principal["id"])


@router.get("/free", response_model=Envelope[PageData[RobotItem]], summary="分页查询免费漫剧端原生机器人")
async def get_free_robots(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[RobotQuery, Query()],
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """只列当前投手的免费规则。不跑机器人。"""
    return success(await list_robot_rules(session, query, _user_id(principal), "IAA"))


@router.post("/free", response_model=Envelope[RobotItem], summary="新增免费漫剧端原生机器人")
async def post_free_robot(
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """免费机器人使用免费端原生模板，执行留在当前投手。"""
    return success(await create_robot_rule(session, body, _user_id(principal), "IAA"))


@router.put("/free/{rule_id}", response_model=Envelope[RobotItem], summary="保存免费漫剧端原生机器人")
async def put_free_robot(
    rule_id: int,
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """整表保存自己的免费规则。不到点执行。"""
    return success(await update_robot_rule(session, rule_id, body, _user_id(principal), "IAA"))


@router.delete("/free/{rule_id}", response_model=Envelope[RobotDeleted], summary="删除免费漫剧端原生机器人")
async def remove_free_robot(
    rule_id: int,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """软删自己的免费规则。"""
    return success(await delete_robot_rule(session, rule_id, _user_id(principal), "IAA"))


@router.patch("/free/{rule_id}/switch", response_model=Envelope[RobotItem], summary="开关免费漫剧端原生机器人")
async def patch_free_robot_switch(
    rule_id: int,
    body: RobotSwitchWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("76"))],
) -> dict[str, Any]:
    """只改开关。关掉后到点循环跳过，这里不提交投放。"""
    return success(await set_robot_enabled(session, rule_id, body.is_enabled, _user_id(principal), "IAA"))


@router.get("/paid", response_model=Envelope[PageData[RobotItem]], summary="分页查询付费漫剧端原生机器人")
async def get_paid_robots(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[RobotQuery, Query()],
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """只列当前投手的付费规则。不跑机器人。"""
    return success(await list_robot_rules(session, query, _user_id(principal), "IAP"))


@router.post("/paid", response_model=Envelope[RobotItem], summary="新增付费漫剧端原生机器人")
async def post_paid_robot(
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """付费机器人使用付费端原生模板，执行留在当前投手。"""
    return success(await create_robot_rule(session, body, _user_id(principal), "IAP"))


@router.put("/paid/{rule_id}", response_model=Envelope[RobotItem], summary="保存付费漫剧端原生机器人")
async def put_paid_robot(
    rule_id: int,
    body: RobotWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """整表保存自己的付费规则。不到点执行。"""
    return success(await update_robot_rule(session, rule_id, body, _user_id(principal), "IAP"))


@router.delete("/paid/{rule_id}", response_model=Envelope[RobotDeleted], summary="删除付费漫剧端原生机器人")
async def remove_paid_robot(
    rule_id: int,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """软删自己的付费规则。"""
    return success(await delete_robot_rule(session, rule_id, _user_id(principal), "IAP"))


@router.patch("/paid/{rule_id}/switch", response_model=Envelope[RobotItem], summary="开关付费漫剧端原生机器人")
async def patch_paid_robot_switch(
    rule_id: int,
    body: RobotSwitchWrite,
    session: SessionDep,
    principal: PrincipalDep,
    _menu: Annotated[None, Depends(require_menu("77"))],
) -> dict[str, Any]:
    """只改开关。关掉后到点循环跳过，这里不提交投放。"""
    return success(await set_robot_enabled(session, rule_id, body.is_enabled, _user_id(principal), "IAP"))
