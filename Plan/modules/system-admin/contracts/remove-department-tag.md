# 契约：remove-department-tag

业务id：system-admin
文档版本：1
方法：DELETE
路径：/api/v1/system-admin/departments/{id}/tags/{tag_id}
作用：去掉该部门上的一个标签。未挂该标签也返回成功（幂等）。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 部门 id |
| tag_id | path | string | 是 | 标签 id |

无请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 部门 id |
| tags | Tag[] | 去掉后剩余标签 |

## 错误

部门不存在 404。共用码见 [说明.md](说明.md)。

## 被谁调用

部门管理 · 列表标签叉号

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
