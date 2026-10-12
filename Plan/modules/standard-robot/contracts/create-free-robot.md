# 契约：create-free-robot

业务id：standard-robot
文档版本：1
方法：POST
路径：/api/v1/standard-native-robots/free
作用：新增一条免费漫剧端原生机器人。模板必须是 IAA。不在这次请求里提交投放。

作者：
状态：draft
更新日期：2026-10-10

## 请求

菜单 `76`。Body 多传 422。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 1–128 字 |
| rule_kind | string | 是 | `nb`、`drama`、`promotion_link` |
| schedule_kind | string | 是 | `hourly` 或 `period` |
| schedule_hour | integer \| null | 否 | `period` 时必填，0–23 |
| schedule_minute | integer | 否 | 0–59，缺省 0 |
| template_id | integer | 是 | 免费端原生模板 |
| platform_id | integer \| null | 否 | `promotion_link` 时必填 |
| accounts_per_series | integer | 否 | 1–20，缺省 3 |
| max_videos_per_series | integer | 否 | 1–800，缺省 200 |
| stat_span | string \| null | 否 | `today` 或 `yesterday` |
| cost_min / cost_max | number \| null | 否 | 消耗区间，元 |
| recovery_min / recovery_max | number \| null | 否 | 回收比值 |
| is_enabled | boolean | 否 | 缺省 true |

`charge_mode` 不收，固定 IAA。所属投手是当前用户。

## 响应

字段同 [list-free-robots.md](list-free-robots.md) 的列表项。`charge_mode` 为 `IAA`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `机器人须使用免费端原生模板` | 模板不是 IAA |
| 400 | `推广链规则需要剧场平台` | `promotion_link` 未传 platform_id |
| 400 | `周期执行需要小时` | `period` 未传 schedule_hour |
| 404 | `模板不存在` | 模板没有或已删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| (免费)漫剧端原生机器人 | 新增 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿。出参补齐可编辑字段 | |
