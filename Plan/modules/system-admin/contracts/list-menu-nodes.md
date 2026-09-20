# 契约：list-menu-nodes

业务id：system-admin
文档版本：1
方法：GET
路径：/api/v1/system-admin/menu-nodes
作用：返回菜单节点树（不分页）；可选带每个节点已分配的角色名。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| business_domain | query | string | 否 | 按领域筛 |
| name | query | string | 否 | 模糊匹配节点名 |
| include_assigned_roles | query | boolean | 否 | 默认 false。true 时每个节点带 `assigned_roles` |

无请求体。树不分页，不要传 `page` / `page_size`。

## 响应

`data` 为树对象，不是分页。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | MenuNode[] | 全树（或筛选后仍按树形）。节点形状见 [说明.md](说明.md) 嵌套对象 |

清单数据可含投放/报表等节点名，这不是要前端预建那些页。

`include_assigned_roles=false`（默认）：节点不带 `assigned_roles`。  
`include_assigned_roles=true`：每个节点带 `assigned_roles: RoleName[]`（`{ id, name }`）。目录节点在参考产品上已分配角色为「-」，本接口给空数组 `[]`。

## 错误

无特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 页面卡片 | 页面动作 |
| --- | --- |
| 角色管理 | 打开分配菜单（`include_assigned_roles=false`） |
| 权限角色查询 | 按领域/名称查树（`include_assigned_roles=true`） |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
