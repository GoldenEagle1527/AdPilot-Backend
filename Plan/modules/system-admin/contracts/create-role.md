# 契约：create-role

业务id：system-admin
文档版本：1
方法：POST
路径：/api/v1/system-admin/roles
作用：新增角色；默认启用，不接收 enabled。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| name | body | string | 是 | |
| remark | body | string | 否 | 最多 200 |

不要传 `enabled`。未传时服务端默认 `true`。

## 响应

`data` 为刚创建的角色对象（字段同 list-roles 的 RoleListItem）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| name | string | |
| remark | string \| null | 未传则为 null |
| enabled | boolean | 恒为 true |
| created_at | string | |
| updated_at | string | |
| assigned_user_count | integer | 0 |
| assigned_department_count | integer | 0 |

## 错误

无特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 页面卡片 | 页面动作 |
| --- | --- |
| 角色管理 | 新增 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
