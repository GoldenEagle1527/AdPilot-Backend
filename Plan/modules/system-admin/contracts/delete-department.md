# 契约：delete-department

业务id：system-admin
文档版本：1
方法：DELETE
路径：/api/v1/system-admin/departments/{id}
作用：软删部门。列表不再返回；库中保留行。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 部门 id |

无请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| deleted | boolean | 恒为 true |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 部门下仍有未删除员工 | 409 | `HAS_MEMBERS` |
| 仍有未删除子部门 | 409 | `HAS_CHILDREN` |
| 部门不存在或已删除 | 404 | `NOT_FOUND` |

## 被谁调用

部门管理 · 删除

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
