# 契约：list-departments

业务id：system-admin
文档版本：2
方法：GET
路径：/api/v1/system-admin/departments
作用：部门树（可按名称模糊、部门 id 精确、启停筛选）。已软删部门不出现。节点含已分配角色。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>` |
| name | query | string | 否 | 模糊匹配部门名 |
| id | query | string | 否 | 部门 id 精确；命中后返回该节点、祖先与子孙 |
| enabled | query | boolean | 否 | 按启停筛 |

树不分页。无请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | DepartmentNode[] | 嵌套 `children`；节点含 `tags`、`roles` |

## 错误

无本接口特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 部门管理 | 加载/筛选树 |
| 用户管理 | 按部门树筛人（组织树） |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 2 | 否 | 增加 `id` 精确筛选；节点增加 `roles`；排除软删 | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
