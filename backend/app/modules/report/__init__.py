"""数据报表：漫剧、全域、利润、素材。读日表，不调巨量。"""

from app.modules.report.controller import router
import app.modules.report.ledger_api  # noqa: F401

__all__ = ["router"]
