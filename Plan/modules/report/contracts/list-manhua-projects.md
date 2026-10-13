# 契约：list-manhua-projects

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/manhua/projects
作用：漫剧项目层（IAP项目、IAA项目）。所选区间内一个巨量项目一行，只列当前用户自己投的项目。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。`IAP` 要菜单 9，`IAA` 要菜单 5 |
| charge_mode | query | string | 是 | `IAP` / `IAA` |
| page、page_size、date_start、date_end、sort_by、sort_order | query | | 否 | 同 [list-manhua-dramas.md](list-manhua-dramas.md)。默认按 `stat_cost` 倒序 |
| series_id | query | integer[] | 否 | 剧目，多选。剧目页下钻时传该剧 id |
| series_name | query | string | 否 | 剧名，模糊 |
| media | query | string | 否 | 默认 `巨量`。其它值返回空页 |
| drama_type | query | string[] | 否 | `真人剧`、`漫剧` |
| channel | query | string[] | 否 | 剧场平台名 |
| bid_type | query | string[] | 否 | `最大转化`、`稳定成本` |
| panel | query | string[] | 否 | 只有 `IAP` 收；只是筛选，不是响应列。`IAA` 传了 422 |
| drama_age | query | string[] | 否 | `新剧`、`老剧` |
| team | query | string[] | 否 | 投手部门名 |
| pitcher | query | string[] | 否 | 优化师姓名，精确匹配 |

只返回 `delivery_task_draft.pitcher_user_id` 等于当前用户的项目。巨量项目对不上 `delivery_task_project` 的不返回。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 字段同 [list-manhua-dramas.md](list-manhua-dramas.md) 的「指标」，`ROI = 合计回收 / 合计消耗`。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| project_id | integer | `cdp_project_id`，巨量项目 id |
| project_name | string | `cdp_project_name`，快照里的项目名 |
| series_id | integer | `manhua_series.id` |
| book_name | string | 剧名 |
| pitcher | string | 投手姓名 |
| team | string | 投手部门名 |
| created_at | string or null | 中台存下这个项目的时间（`delivery_task_project.created_date`），北京时间 `+08:00` |
| first_cost_time | string or null | 第一个 `stat_cost > 0` 的快照小时，不限所选区间。北京时间 `+08:00` |
| project_budget | number or null | 草稿上的项目预算；草稿为空取模板 |
| roi_goal | number or null | 模板 `roi_goal` |
| （指标） | | 同 [list-manhua-dramas.md](list-manhua-dramas.md)「指标」 |

不返回：面板列（`IAP` 面板只做筛选）、出价（`ad_platform_cdp_promotion_bid` 是巨量广告维度，本期快照未存）、起量工具。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 缺本收费模式对应的菜单 | 403 | `已登录但无对应菜单或组件` |
| 起日晚于止日、`IAA` 传面板、排序字段不支持 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| R1IAP / R1IAA 下钻 | 项目列表 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
