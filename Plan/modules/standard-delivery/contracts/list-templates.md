# 契约：list-templates

业务id：standard-delivery
文档版本：1
方法：GET
路径：/api/v1/standard-delivery/templates
作用：按收费模式分页列出投放模板。免费、付费分两次查。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。免费菜单 `45`，付费菜单 `50` |
| charge_mode | query | string | 是 | `IAA` 免费、`IAP` 付费 |
| name | query | string | 否 | 模板名称，模糊 |
| subject_id | query | integer | 否 | 投放主体 id |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 模板 id |
| name | string | 模板名称 |
| charge_mode | string | `IAA` 或 `IAP` |
| subject_id | string | 主体 id |
| subject_name | string | 主体名称 |
| bid_panels | string[] | 出价面板 |
| ads_per_account | integer | 每账户广告条数，1–100 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有该收费模式的菜单 |
| 422 | `charge_mode: ...` | 收费模式不认识，或分页越界 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 免费/付费端原生模板管理 | 打开列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
