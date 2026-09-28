# 契约：set-app-status

业务id：theater
文档版本：1
方法：PATCH
路径：/api/v1/theater/apps/{app_id}/status
作用：改一条三方剧场应用的状态（有效/无效）。**只能改状态**，其它字段不可改。对应应用列表里的行内状态切换。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| app_id | path | integer | 是 | 应用主键 |
| is_valid | body | boolean | 是 | 状态：`true` 有效、`false` 无效 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

body 只收 `is_valid`，多传别的（如 `name`、`platform_id`）返回 422。

不验平台：所属平台已禁用时，仍可把应用改成有效或无效。

示例：

```json
{ "is_valid": false }
```

## 响应

改后的整条记录，字段同 [list-apps.md](list-apps.md) 的 **AppItem**。`updated_at` 为改后的时间。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `is_valid: Field required` | 没传 `is_valid`、不是布尔、或 body 多带字段 |
| 404 | `应用不存在` | 应用 id 不存在或已软删 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/应用列表 | 行内切换状态 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
