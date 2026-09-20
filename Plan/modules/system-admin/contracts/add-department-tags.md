# 契约：add-department-tags

业务id：system-admin
文档版本：1
方法：PUT
路径：/api/v1/system-admin/departments/batch-tags
作用：给多个部门**追加**标签（已有的保留）。前端勾选多行后打标只调本接口。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| department_ids | body | string[] | 是 | 至少 1 个 |
| tag_ids | body | string[] | 是 | 至少 1 个；须是目录中已有标签 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | `{ id, tags: Tag[] }[]` | 每个部门追加后的标签 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 部门或标签不存在 | 404 | `NOT_FOUND` |

## 被谁调用

部门管理 · 添加部门标签

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
