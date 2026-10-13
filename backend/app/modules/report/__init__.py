"""数据报表：漫剧报表与漫剧全域报表的只读查询。读快照，不调巨量。"""

from app.modules.report.controller import router

__all__ = ["router"]
