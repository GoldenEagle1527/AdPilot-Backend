# 契约：list-profit-daily

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/daily
作用：每日利润。一天一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

Header `Authorization`。要菜单 24。

公共查询：`page`（默认 1）、`page_size`（默认 20，最大 100）、`date_start`、`date_end`（北京时间，默认今天，起止都含当天）、`sort_order`（`asc` / `desc`，默认 `desc`）、`sort_by`（`stat_cost` / `recovery` / `recovery_rate` / `profit`，默认 `stat_cost`）、`mode`（`all` 全域+标准、`standard` 仅标准、`iaa`、`iap`、`uni` 仅全域，默认 `all`）、`drama_type`（`真人剧` / `漫剧`，不传为全部）、`platform`（`tomato` 番茄 / `ouxi` 鸥溪，不传为全部）。

另有 `pitcher_user_id`。投手账号忽略该参数，只返回自己。负责人和运营管理员可按投手筛。

## 响应

与 [list-profit-overview.md](list-profit-overview.md) 相同：`stat_date` 加四个利润字段，带 `summary`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 24 | 403 | |
| 参数不合法 | 422 | |


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 利润报表 / 每日利润统计（菜单 24） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
