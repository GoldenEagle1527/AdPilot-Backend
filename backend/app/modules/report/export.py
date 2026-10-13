"""漫剧报表导出 Excel。行与列表接口同一套筛选、权限和排序，不分页。"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook

_METRIC_COLUMNS = [
    ("stat_cost", "消耗"),
    ("stat_pay_amount", "付费金额"),
    ("pay_amount_roi", "回收ROI"),
    ("attribution_game_in_app_ltv_1day", "当日付费金额"),
    ("attribution_micro_game_0d_ltv", "当日广告变现LTV"),
    ("attribution_game_in_app_ltv_8days", "7日付费金额"),
    ("attribution_micro_game_7d_ltv", "7日广告变现LTV"),
    ("attribution_game_in_app_roi_1day", "当日付费ROI"),
    ("attribution_micro_game_0d_roi", "当日广告变现ROI"),
    ("attribution_game_in_app_roi_8days", "7日付费ROI"),
    ("attribution_micro_game_7d_roi", "7日广告变现ROI"),
    ("show_cnt", "展示数"),
    ("cpm_platform", "平均千次展现成本"),
    ("click_cnt", "点击数"),
    ("cpc_platform", "点击成本"),
    ("active", "激活数"),
    ("active_cost", "激活成本"),
    ("convert_cnt", "转化数"),
    ("conversion_cost", "转化成本"),
    ("ctr", "点击率(%)"),
    ("active_rate", "激活率(%)"),
    ("conversion_rate", "转化率(%)"),
]

_HEAD_COLUMNS = {
    "drama": [
        ("book_name", "剧目名称"),
        ("media", "投放媒体"),
        ("drama_type", "剧目类型"),
        ("channel", "剧目渠道"),
        ("bid_type", "投放类型"),
        ("panel", "面板类型"),
        ("drama_age", "新/老剧"),
        ("teams", "团队"),
        ("pitchers", "优化师"),
        ("promotion_with_cost_count", "有消耗计划数"),
    ],
    "project": [
        ("project_name", "项目名称"),
        ("project_id", "项目ID"),
        ("book_name", "剧目名称"),
        ("pitcher", "优化师"),
        ("created_at", "项目创建时间"),
        ("first_cost_time", "项目开始有消耗时间"),
        ("project_budget", "项目预算"),
        ("roi_goal", "ROI系数"),
    ],
    "promotion": [
        ("promotion_name", "计划名称"),
        ("promotion_id", "计划ID"),
        ("book_name", "剧目名称"),
        ("pitcher", "优化师"),
        ("created_at", "计划创建时间"),
        ("first_cost_time", "计划开始有消耗时间"),
        ("project_budget", "项目预算"),
        ("roi_goal", "ROI系数"),
    ],
}

_SHEET_NAMES = {"drama": "剧目", "project": "项目", "promotion": "计划"}


def columns_for(level: str) -> list[tuple[str, str]]:
    return [*_HEAD_COLUMNS[level], *_METRIC_COLUMNS]


def workbook_bytes(level: str, rows: list[dict[str, Any]]) -> bytes:
    """表头一行中文，之后一行一条。空值写空格子。"""
    columns = columns_for(level)
    book = Workbook()
    sheet = book.active
    sheet.title = _SHEET_NAMES[level]
    sheet.append([title for _, title in columns])
    for row in rows:
        sheet.append([row.get(key) for key, _ in columns])
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
