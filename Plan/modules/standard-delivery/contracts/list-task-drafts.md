# 契约：list-task-drafts

业务id：standard-delivery
文档版本：3
方法：GET
路径：/api/v1/standard-delivery/task-drafts
作用：分页列出当前登录投手自己的投放任务草稿。不返回别人的。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。免费菜单 `39`，付费菜单 `46` |
| charge_mode | query | string | 是 | `IAA` 或 `IAP` |
| template_id | query | integer | 否 | 模板 id |
| subject_id | query | integer | 否 | 模板上的主体 id |
| series_id | query | integer | 否 | 短剧 id |
| douyin_account_id | query | integer | 否 | 抖音号 id |
| library_no | query | integer | 否 | 商品库的巨量库 id |
| placement | query | string | 否 | `aweme`、`aweme_feed`、`universal` |
| optimize_goal | query | string | 否 | `AD_CONVERT_TYPE_ACTIVE` 或 `AD_CONVERT_TYPE_PAY` |
| scheduled | query | boolean | 否 | `true` 只看已预约，`false` 只看未预约 |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

## 响应

分页。`list` 每项字段同 [get-task-draft.md](get-task-draft.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有该收费模式的菜单 |
| 422 | `placement: ...` | 枚举或分页不合法 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 免费/付费端原生投放任务 | 草稿列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 3 | 否 | 列表项跟随详情，抖音号、版位、项目预算、商品库可以为空 | |
| 2026-10-08 | 2 | 否 | 列表项增加专辑链接和项目/广告开关，见 get-task-draft | |
| 2026-09-29 | 1 | 否 | 初稿 | |
