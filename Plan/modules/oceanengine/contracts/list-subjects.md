# 契约：list-subjects

业务id：oceanengine
文档版本：1
方法：GET
路径：/api/v1/oceanengine/subjects
作用：分页列出投放主体。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `65` |
| page | query | int | 否 | 从 1，默认 1 |
| page_size | query | int | 否 | 默认 20，上限 100 |
| name | query | string | 否 | 主体名称模糊 |
| subject_no | query | int | 否 | 主体 id 精确 |
| delivery_mode | query | string | 否 | `standard` 标准投放，`uni` 全域投放 |
| theater_kind | query | string | 否 | 剧场类型文本，精确匹配 |

无请求体。管理列表不按部门数据权限过滤。

## 响应

分页：`list` / `total` / `page` / `page_size`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 本库主键 |
| name | string | 主体名称 |
| subject_no | int | 主体 id，未删除行内唯一 |
| short_name | string \| null | |
| delivery_mode | string | `standard` 或 `uni` |
| theater_name | string | 剧场名称，文本，无外键 |
| theater_kind | string | 剧场类型，文本。约定「小程序」或「端原生」 |
| charge_mode | string | 收费模式，文本。约定 `IAA` 或 `IAP` |
| min_bid | number | 最多 2 位小数 |
| max_bid | number | 最多 2 位小数 |
| roi_goal | number \| null | 最多 3 位小数 |
| department_id | int \| null | 空表示各部门都能用 |
| material_account_id | int | 素材账户，广告主列表里的 advertiser_id |
| dual_bid | bool | 真 = 出价加 ROI，假 = 只出价 |
| bid_panel | string \| null | 出价面板文本 |

请求与响应都不出现 `actual_bid`、`arpu`。已软删的不返回。本阶段没有删除接口。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 65 | 403 | |
| 校验失败 | 422 | |

## 业务规则

剧场只存名称、类型、收费模式三份文本。v1 不建剧场外键，这三个字段名不随以后的剧场模块改掉。

## 被谁调用

投放主体管理页。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
