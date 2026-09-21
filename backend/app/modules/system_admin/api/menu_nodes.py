from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.envelope import Envelope, success
from app.modules.system_admin.deps import MENU_ROLE_QUERY, MENU_ROLES, SessionDep, require_menu
from app.modules.system_admin.domain.models import MenuNode, Role, RoleMenu
from app.modules.system_admin.schemas.common import MenuTree

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_ROLES, MENU_ROLE_QUERY))]


def _sort_key(node: MenuNode) -> tuple[int, int | str]:
    try:
        return (0, int(node.id))
    except ValueError:
        return (1, node.id)


def _matches(node: MenuNode, business_domain: str | None, name: str | None) -> bool:
    if business_domain is not None and node.business_domain != business_domain:
        return False
    if name and name.lower() not in node.name.lower():
        return False
    return True


def _to_dict(
    node: MenuNode,
    children: list[dict[str, Any]],
    include_assigned_roles: bool,
    roles_by_menu: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": str(node.id),
        "name": node.name,
        "type": node.type,
        "parent_id": None if node.parent_id is None else str(node.parent_id),
        "business_domain": node.business_domain,
        "tenant_kind": node.tenant_kind,
        "children": children,
    }
    if include_assigned_roles:
        if node.type == "目录":
            item["assigned_roles"] = []
        else:
            item["assigned_roles"] = roles_by_menu.get(str(node.id), [])
    return item


@router.get("/menu-nodes", response_model=Envelope[MenuTree], response_model_exclude_none=True)
async def list_menu_nodes(
    session: SessionDep,
    _principal: PrincipalDep,
    business_domain: str | None = Query(default=None),
    name: str | None = Query(default=None),
    include_assigned_roles: bool = Query(default=False),
):
    nodes = list((await session.execute(select(MenuNode))).scalars().all())
    by_id = {n.id: n for n in nodes}

    filtered = {n.id for n in nodes if _matches(n, business_domain, name)}
    keep = set(filtered)
    for nid in filtered:
        current = by_id[nid].parent_id
        while current and current not in keep:
            keep.add(current)
            parent = by_id.get(current)
            current = parent.parent_id if parent else None

    roles_by_menu: dict[str, list[dict[str, str]]] = {}
    if include_assigned_roles:
        assign_rows = (
            await session.execute(
                select(RoleMenu.menu_id, Role.id, Role.name)
                .join(Role, Role.id == RoleMenu.role_id)
                .order_by(Role.id)
            )
        ).all()
        for menu_id, role_id, role_name in assign_rows:
            roles_by_menu.setdefault(str(menu_id), []).append({"id": str(role_id), "name": role_name})

    children_of: dict[str | None, list[MenuNode]] = {}
    for node in nodes:
        if node.id not in keep:
            continue
        parent_key = None if node.parent_id is None else str(node.parent_id)
        children_of.setdefault(parent_key, []).append(node)
    for siblings in children_of.values():
        siblings.sort(key=_sort_key)

    def build(parent_id: str | None) -> list[dict[str, Any]]:
        return [
            _to_dict(
                child,
                build(str(child.id)),
                include_assigned_roles,
                roles_by_menu,
            )
            for child in children_of.get(parent_id, [])
        ]

    return success({"items": build(None)})
