# 契约：copy-product-snapshot

业务id：standard-delivery
文档版本：1
方法：POST
路径：/api/v1/standard-delivery/templates/{template_id}/copy-product-snapshot
作用：把一条产品快照抄到标准模板的产品名称、主图、卖点和行动号召。其它列不动。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单随模板收费模式：免费 `45`，付费 `50` |
| template_id | path | integer | 是 | 未删除的标准模板 |
| snapshot_id | body | integer | 是 | 未删除的产品快照 |

多传返回 422。

## 响应

抄完后的模板，字段同 [get-template.md](get-template.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有模板所属收费模式的菜单 |
| 404 | `模板不存在` | 标准模板不存在或已软删 |
| 404 | `产品快照不存在` | 快照不存在或已软删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 标准模板 | 选择产品模板后写入当前模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 1 | 否 | 初稿 | |
