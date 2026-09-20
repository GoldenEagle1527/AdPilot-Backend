from fastapi import APIRouter

from app.modules.material.api.manhua_series import router as manhua_series_router

router = APIRouter()
router.include_router(manhua_series_router)

__all__ = ["router"]
