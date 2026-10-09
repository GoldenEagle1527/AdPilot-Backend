# 契约：get-template

业务id：standard-delivery
文档版本：5
方法：GET
路径：/api/v1/standard-delivery/templates/{template_id}
作用：取一条未删除的投放模板。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `45` 或 `50`，须覆盖这条模板的收费模式 |
| template_id | path | integer | 是 | 模板 id |

## 响应

字段同 [list-templates.md](list-templates.md) 的列表项。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有这条模板所属收费模式的菜单 |
| 404 | `模板不存在` | id 不存在或已软删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板管理 | 打开一条模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 5 | 否 | 出参跟随列表项，增加 `gender`、`age_bands` | |
| 2026-10-09 | 4 | 是 | 出参跟随列表项：`library_kind` 替换 `product_library_id` | |
| 2026-10-08 | 3 | 否 | 出参跟随列表项，增加标准模板新增字段 | |
| 2026-10-08 | 2 | 否 | 出参跟随列表项，增加标准提交字段 | |
| 2026-09-29 | 1 | 否 | 初稿 | |
