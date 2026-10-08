# 契约：delete-template

业务id：standard-delivery
文档版本：1
方法：DELETE
路径：/api/v1/standard-delivery/templates/{template_id}
作用：软删一条投放模板。还有未删除的草稿或自动规则指向它时拒绝。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条模板的收费模式 |
| template_id | path | integer | 是 | 模板 id |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 模板 id |
| deleted | boolean | 恒为 true |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有对应菜单 |
| 404 | `模板不存在` | 不存在或已软删 |
| 409 | `模板已被投放草稿或自动规则使用` | 还有未删除的草稿或规则 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板管理 | 删除 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
