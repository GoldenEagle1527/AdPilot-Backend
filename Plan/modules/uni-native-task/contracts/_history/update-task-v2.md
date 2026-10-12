# 契约：update-task

业务id：uni-native-task
文档版本：2
方法：PUT
路径：/api/v1/uni-native-tasks/{task_id}
作用：整表保存当前投手自己的端原生投放任务。账户、推广链、视频、标题库引用和临时标题按本次提交替换。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| task_id | path | integer | 是 | 任务 id |
| body | body | object | 是 | 与 [create-task.md](create-task.md) 的请求体相同 |

状态仍是 `saved`。`executed_at` 仍为空。不上传素材，不调用巨量。

## 响应

保存后的整条记录，字段同 [list-tasks.md](list-tasks.md) 的列表项。

## 错误

与 [create-task.md](create-task.md) 相同。任务不存在、已软删或不是当前投手时，404，`投放任务不存在`。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 编辑后保存 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 2 | 否 | 省略推广链时与新建相同：剧场表存在则补该剧 IAA 的 `link_text` | |
| 2026-09-30 | 1 | 否 | 初稿 | |
