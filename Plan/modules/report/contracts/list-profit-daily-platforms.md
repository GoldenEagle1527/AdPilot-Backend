# 契约：list-profit-daily-platforms

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/daily/platforms
作用：每日利润点开某一天，按平台列出。

作者：
状态：draft
更新日期：2026-10-13

## 请求

同 [list-profit-daily.md](list-profit-daily.md)。点某一天时起止日期都传这一天。

## 响应

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| platform | string | `tomato` 或 `ouxi` |
| platform_name | string | 番茄 或 鸥溪 |
| （四个利润字段） | | 同概览 |

目前只有番茄有数。`summary` 同概览。

## 错误

同每日利润。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 每日利润统计，点日期（菜单 24） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
