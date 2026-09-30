# 契约：get-run

业务id：uni-native-auto-run
文档版本：1
方法：GET
路径：/api/v1/uni-native-auto-runs/{run_id}
作用：查询一条未删除的端原生自动化投放执行记录。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| run_id | path | integer | 是 | 执行记录 id |

无请求体。

## 响应

`data` 为一条记录，字段同 [list-runs.md](list-runs.md) 的列表单项。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | 未带或 Token 无效 | 未登录 |
| 404 | 执行记录不存在 | id 没有，或已软删 |
| 422 | `run_id: ...` | 路径不是整数 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生自动化投放 | 查看一条执行记录 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
