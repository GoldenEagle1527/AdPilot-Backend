"""广告主导入只接受 xlsx。"""

from __future__ import annotations
import io
import unittest

from openpyxl import Workbook

from app.core.envelope import ApiError
from app.modules.account.commands import _xlsx_rows


def _xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class XlsxImportTests(unittest.TestCase):
    def test_assign_reads_text_and_integer_ids(self) -> None:
        """分配表读出广告主 id 和投手账号。数字单元格按整数字符串。"""
        raw = _xlsx(
            ["广告主 id", "投手登录账号"],
            [[1873916032590219, "pitcher_a"], ["42", "pitcher_b"]],
        )
        rows = _xlsx_rows(raw, "assign")
        self.assertEqual(
            rows,
            [
                {"广告主 id": "1873916032590219", "投手登录账号": "pitcher_a"},
                {"广告主 id": "42", "投手登录账号": "pitcher_b"},
            ],
        )

    def test_unbind_requires_only_advertiser_column(self) -> None:
        """解绑表只有广告主 id 一列。"""
        raw = _xlsx(["广告主 id"], [[7]])
        self.assertEqual(_xlsx_rows(raw, "unbind"), [{"广告主 id": "7"}])

    def test_csv_is_rejected(self) -> None:
        """CSV 不是 xlsx。"""
        with self.assertRaises(ApiError) as caught:
            _xlsx_rows("广告主 id\n1\n".encode(), "unbind")
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(caught.exception.message, "文件不是 xlsx")

    def test_wrong_header_is_rejected(self) -> None:
        """表头与 action 不一致时整份拒绝。"""
        raw = _xlsx(["广告主 id"], [[1]])
        with self.assertRaises(ApiError) as caught:
            _xlsx_rows(raw, "assign")
        self.assertEqual(caught.exception.message, "表头不正确")
