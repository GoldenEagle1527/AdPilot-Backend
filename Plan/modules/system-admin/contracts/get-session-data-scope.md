# 契约：get-session-data-scope

业务id：system-admin
文档版本：3
方法：GET
路径：/api/v1/system-admin/session/data-scope
作用：当前用户**有效**数据范围。未勾选任何部门 = 仅本人；勾选则含启用部门及启用子孙。

作者：调度者
状态：accepted
更新日期：2026-09-21

## 请求

无请求体。无 path/query。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>` |

## 响应

`data` 内字段。信封、id 见 [说明.md](说明.md)。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| self_only | boolean | true = 未勾选部门，只有当前用户自己的数据 |
| user_id | string | 当前用户 id，`self_only` 时业务方按此过滤「仅本人」 |
| department_ids | string[] | 可见启用部门（已展开子孙）。`self_only` 时为空数组 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未带或 Token 无效 / 无对应菜单或组件 / 字段校验失败 | 401 / 403 / 422 | 见说明.md 共用错误码 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 其它业务列表 | 过滤。`self_only` 时只查该 `user_id`；否则按 `department_ids` 下的用户过滤 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 3 | 否 | 有效范围排除停用部门 | 姜英睿 |
| 2026-09-20 | 2 | 是 | 空集合从「无部门数据权限」改为仅本人；增加 `self_only` `user_id`；部门 id 含子孙。快照 [_history/get-session-data-scope-v1.md](_history/get-session-data-scope-v1.md) | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
