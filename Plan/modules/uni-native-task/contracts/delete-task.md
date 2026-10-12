# 契约：delete-task

业务id：uni-native-task
文档版本：1
方法：DELETE
路径：/api/v1/uni-native-tasks/{task_id}
作用：软删当前投手自己的端原生投放任务。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| task_id | path | integer | 是 | 任务 id |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 任务 id |
| deleted | boolean | true |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `投放任务不存在` | id 不存在、已软删，或不是当前投手的 |
| 422 | `task_id: ...` | path 不是整数 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 删除 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
