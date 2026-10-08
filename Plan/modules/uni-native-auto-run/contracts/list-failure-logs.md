# 契约：list-failure-logs

业务id：uni-native-auto-run
文档版本：1
方法：GET
路径：/api/v1/uni-native-auto-runs/{run_id}/failure-logs
作用：分页列出一条执行记录的失败日志。没有公开的新增。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| run_id | path | integer | 是 | 执行记录 id |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |

无请求体。多传别的 query 返回 422。排序固定 id 升序。

## 响应

`data` 为分页：`list` / `total` / `page` / `page_size`。`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 日志 id |
| series_name | string | 失败的短剧名称 |
| reason | string | 失败原因 |
| created_at | string | 北京时间，精确到秒 |

没有失败日志时 `list: []` 且 `total: 0`。执行记录本身须存在。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | 未带或 Token 无效 | 未登录 |
| 404 | 执行记录不存在 | 执行记录没有，或已软删 |
| 422 | `page: ...` | 分页越界、多传参数、路径不是整数 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生自动化投放 | 打开一条记录的失败日志 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
