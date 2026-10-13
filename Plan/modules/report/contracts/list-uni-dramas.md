# 契约：list-uni-dramas

业务id：report
文档版本：2
方法：GET
路径：/api/v1/reports/uni/dramas
作用：漫剧全域短剧报表 tab1「短剧收益」。所选区间内一部剧一天一行。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | 要菜单 13 |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |
| date_start | query | string | 否 | `YYYY-MM-DD`，北京时间，含当天。默认今天 |
| date_end | query | string | 否 | 同上，不能早于 `date_start` |
| series_name | query | string | 否 | 剧名，模糊 |
| sort_by | query | string | 否 | 任一数值列名，默认 `all_stat_cost_trend` |
| sort_order | query | string | 否 | `asc` / `desc`，默认 `desc` |

口径见 [口径.md](../../../product/数据报表/口径.md)：

- 数据来自 `oe_uni_project_report`（`UNI_PROJECT_DATA` 小时快照），按 `uni_native_task_account.ocean_project_id` 回到任务的剧和投手。全域是项目粒度，不按面板拆。对不上中台任务的巨量项目不进本页。
- 行键：（`series_id`，`stat_time_day`）。不带投手列。
- 当前用户 id 必须在该剧当天的投手里（当天有快照数据或新建项目的投手）；一部剧当天多个投手时，指标是这些投手的项目之和。
- 日期既是筛选（区间），也是列 `stat_time_day`。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 是筛选、权限之后全部行的合计，字段同下方「全域指标」。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| series_id | integer | `manhua_series.id`。时速弹框用 |
| book_name | string | 剧名 |
| platform_name | string | 剧场平台名（模板主体剧场名 → 剧场应用 → 平台），如 `番茄`。对不上为空串 |
| stat_time_day | string | `YYYY-MM-DD`，北京时间 |
| （全域指标） | | 见下表 |

### 全域指标

金额是该行当天的合计，两位小数。ROI 用合计重算（四位小数），分母为 0 时为 0，不平均各行比率。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| all_stat_cost_trend | number | 全域消耗 |
| all_stat_total_cost_trend | number | 全域成本 |
| all_gmv_trend | number | 全域 GMV |
| all_billing_gmv_0day_trend | number | 当日全域 GMV |
| all_billing_gmv_24h_trend | number | 24 小时全域 GMV |
| all_billing_gmv_3days_trend | number | 三日全域 GMV，三日 ROI 的分子 |
| all_roi_trend | number | `all_gmv_trend / all_stat_total_cost_trend` |
| all_roi_24h_trend | number | `all_billing_gmv_24h_trend / all_stat_total_cost_trend` |
| all_roi_0day_trend | number | `all_billing_gmv_0day_trend / all_stat_total_cost_trend` |
| all_roi_3days_trend | number | `all_billing_gmv_3days_trend / all_stat_total_cost_trend` |
| all_income_trend | number | 全域收入 |
| all_income_0day_trend | number | 当日全域收入 |
| all_pay_amount_income_trend | number | 付费收入 |
| all_micro_game_income_trend | number | 变现收入 |
| new_project_count | integer | 当天中台存下的全域项目数（任务 `running` / `done`、账户行有 `ocean_project_id`，按账户行更新时间的北京日期）。含该剧全部投手 |
| new_project_with_cost_count | integer | 恒为 0 |
| spending_project_count | integer | 恒为 0 |
| spending_advertiser_count | integer | 恒为 0 |

某天没有消耗但有新建项目的剧也会出该天一行，金额为 0。

## 数据来源与缺口

- 快照由每小时任务写入 `oe_uni_project_report`（`UNI_PROJECT_DATA`，维度 `stat_time_hour`、`cdp_project_id`），每次重拉近 8 天。任务上线前的日期没有数据。mock 模式不拉。
- `all_roi_*` 按巨量原值也存了一份，但列表和汇总都用合计 GMV / 合计成本重算，原值不对外。
- `UNI_PROJECT_DATA` 没有 `stat_pay_amount`，全域没有「回收」数据（时速弹框回收 tab 为空）。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 13 | 403 | |
| 起日晚于止日、排序字段不支持 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧全域报表 / 短剧报表 tab1 | 列表、排序、顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 2 | 是 | 行粒度改为一部剧一天一行，加 `stat_time_day`。v1 快照见 `_history/list-uni-dramas-v1.md` | |
| 2026-10-13 | 1 | 否 | 初稿 | |
