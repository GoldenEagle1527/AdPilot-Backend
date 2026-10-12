# 契约：list-templates

业务id：uni-template
文档版本：1
方法：GET
路径：/api/v1/uni-templates
作用：分页列出未删除的全域模板。每个登录投手都能看见全部模板，抖音号只显示自己分配的。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| name | query | string | 否 | 模板名称，模糊 |
| subject_id | query | integer | 否 | 投放主体 id |
| charge_mode | query | string | 否 | 投放变现模式：`IAA`、`IAP`，不传为全部 |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 模板 id，本系统自增 |
| name | string | 模板名称 |
| subject_id | string | 主体 id |
| subject_name | string | 主体名称 |
| charge_mode | string | 投放变现模式：`IAA` 或 `IAP` |
| project_budget | string | 项目预算，单位元，两位小数 |
| roi_coefficient | string | ROI 系数，三位小数 |
| aigc_dynamic_creative | boolean | AIGC 动态创意 |
| title_select_mode | string | `manual` 手动、`auto` 自动 |
| douyin_accounts | object[] | 当前投手分配的全域号。每项 `id`、`aweme_id`、`name`。没有则 `[]` |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 422 | `page: ...` | 分页越界、变现模式不认识、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板管理 | 打开列表 |
| 模板抖音号分配 | 打开列表，看自己的抖音号 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
