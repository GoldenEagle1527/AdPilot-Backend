# 契约：list-department-roles

业务id：system-admin
文档版本：1
方法：GET
路径：/api/v1/system-admin/departments/{id}/roles
作用：对该部门的全部角色已分配表。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 部门 id |

无请求体。不分页。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | RoleBrief[] | **全部角色**各一行；含 `assigned` / `assigned_at`（未分配 `assigned_at=null`） |

## 错误

无本接口特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 页面卡片 | 页面动作 |
| --- | --- |
| 部门管理 | 打开分配角色 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
