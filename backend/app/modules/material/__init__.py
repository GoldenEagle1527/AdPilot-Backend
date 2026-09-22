"""素材包：漫剧表、常读短剧列表拉取和落库。定时入口在 app.tasks。"""

from app.modules.material.controller import router

__all__ = ["router"]
