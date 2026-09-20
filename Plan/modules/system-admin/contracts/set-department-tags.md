# 契约：set-department-tags

业务id：system-admin
文档版本：1
方法：PUT
路径：/api/v1/system-admin/departments/{id}/tags
作用：整集替换部门上的标签。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 部门 id |
| tag_ids | body | string[] | 是 | 整集替换；空数组 = 清空 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 部门 id |
| tags | Tag[] | 替换后的标签 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 标签不存在 | 404 | `tag_ids` 中有找不到的 tag |

其余见 [说明.md](说明.md) 共用错误码。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 部门管理 | 打/摘标签 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
