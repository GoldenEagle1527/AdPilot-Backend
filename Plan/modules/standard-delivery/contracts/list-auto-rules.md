# 契约：list-auto-rules

业务id：standard-delivery
文档版本：1
方法：GET
路径：/api/v1/standard-delivery/auto-rules
作用：分页列出当前登录投手自己的自动投放规则。不执行规则。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。免费菜单 `51`，付费菜单 `52` |
| charge_mode | query | string | 是 | `IAA` 或 `IAP` |
| name | query | string | 否 | 规则名称，模糊 |
| template_id | query | integer | 否 | 模板 id |
| series_id | query | integer | 否 | 选中了这部短剧 |
| no_bid_only | query | boolean | 否 | 是否只针对最大转化 |
| scheduled | query | boolean | 否 | `true` 只看已预约，`false` 只看未填预约（立即执行，本轮仍不跑） |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

## 响应

分页。`list` 每项字段同 [get-auto-rule.md](get-auto-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有该收费模式的菜单 |
| 422 | `charge_mode: ...` | 枚举或分页不合法 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 免费/付费端原生自动投放 | 规则列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
