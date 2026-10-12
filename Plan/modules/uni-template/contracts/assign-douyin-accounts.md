# 契约：assign-douyin-accounts

业务id：uni-template
文档版本：1
方法：PUT
路径：/api/v1/uni-templates/{template_id}/douyin-accounts
作用：用请求里的号换掉当前登录投手在这条全域模板上的分配。别的投手的分配不动。空数组表示清空自己的分配。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。投手 id 取登录用户，请求体里不能指定别人 |
| template_id | path | integer | 是 | 全域模板 id |
| douyin_account_ids | body | integer[] | 是 | `douyin_account.id`。须未删除、`delivery_mode=uni`，且 `douyin_pitcher` 里已分给当前用户。可空，最多 100 个，不得重复 |

多传字段返回 422。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| template_id | string | 模板 id |
| douyin_accounts | object[] | 替换后的号，顺序与请求一致。每项 `id`、`aweme_id`、`name` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `模板不存在` | 模板 id 不存在、已软删，或这条是标准模板 |
| 404 | `抖音号不存在` | 有 id 不存在或已软删 |
| 400 | `只能分配全域抖音号` | 号是标准投放 |
| 400 | `抖音号未分配给当前投手` | 号是全域，但没有分给当前用户 |
| 422 | `douyin_account_ids: ...` | 重复、超过 100 个、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板抖音号分配 | 分配抖音号 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
