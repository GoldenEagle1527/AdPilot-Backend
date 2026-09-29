# 契约：delete-task-draft

业务id：standard-delivery
文档版本：1
方法：DELETE
路径：/api/v1/standard-delivery/task-drafts/{draft_id}
作用：软删当前投手自己的一条任务草稿。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条草稿的收费模式 |
| draft_id | path | integer | 是 | 草稿 id |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 草稿 id |
| deleted | boolean | 恒为 true |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有对应菜单 |
| 404 | `投放草稿不存在` | 不存在、已软删，或不是当前投手的 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 删除草稿 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
