# 契约：list-free-robots

业务id：standard-robot
文档版本：1
方法：GET
路径：/api/v1/standard-native-robots/free
作用：分页列出当前登录投手自己的免费（IAA）漫剧端原生机器人。不执行。

作者：
状态：draft
更新日期：2026-10-10

## 请求

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `76` |
| page | query | integer | 否 | 从 1，缺省 1 |
| page_size | query | integer | 否 | 默认 20，上限 100 |
| name | query | string | 否 | 规则名称，模糊。`%` 和 `_` 按字面量 |
| is_enabled | query | boolean | 否 | 开关。不传为全部 |

无请求体。多传 query 返回 422。排序为创建时间倒序、同秒按 id 倒序。只含未删除、`charge_mode=IAA`、`pitcher_user_id` 为当前用户的行。

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 主键 |
| name | string | 规则名称 |
| charge_mode | string | `IAA` |
| rule_kind | string | `nb`、`drama`、`promotion_link` |
| schedule_kind | string | `hourly` 每小时、`period` 每天 |
| schedule_hour | integer \| null | 每天执行的小时。每小时规则可空 |
| schedule_minute | integer | 0–59 |
| template_id | string | 免费端原生模板 |
| pitcher_user_id | string | 所属投手 |
| platform_id | string \| null | 推广链规则的剧场平台 |
| accounts_per_series | integer | 每部剧新账户数 |
| max_videos_per_series | integer | 每部剧视频上限 |
| stat_span | string \| null | `today` 或 `yesterday` |
| cost_min | string \| null | 消耗下限，两位小数 |
| cost_max | string \| null | 消耗上限 |
| recovery_min | string \| null | 回收下限，四位小数，比值不是百分数 |
| recovery_max | string \| null | 回收上限 |
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
| 2026-10-10 | 1 | 否 | 初稿 | |
