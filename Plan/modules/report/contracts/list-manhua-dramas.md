# 契约：list-manhua-dramas

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/manhua/dramas
作用：漫剧剧目首页（R1IAP、R1IAA）。所选日期区间内一部剧一行，付费再按面板拆行。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。`IAP` 要菜单 9，`IAA` 要菜单 5 |
| charge_mode | query | string | 是 | `IAP` 付费（R1IAP）、`IAA` 免费（R1IAA） |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |
| date_start | query | string | 否 | `YYYY-MM-DD`，北京时间，含当天。默认今天 |
| date_end | query | string | 否 | `YYYY-MM-DD`，北京时间，含当天。默认今天。不能早于 `date_start` |
| bid_type | query | string[] | 否 | 投放类型，多选：`最大转化`（模板 `NO_BID`）、`稳定成本`（模板 `CUSTOM`） |
| panel | query | string[] | 否 | 面板，多选。只有 `IAP` 收，`IAA` 传了 422 |
| drama_age | query | string[] | 否 | `新剧`、`老剧`。新剧 = `manhua_series.publish_time` 的日期落在所选区间内 |
| team | query | string[] | 否 | 团队 = 投手所在部门名称，多选。行里任一投手的部门命中即保留 |
| series_id | query | integer[] | 否 | 仅 `IAA`。剧目 `manhua_series.id`，多选 |
| series_name | query | string | 否 | 仅 `IAA`。剧名，模糊 |
| media | query | string | 否 | 仅 `IAA` 可改。默认 `巨量`；本期只有巨量有数据，其它值返回空页 |
| drama_type | query | string[] | 否 | 仅 `IAA`。`真人剧`、`漫剧`（剧场应用风格 `live_action` / `manhua`） |
| channel | query | string[] | 否 | 仅 `IAA`。剧目渠道，即剧场平台名（如 `番茄`、`鸥溪`） |
| pitcher | query | string[] | 否 | 仅 `IAA`。优化师姓名，多选，精确匹配。行里任一投手命中即保留，指标不变 |
| sort_by | query | string | 否 | 任一数值列名，默认 `stat_cost` |
| sort_order | query | string | 否 | `asc` / `desc`，默认 `desc` |

`IAP` 只收口径里 R1IAP 的筛选（日期、投放类型、面板、新/老剧、团队）。多传仅 `IAA` 的筛选按 422。

行、权限口径见 [口径.md](../../../product/数据报表/口径.md)：

- 只统计中台标准投放提交成功、`delivery_task_draft.charge_mode` 等于本次 `charge_mode` 的巨量项目（`delivery_task_project.ocean_project_id`）。巨量里对不上的项目不进本页。
- `IAP`：键为（剧，`delivery_task_project.bid_panel`）。旧的多面板项目面板为空串，自成一行，不复制。
- `IAA`：键为剧，面板作为列返回。
- 当前用户 id 必须在该行投手里才返回。一行多个投手时，指标是这些投手的项目之和。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 是筛选、权限之后全部行（不只本页）的合计，字段同下方「指标」，另加 `promotion_with_cost_count`。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| series_id | integer | `manhua_series.id`。下钻用 |
| book_name | string | 剧名 |
| media | string | 恒为 `巨量` |
| drama_type | string | `真人剧` / `漫剧`。主体剧场名对不上剧场应用时为空串 |
| channel | string | 剧场平台名，如 `番茄`。对不上为空串 |
| bid_type | string | 该行项目的投放类型，多种用 `、` 连接 |
| panel | string | `IAP`：本行面板，可能为空串。`IAA`：该剧项目上出现过的非空面板，用 `、` 连接 |
| drama_age | string | `新剧` / `老剧` |
| teams | string | 投手部门名，`、` 连接 |
| pitchers | string | 投手姓名，`、` 连接 |
| promotion_with_cost_count | integer | 区间内 `stat_cost > 0` 的广告去重数 |
| （指标） | | 见下表 |

### 指标

全部来自 `oe_delivery_report`（BASIC_DATA 小时快照）在区间内的合计。比率用合计后的分子分母计算，不平均各行比率；分母为 0 时为 0。金额两位小数，ROI 四位小数，百分数两位小数。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_cost | number | 消耗 |
| stat_pay_amount | number | 付费金额，即漫剧回收 |
| pay_amount_roi | number | `stat_pay_amount / stat_cost` |
| attribution_game_in_app_ltv_1day | number | 当日付费金额 |
| attribution_game_in_app_ltv_8days | number | 7 日付费金额 |
| attribution_micro_game_0d_ltv | number | 当日广告变现 LTV |
| attribution_micro_game_7d_ltv | number | 7 日广告变现 LTV |
| attribution_game_in_app_roi_1day | number | 当日付费金额 / 消耗 |
| attribution_game_in_app_roi_8days | number | 7 日付费金额 / 消耗 |
| attribution_micro_game_0d_roi | number | 当日广告变现 LTV / 消耗 |
| attribution_micro_game_7d_roi | number | 7 日广告变现 LTV / 消耗 |
| show_cnt | integer | 展示数 |
| cpm_platform | number | 消耗 × 1000 / 展示数 |
| click_cnt | integer | 点击数 |
| cpc_platform | number | 消耗 / 点击数 |
| active | integer | 激活数 |
| active_cost | number | 消耗 / 激活数 |
| convert_cnt | integer | 转化数 |
| conversion_cost | number | 消耗 / 转化数 |
| ctr | number | 点击数 / 展示数 × 100 |
| active_rate | number | 激活数 / 点击数 × 100 |
| conversion_rate | number | 转化数 / 点击数 × 100 |

空结果是 `list: []`、`total: 0`，`summary` 各项为 0。

## 数据来源与缺口

- 快照由每小时任务写入 `oe_delivery_report`（`BASIC_DATA`，维度 `stat_time_hour`、`cdp_project_id`、`cdp_promotion_id`），每次重拉近 8 天（巨量只给近 8 天小时粒度）。更早的日期停在最后一次拉到的值；任务上线前的日期没有数据。mock 模式不拉。
- 未存：`ad_platform_cdp_promotion_bid`（出价）、`ad_platform_cdp_promotion_roi_goal`。它们是巨量广告维度，加进小时报表会拆行，本期不存。项目/计划页的 ROI 系数用中台模板 `roi_goal`，出价不返回。
- 比率字段（ROI、千展成本、点击率等）不落库，按合计重算。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 没有任一报表菜单，或缺本收费模式对应的菜单 | 403 | `已登录但无对应菜单或组件` |
| 起日晚于止日、`IAA` 传面板、`IAP` 传了 R1IAP 没有的筛选、排序字段不支持 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧报表 / (付费)、(免费)端原生短剧报表 | 剧目首页列表与顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
