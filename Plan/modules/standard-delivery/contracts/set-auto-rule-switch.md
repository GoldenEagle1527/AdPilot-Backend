# 契约：set-auto-rule-switch

业务id：standard-delivery
文档版本：1
方法：PATCH
路径：/api/v1/standard-delivery/auto-rules/{rule_id}/switch
作用：只改自动规则的开关。从关到开且没有 `schedule_start` 时执行一次。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单随规则收费模式：免费 `51`，付费 `52` |
| rule_id | path | integer | 是 | 当前投手自己的规则 |
| is_enabled | body | boolean | 是 | `true` 开启、`false` 关闭 |

多传返回 422。

## 响应

字段同 [get-auto-rule.md](get-auto-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有这条规则所属收费模式的菜单 |
| 404 | `自动规则不存在` | 不存在、已软删，或不是当前投手的 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 自动投放 | 行内开关 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 1 | 否 | 初稿 | |
