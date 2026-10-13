# 契约：list-profit-overview

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/overview
作用：利润统计概览。一天一行。读日表，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

Header `Authorization`。要菜单 23。

公共查询：`page`（默认 1）、`page_size`（默认 20，最大 100）、`date_start`、`date_end`（北京时间，默认今天，起止都含当天）、`sort_order`（`asc` / `desc`，默认 `desc`）、`sort_by`（`stat_cost` / `recovery` / `recovery_rate` / `profit`，默认 `stat_cost`）、`mode`（`all` 全域+标准、`standard` 仅标准、`iaa`、`iap`、`uni` 仅全域，默认 `all`）、`drama_type`（`真人剧` / `漫剧`，不传为全部）、`platform`（`tomato` 番茄 / `ouxi` 鸥溪，不传为全部）。

另有 `department_id`：分组，投手所在部门。不传为权限内全部。

负责人看全部部门。其余账号按数据权限；数据范围为空时只看自己所在部门。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 是筛选后全部行的合计，不是当前页。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_date | string | `YYYY-MM-DD` |
| stat_cost | number | 消耗 |
| recovery | number | 回收，`stat_pay_amount` |
| recovery_rate | number | 合计回收 / 合计消耗。分母为 0 时为 0 |
| profit | number | 回收×0.95 − 消耗×当天 ROI 系数。跨天先按天算再相加 |

`summary` 四个字段与行相同。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 23 | 403 | |
| 起日晚于止日、mode 或排序不合法 | 422 | |


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 利润报表 / 利润统计概览（菜单 23） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
