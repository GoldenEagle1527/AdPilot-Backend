# 契约：list-departments

业务id：system-admin
文档版本：3
方法：GET
路径：/api/v1/system-admin/departments
作用：部门树（可按名称模糊、部门 id 精确、启停筛选）。已软删部门不出现。节点含已分配角色。只对顶级部门分页，每个节点仍带完整 children。

作者：调度者
状态：accepted
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>` |
| name | query | string | 否 | 模糊匹配部门名 |
| id | query | string | 否 | 部门 id 精确；命中后返回该节点、祖先与子孙 |
| enabled | query | boolean | 否 | 按启停筛 |
| page | query | int | 否 | 从 1，默认 1。不传返回第一页顶级部门，不是整棵树的全部顶级节点 |
| page_size | query | int | 否 | 默认 20，上限 100。只切顶级部门 |

无请求体。`total` 是筛选后的顶级部门数。子部门留在对应节点的 `children` 里，不另分页。

## 响应

分页体：`list` / `total` / `page` / `page_size`。列表字段是 `list`，不是 `items`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | DepartmentNode[] | 本页顶级部门。嵌套 `children`；节点含 `tags`、`roles` |
| total | int | 顶级部门总数 |
| page | int | 当前页 |
| page_size | int | 每页条数 |

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
| 2026-10-09 | 3 | 是 | 顶级部门改为分页。不传 `page` 只返回第一页。`data.items` 改为 `data.list`，并增加 `total`、`page`、`page_size`。节点的 `children` 仍是完整子树。快照 [_history/list-departments-v2.md](_history/list-departments-v2.md) | |
| 2026-09-20 | 2 | 否 | 增加 `id` 精确筛选；节点增加 `roles`；排除软删 | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
