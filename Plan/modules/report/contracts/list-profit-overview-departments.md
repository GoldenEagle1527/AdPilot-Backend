# 契约：list-profit-overview-departments

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/overview/departments
作用：利润概览点开某一天，按部门列出。

作者：
状态：draft
更新日期：2026-10-13

## 请求

同 [list-profit-overview.md](list-profit-overview.md)。点某一天时 `date_start` 和 `date_end` 都传这一天。

## 响应

`list` 每一项在四个利润字段之外：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| department_id | integer | 部门。没有部门的行是 0 |
| department_name | string | 部门名 |

四个利润字段同概览。`summary` 同概览。

## 错误

同概览。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 利润统计概览，点日期（菜单 23） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
