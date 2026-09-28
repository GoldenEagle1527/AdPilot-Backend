# 契约：import-advertisers

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/advertisers/import
作用：用 Excel 批量分配或解绑广告主。规则与单批接口相同。

作者：
状态：draft
更新日期：2026-09-23

## 请求

`multipart/form-data`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `63`。只有菜单 32 为 403 |
| action | form | string | 是 | 只允许 `assign` 或 `unbind` |
| file | form | file | 是 | xlsx |

表头：

- `assign`：`广告主 id`、`投手登录账号`
- `unbind`：`广告主 id`

`广告主 id` 与列表 `account_id` 相同。`投手登录账号` 解析为用户，须带投手标签、未删除且启用。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| action | string | `assign` 或 `unbind` |
| success_count | int | 成功行数。只有整份文件都通过才返回 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 63 | 403 | |
| `action` 不是 `assign`\|`unbind`，文件不是 xlsx，表头不对，广告主不存在或已解绑，投手账号不存在或不可用 | 422 | 整份不写 |
| `action=assign` 且任一户已有投手 | 409 | `广告主已有投手，须先解绑`。整份不部分成功。失效户仍挂着投手时同样 409 |
| `action=unbind` 且任一户有 `opt_status=ENABLE` 的广告 | 409 | `message` 带计划名，格式与解绑接口相同。整份不部分成功 |

## 业务规则

两种 `action` 只此 `assign` 与 `unbind`。与 `POST /advertisers/assign`、`POST /advertisers/unbind` 同一套拒绝规则，不绕过占用检查，也不在分配时自动解绑。

## 被谁调用

广告主账户页的导入。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
