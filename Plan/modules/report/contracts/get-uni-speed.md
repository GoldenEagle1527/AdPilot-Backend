# 契约：get-uni-speed

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/uni/speed
作用：漫剧全域时速弹框。所选日与前一天按小时对比全域消耗，带分时增长率。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `drama` 要菜单 13，`pitcher` 要 14，`group` 要 15 |
| scope | query | string | 是 | `drama` 剧目行（两个剧目 tab）、`pitcher` 投手行、`group` 组行 |
| id | query | integer | 是 | `drama`：`manhua_series.id`；`pitcher`：用户 id；`group`：部门 id |
| date | query | string | 否 | 所选日 `YYYY-MM-DD`，北京时间，默认今天 |

可见性与列表一致：

- `drama`：当前用户须是该剧全域项目的投手之一；曲线是该剧全部投手之和。
- `pitcher`：`id` 必须是当前用户。
- `group`：`id` 必须在组报表可见部门里（数据范围；为空时本部门）。
- 不满足一律 404。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| date | string | 所选日 |
| previous_date | string | 前一天 |
| cost | object | 消耗 tab，见下 |
| recovery | object | 回收 tab，形状同 `cost`。`UNI_PROJECT_DATA` 没有 `stat_pay_amount`，三个数组恒为 `[]` |

`cost`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| current | array | 所选日 `{ "hour", "value" }`，`value` 是该小时 `all_stat_cost_trend` 合计 |
| previous | array | 前一天 `{ "hour", "value" }` |
| growth_rate | array | `{ "hour", "rate" }`，只覆盖 `current` 的小时。`rate = (当小时 - 前一天同小时) / 前一天同小时`，前一天为 0 时为 0，四位小数 |

所选日是今天时 `current` 只到当前小时（北京时间），没到的小时不返回；过去的日子为 0–23；将来的日子为空。到了但没有快照的小时补 0。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 缺 `scope` 对应菜单 | 403 | |
| 行不存在或不可见 | 404 | `报表行不存在或不可见` |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域四个页面的「消耗时速」 | 弹框曲线 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
