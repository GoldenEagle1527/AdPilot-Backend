# 契约：list-runs

业务id：uni-native-auto-run
文档版本：1
方法：GET
路径：/api/v1/uni-native-auto-runs
作用：分页列出未删除的端原生自动化投放执行记录。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| rule_type | query | string | 否 | `promotion_link` 或 `drama_condition`。不传为全部 |
| series_name | query | string | 否 | 短剧名称，模糊。去首尾空白，空串当不传；命中 `series_names` 里任意一个；`%` 和 `_` 按字面量 |
| rule_id | query | integer | 否 | 规则 id，精确，即 `uni_robot_rule.id` |
| rule_name | query | string | 否 | 规则名称，模糊。去首尾空白，空串当不传；`%` 和 `_` 按字面量 |

无请求体。多传别的 query 返回 422。排序固定执行时间倒序、同秒按 id 倒序。

## 响应

`data` 为分页：`list` / `total` / `page` / `page_size`。`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 执行记录 id |
| rule_id | string | `uni_robot_rule.id` |
| rule_name | string | 执行当时的规则名称 |
| rule_type | string | `promotion_link` 或 `drama_condition` |
| executed_at | string | 执行时间，北京时间，精确到秒 |
| template_name | string | 执行当时的模板名称 |
| status | string | `success` / `failed` / `partial` |
| series_names | array of string | 这次跑到的短剧名称。可以是 `[]` |
| created_at | string | 北京时间，精确到秒 |
| updated_at | string | 北京时间，精确到秒 |

空结果是 `list: []` 且 `total: 0`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | 未带或 Token 无效 | 未登录 |
| 422 | `rule_type: ...` | 类型不在两种之内、`rule_id` 小于 1、分页越界、多传参数 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生自动化投放 | 列出执行记录 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
