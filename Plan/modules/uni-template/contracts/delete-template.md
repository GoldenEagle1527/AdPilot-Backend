# 契约：delete-template

业务id：uni-template
文档版本：1
方法：DELETE
路径：/api/v1/uni-templates/{template_id}
作用：软删一条全域模板。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
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
| 404 | `模板不存在` | id 不存在、已软删，或这条是标准模板 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板管理 | 删除 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
