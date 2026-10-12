# 契约：list-menu-nodes

业务id：system-admin
文档版本：2
方法：GET
路径：/api/v1/system-admin/menu-nodes
作用：返回菜单节点树。只对顶级节点分页，子节点仍挂在 children 上。可选带每个节点已分配的角色名。

作者：调度者
状态：accepted
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| business_domain | query | string | 否 | 按领域筛 |
| name | query | string | 否 | 模糊匹配节点名 |
| include_assigned_roles | query | boolean | 否 | 默认 false。true 时每个节点带 `assigned_roles`。行为与分页前相同 |
| page | query | int | 否 | 从 1，默认 1。不传返回第一页顶级节点 |
| page_size | query | int | 否 | 默认 20，上限 100。只切顶级节点 |

无请求体。`total` 是筛选后的顶级节点数。子节点留在 `children`，不另分页。

## 响应

分页体：`list` / `total` / `page` / `page_size`。列表字段是 `list`，不是 `items`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | MenuNode[] | 本页顶级节点（筛选后仍按树形，children 完整）。节点形状见 [说明.md](说明.md) 嵌套对象 |
| total | int | 顶级节点总数 |
| page | int | 当前页 |
| page_size | int | 每页条数 |

清单数据可含投放/报表等节点名，这不是要预建那些业务 CRUD。

`include_assigned_roles=false`（默认）：节点不带 `assigned_roles`。  
`include_assigned_roles=true`：每个节点带 `assigned_roles: RoleName[]`（`{ id, name }`）。目录节点在参考产品上已分配角色为「-」，本接口给空数组 `[]`。

## 错误

无特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 角色管理 | 打开分配菜单（`include_assigned_roles=false`） |
| 权限角色查询 | 按领域/名称查树（`include_assigned_roles=true`） |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 2 | 是 | 顶级节点改为分页。不传 `page` 只返回第一页。`data.items` 改为 `data.list`，并增加 `total`、`page`、`page_size`。`include_assigned_roles` 与节点 `children` 不变。快照 [_history/list-menu-nodes-v1.md](_history/list-menu-nodes-v1.md) | |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
