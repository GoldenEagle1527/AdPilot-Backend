# 契约：get-manhua-trend

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/manhua/trend
作用：漫剧趋势弹框。所选一天按小时的消耗（`stat_cost`）和回收（`stat_pay_amount`）。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `IAP` 要菜单 9，`IAA` 要菜单 5 |
| charge_mode | query | string | 是 | `IAP` / `IAA` |
| grain | query | string | 是 | `drama` 剧目行、`project` 项目行、`promotion` 计划行 |
| id | query | integer | 是 | `drama`：`manhua_series.id`；`project`：`cdp_project_id`；`promotion`：`cdp_promotion_id` |
| panel | query | string | 否 | 仅 `IAP` 的 `drama`：该行面板，空串表示无面板的旧行。不传则合计该剧全部面板。其它组合传了 422 |
| date | query | string | 否 | `YYYY-MM-DD`，北京时间，默认今天 |

可见性与列表一致：

- `drama`：该剧（`IAP` 再加面板）在本收费模式下的项目里，当前用户须是投手之一；曲线是这些项目全部投手之和。
- `project` / `promotion`：项目投手须是当前用户。
- 不可见或不存在一律 404。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| date | string | 所选日 `YYYY-MM-DD` |
| items | array | `{ "hour", "stat_cost", "stat_pay_amount" }`。`hour` 0–23（北京时间） |

所选日是今天时只返回已经到了的小时（0 到当前小时）；过去的日子返回 0–23；将来的日子 `items: []`。到了但快照没有数据的小时补 0。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 缺本收费模式对应的菜单 | 403 | |
| 行不存在或不可见 | 404 | `报表行不存在或不可见` |
| 非 `IAP` 剧目却传面板 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| R1IAP、R1IAA、项目、计划页的「趋势」 | 弹框曲线 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
