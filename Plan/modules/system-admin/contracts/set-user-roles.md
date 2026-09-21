# 契约：set-user-roles

业务id：system-admin
文档版本：2
方法：PUT
路径：/api/v1/system-admin/users/{id}/roles
作用：整集替换用户角色；不改部门角色。

作者：调度者
状态：accepted
更新日期：2026-09-21

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 用户 id |
| role_ids | body | string[] | 是 | 只写用户角色。空数组 = 取消全部用户角色（部门角色不动） |

## 响应

与 [list-user-roles.md](list-user-roles.md) 相同形状。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | RoleBrief[] | 替换后仍返回全部角色 |
| department_roles | RoleName[] | 只读，本接口不改 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 角色不存在 | 404 | `role_ids` 中有找不到的角色 |
| 去掉自己的用户管理菜单 | 409 | `CANNOT_STRIP_OWN_ADMIN`（部门角色仍能保住该菜单则放过） |
| 完成后无人再持有用户管理菜单 | 409 | `LAST_ADMIN_REQUIRED` |

其余见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 用户管理 | 保存用户角色 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 2 | 否 | 禁止去掉自己的用户管理；保留最后一名用户管理员 | 姜英睿 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
