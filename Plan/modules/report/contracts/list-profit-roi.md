# 契约：list-profit-roi

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/roi
作用：ROI 系数列表。四张利润报表共用。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | 要菜单 23 |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

按创建时间倒序。没有 `summary`。

## 响应

`data.list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 配置 id |
| date_start | string | 生效起，含当天 |
| date_end | string | 生效止，含当天 |
| roi_rate | number | 系数，两位小数 |
| created_date | string | 北京时间。重叠日期取这条最新的 |

## 错误

无菜单 23 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 利润统计概览的 ROI 配置（菜单 23） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
