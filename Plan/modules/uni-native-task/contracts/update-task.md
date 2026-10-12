# 契约：update-task

业务id：uni-native-task
文档版本：4
方法：PUT
路径：/api/v1/uni-native-tasks/{task_id}
作用：只改当前投手自己、且仍是 `saved` 的端原生投放任务。改完后在同一次请求里创建项目和广告。`running`、`done`、`failed` 返回 409，不再建一套项目。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| task_id | path | integer | 是 | 任务 id |
| body | body | object | 是 | 与 [create-task.md](create-task.md) 的请求体相同。不传推广链、不传视频的带出规则也与新建相同 |

抖音号校验与 [create-task.md](create-task.md) 相同，包含必须已分配到本次模板。成功时状态为 `done`。

## 响应

保存并提交后的整条记录，字段同 [list-tasks.md](list-tasks.md) 的列表项。成功 HTTP 200，`status` 为 `done`。

## 错误

与 [create-task.md](create-task.md) 相同。任务不存在、已软删或不是当前投手时，404，`投放任务不存在`。

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 409 | `任务已创建，不能再修改` | 状态已是 `running`、`done` 或 `failed` |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 仅未创建项目的旧行可再保存并提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 4 | 是 | 请求体随新建：不传推广链时带出全部档位，不传视频时只带投手归属。快照 [_history/update-task-v3.md](_history/update-task-v3.md) | |
| 2026-10-12 | 3 | 是 | 仅 `saved` 可改，改完同一次请求提交，成功为 `done`。已创建的返回 409。抖音号校验与新建相同。快照 [_history/update-task-v2.md](_history/update-task-v2.md) | |
| 2026-10-08 | 2 | 否 | 省略推广链时与新建相同：剧场表存在则补该剧 IAA 的 `link_text` | |
| 2026-09-30 | 1 | 否 | 初稿 | |
