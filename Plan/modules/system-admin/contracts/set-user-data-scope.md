# 契约：set-user-data-scope

业务id：system-admin
文档版本：1
方法：PUT
路径：/api/v1/system-admin/users/{id}/data-scope
作用：整集替换用户可见部门。勾父=选中子孙是调用方交互；后端只存提交的 id，不自动展开。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 用户 id |
| department_ids | body | string[] | 是 | 整集。空数组合法 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| department_ids | string[] | 写入后的集合 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 部门不存在 | 404 | `department_ids` 中有找不到的部门 |

其余见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 用户管理 | 保存数据权限 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
