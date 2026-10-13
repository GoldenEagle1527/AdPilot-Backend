# 契约：list-profit-pitchers

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/pitchers
作用：投手利润。所选区间一个投手一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

Header `Authorization`。要菜单 28。

公共查询：`page`（默认 1）、`page_size`（默认 20，最大 100）、`date_start`、`date_end`（北京时间，默认今天，起止都含当天）、`sort_order`（`asc` / `desc`，默认 `desc`）、`sort_by`（`stat_cost` / `recovery` / `recovery_rate` / `profit`，默认 `stat_cost`）、`mode`（`all` 全域+标准、`standard` 仅标准、`iaa`、`iap`、`uni` 仅全域，默认 `all`）、`drama_type`（`真人剧` / `漫剧`，不传为全部）、`platform`（`tomato` 番茄 / `ouxi` 鸥溪，不传为全部）。

没有投手筛选。负责人看全部部门，其余按数据权限。

## 响应

`list` 每一项：`pitcher_user_id`、`pitcher_name`，加四个利润字段。`summary` 同概览。

## 错误

无菜单 28 为 403。其余同概览。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 利润报表 / 投手利润统计（菜单 28） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
