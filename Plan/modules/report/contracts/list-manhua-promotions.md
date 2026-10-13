# 契约：list-manhua-promotions

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/manhua/promotions
作用：漫剧计划层（IAP计划、IAA计划）。所选区间内一条巨量广告一行，只列当前用户自己投的广告。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

与 [list-manhua-projects.md](list-manhua-projects.md) 完全相同（同一套筛选、菜单、默认排序）。项目页下钻时前端按 `series_id` 等条件带过来；本接口不单独收 `project_id`。

只返回 `delivery_task_promotion.ocean_promotion_id` 对得上、且所属项目的投手是当前用户的广告。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 同 [list-manhua-dramas.md](list-manhua-dramas.md)「指标」。

`list` 每一项：在 [list-manhua-projects.md](list-manhua-projects.md) 的项目行字段之外：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| promotion_id | integer | `cdp_promotion_id`，巨量广告 id。字段表里「计划就是项目」的备注作废 |
| promotion_name | string | `cdp_promotion_name` |
| created_at | string or null | 中台存下这条广告的时间（`delivery_task_promotion.created_date`） |
| first_cost_time | string or null | 这条广告第一个 `stat_cost > 0` 的快照小时 |

`project_id`、`project_name`、剧、投手、预算、ROI 系数、指标同项目行。

## 错误

同 [list-manhua-projects.md](list-manhua-projects.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| IAP项目 / IAA项目 下钻 | 计划列表 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
