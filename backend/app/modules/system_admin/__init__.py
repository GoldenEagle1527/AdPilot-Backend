from fastapi import APIRouter

from app.modules.system_admin.deps import require_menu

from app.modules.system_admin.api.department_roles import router as department_roles_router
from app.modules.system_admin.api.department_tags import router as department_tags_router
from app.modules.system_admin.api.departments import router as departments_router
from app.modules.system_admin.api.menu_nodes import router as menu_nodes_router
from app.modules.system_admin.api.password_reset import router as password_reset_router
from app.modules.system_admin.api.role_menus import router as role_menus_router
from app.modules.system_admin.api.roles import router as roles_router
from app.modules.system_admin.api.session_queries import router as session_router
from app.modules.system_admin.api.user_data_scope import router as user_data_scope_router
from app.modules.system_admin.api.user_roles import router as user_roles_router
from app.modules.system_admin.api.user_tags import router as user_tags_router
from app.modules.system_admin.api.users import router as users_router

router = APIRouter()
router.include_router(session_router)
router.include_router(department_tags_router)
router.include_router(departments_router)
router.include_router(department_roles_router)
router.include_router(roles_router)
router.include_router(role_menus_router)
router.include_router(menu_nodes_router)
router.include_router(user_tags_router)
router.include_router(users_router)
router.include_router(user_roles_router)
router.include_router(user_data_scope_router)
router.include_router(password_reset_router)

__all__ = ["require_menu", "router"]
