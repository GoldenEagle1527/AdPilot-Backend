# 契约：create-free-robot

业务id：standard-robot
文档版本：3
方法：POST
路径：/api/v1/standard-native-robots/free
作用：新增一条免费漫剧端原生机器人。模板必须是 IAA。不在这次请求里提交投放。

作者：
状态：draft
更新日期：2026-10-13

## 请求

菜单 `76`。Body 多传 422。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 1–128 字 |
| rule_kind | string | 是 | `nb`、`drama`、`promotion_link` |
| schedule_kind | string | 是 | `daily`/`period` 每天定点，`cycle`/`hourly` 按间隔 |
| schedule_hour | integer \| null | 否 | `daily` 或 `period` 时必填，0–23 |
| schedule_minute | integer | 否 | 0–59，缺省 0 |
| schedule_end_hour | integer \| null | 否 | 每天结束小时，0–23。NB 起止时间 |
| schedule_end_minute | integer \| null | 否 | 每天结束分钟。与结束小时必须同时给或同时不给 |
| delivery_hours | integer \| null | 否 | NB 投放时间，1–8760 小时 |
| bid_type | string \| null | 否 | NB 竞价策略：`CUSTOM`、`NO_BID` |
| cycle_minutes | integer \| null | 否 | NB 周期，1–1440 分钟 |
| sort_order | integer | 否 | 排序，0–9999，缺省 0 |
| template_id | integer | 是 | 免费端原生模板 |
| platform_id | integer \| null | 否 | 剧场应用 id。`promotion_link` 时必填；`drama` 有值就存并回传 |
| accounts_per_series | integer | 否 | 1–20，缺省 3 |
| max_videos_per_series | integer | 否 | 1–800，缺省 200 |
| stat_span | string \| null | 否 | `today` 或 `yesterday` |
| cost_op | string \| null | 否 | `gt` 大于、`lt` 小于、`gte` 大于等于、`lte` 小于等于 |
| cost_min / cost_max | number \| null | 否 | 消耗，元。大于、大于等于放 `cost_min`；小于、小于等于放 `cost_max` |
| recovery_op | string \| null | 否 | 回收率比较，取值同 `cost_op` |
| recovery_min / recovery_max | number \| null | 否 | 回收比值。大于、大于等于放 `recovery_min`；小于、小于等于放 `recovery_max` |
| is_enabled | boolean | 否 | 缺省 true |

`charge_mode` 不收，固定 IAA。所属投手是当前用户。

## 响应

字段同 [list-free-robots.md](list-free-robots.md) 的列表项。`charge_mode` 为 `IAA`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `机器人须使用免费端原生模板` | 模板不是 IAA |
| 400 | `推广链规则需要剧场平台` | `promotion_link` 未传 platform_id |
| 400 | `每天执行需要小时` | `daily` 或 `period` 未传 schedule_hour |
| 400 | `每天结束时间要同时给出小时和分钟` | 结束小时和分钟只给了一个 |
| 404 | `模板不存在` | 模板没有或已删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| (免费)漫剧端原生机器人 | 新增 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 3 | 否 | 入参增加消耗、回收率比较符 `cost_op`、`recovery_op` | |
| 2026-10-13 | 2 | 否 | 入参增加投放时间、竞价策略、周期、每天结束时分、排序；剧条件可带剧场；时间调度接受 daily、cycle | |
| 2026-10-10 | 1 | 否 | 初稿。出参补齐可编辑字段 | |
