# 契约：create-department

业务id：system-admin
文档版本：2
方法：POST
路径：/api/v1/system-admin/departments
作用：新增部门或子部门。

作者：调度者
状态：accepted
更新日期：2026-09-21

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| name | body | string | 是 | |
| parent_id | body | string \| null | 否 | 不传或 `null` = 根 |
| sort | body | integer | 否 | 默认 `0` |
| tenant | body | string | 否 | 不传 = 当前用户 `tenant` |

不要传 `status`/`enabled`（新建后默认 `enabled=true`）。不要传 `tags`/`roles`。

同级重名允许（模型未禁止）。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| （整个 data） | DepartmentNode | 新建节点；`children` 空数组，`tags` 空数组 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 父部门不存在 | 404 | `parent_id` 有值但找不到该部门 |
| 父部门已停用 | 409 | `DEPARTMENT_DISABLED` |

其余见 [说明.md](说明.md) 共用错误码。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 部门管理 | 新增 / 添加子部门 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 2 | 否 | 不能在停用部门下建子部门 | 姜英睿 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
