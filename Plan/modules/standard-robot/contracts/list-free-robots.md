# 契约：list-free-robots

业务id：standard-robot
文档版本：3
方法：GET
路径：/api/v1/standard-native-robots/free
作用：分页列出当前登录投手自己的免费（IAA）漫剧端原生机器人。不执行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `76` |
| page | query | integer | 否 | 从 1，缺省 1 |
| page_size | query | integer | 否 | 默认 20，上限 100 |
| name | query | string | 否 | 规则名称，模糊。`%` 和 `_` 按字面量 |
| is_enabled | query | boolean | 否 | 开关。不传为全部 |

无请求体。多传 query 返回 422。排序为 `sort_order` 升序，相同再按创建时间倒序、同秒按 id 倒序。只含未删除、`charge_mode=IAA`、`pitcher_user_id` 为当前用户的行。旧行 `sort_order` 为 0，顺序与原先的创建时间倒序一致。

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 主键 |
| name | string | 规则名称 |
| charge_mode | string | `IAA` |
| rule_kind | string | `nb`、`drama`、`promotion_link` |
| schedule_kind | string | `daily`/`period` 每天定点，`cycle`/`hourly` 按间隔 |
| schedule_hour | integer \| null | 每天开始或定点的小时 |
| schedule_minute | integer | 0–59 |
| schedule_end_hour | integer \| null | 每天结束小时。NB 起止时间，没填为空 |
| schedule_end_minute | integer \| null | 每天结束分钟。与结束小时成对 |
| delivery_hours | integer \| null | NB 投放时间，小时 |
| bid_type | string \| null | NB 竞价策略：`CUSTOM` 稳定成本、`NO_BID` 最大转化 |
| cycle_minutes | integer \| null | NB 周期，分钟 |
| sort_order | integer | 排序，小的在前。旧行为 0 |
| template_id | string | 免费端原生模板 |
| pitcher_user_id | string | 所属投手 |
| platform_id | string \| null | 剧场应用 id。剧条件和推广链都回，没选为空 |
| accounts_per_series | integer | 每部剧新账户数 |
| max_videos_per_series | integer | 每部剧视频上限 |
| stat_span | string \| null | `today` 或 `yesterday` |
| cost_op | string \| null | 消耗比较：`gt` 大于、`lt` 小于、`gte` 大于等于、`lte` 小于等于。没选为空 |
| cost_min | string \| null | 消耗下限，两位小数。大于、大于等于时用这个数 |
| cost_max | string \| null | 消耗上限。小于、小于等于时用这个数 |
| recovery_op | string \| null | 回收率比较，取值同 `cost_op` |
| recovery_min | string \| null | 回收下限，四位小数，比值不是百分数。大于、大于等于时用这个数 |
| recovery_max | string \| null | 回收上限。小于、小于等于时用这个数 |
| is_enabled | boolean | 开关 |
| created_at | string | 北京时间 `+08:00` |
| updated_at | string | 北京时间 `+08:00` |

另有 `total`、`page`、`page_size`。空结果是 `list: []`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有菜单 76 |
| 422 | `page: ...` | 分页或筛选不合法 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 标准自动投放策略 / (免费)漫剧端原生机器人 | 列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 3 | 否 | 列表项增加 `cost_op`、`recovery_op`。小于、小于等于的数值仍在 `cost_max`、`recovery_max` | |
| 2026-10-13 | 2 | 否 | 列表项增加投放时间、竞价策略、周期、每天结束时分、排序；`platform_id` 剧条件也回；`schedule_kind` 增加 `daily`、`cycle` | |
| 2026-10-10 | 1 | 否 | 初稿 | |
