# 契约：update-auto-rule

业务id：standard-delivery
文档版本：1
方法：PUT
路径：/api/v1/standard-delivery/auto-rules/{rule_id}
作用：整表保存自己的自动规则。短剧按本次提交替换。换模板时收费模式必须和原来的一致。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条规则的收费模式 |
| rule_id | path | integer | 是 | 规则 id |
| body | body | object | 是 | 字段与 [create-auto-rule.md](create-auto-rule.md) 相同。不传 `accounts_per_series` 时按 3，不传 `max_videos_per_series` 时按 200，不传 `no_bid_only` 时按 false |

## 响应

保存后的整条记录，字段同 [get-auto-rule.md](get-auto-rule.md)。

## 错误

与 [create-auto-rule.md](create-auto-rule.md) 相同，另加：

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `自动规则不存在` | 不存在、已软删，或不是当前投手的 |
| 400 | `模板收费模式与规则不一致` | 新模板的 IAA/IAP 和规则原来的不同 |

重名检查会排除自己。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 自动投放 | 再次保存规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
