# 契约：list-rules

业务id：uni-robot
文档版本：1
方法：GET
路径：/api/v1/uni-robot/rules
作用：分页列出未删除的全部漫剧机器人。剧条件和推广链在同一页，按填写的排序从小到大。

作者：
状态：draft
更新日期：2026-10-13

## 请求

菜单 `80`。

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>` |
| page | query | integer | 否 | 从 1，缺省 1 |
| page_size | query | integer | 否 | 默认 20，上限 100 |
| name | query | string | 否 | 规则名称，模糊 |
| is_enabled | query | boolean | 否 | 开关。不传为全部 |
| rule_kind | query | string | 否 | `promotion_link` 或 `drama_condition`。不传为两种都在 |

无请求体。多传 query 返回 422。顺序是 `sort_order` 从小到大，相同再按创建时间倒序、同秒按 id 倒序。填 4 的行排在填 6 的前面，不管规则类型。

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 主键 |
| name | string | 规则名称 |
| rule_kind | string | `promotion_link` 或 `drama_condition` |
| template_id | string | 模板 |
| platform_id | string | 剧场平台 |
| max_videos_per_series | integer | 每部剧视频上限 |
| schedule_kind | string | `daily` 每天、`cycle` 周期 |
| schedule_hour | integer | 每天开始小时 |
| schedule_minute | integer | 每天开始分钟 |
| schedule_end_hour | integer \| null | 每天结束小时 |
| schedule_end_minute | integer \| null | 每天结束分钟 |
| cycle_minutes | integer \| null | 周期分钟 |
| sort_order | integer | 排序，小的在前 |
| is_enabled | boolean | 开关 |
| stat_span | string \| null | 仅剧条件：`today`、`yesterday` |
| cost_min | string \| null | 仅剧条件，两位小数 |
| cost_max | string \| null | 仅剧条件 |
| recovery_min | string \| null | 仅剧条件，四位小数 |
| recovery_max | string \| null | 仅剧条件 |
| created_at | string | 北京时间 |
| updated_at | string | 北京时间 |

另有 `total`、`page`、`page_size`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有菜单 80 |
| 422 | `page: ...` | 分页或筛选不合法 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 总列表。按返回顺序展示，不要再按更新时间排 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿。两种规则同一列表，按 sort_order 升序 | |
