# 契约：update-subject

业务id：oceanengine
文档版本：1
方法：PUT
路径：/api/v1/oceanengine/subjects/{id}
作用：修改投放主体。字段与创建相同。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。不接收 `actual_bid`、`arpu`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `65` |
| id | path | int | 是 | 本库主键 |
| name | body | string | 是 | |
| subject_no | body | int | 是 | 未删除行内唯一，可保持原值 |
| short_name | body | string \| null | 否 | |
| delivery_mode | body | string | 是 | `standard` 或 `uni` |
| theater_name | body | string | 是 | 剧场名称，文本，无外键 |
| theater_kind | body | string | 是 | 剧场类型，文本 |
| charge_mode | body | string | 是 | 收费模式，文本 |
| min_bid | body | number | 是 | 最多 2 位小数 |
| max_bid | body | number | 是 | 最多 2 位小数，且 `min_bid <= max_bid` |
| roi_goal | body | number \| null | 否 | 最多 3 位小数 |
| department_id | body | int \| null | 否 | |
| material_account_id | body | int | 是 | 广告主列表里的 advertiser_id，且该户未解绑 |
| dual_bid | body | bool | 是 | |
| bid_panel | body | string \| null | 否 | |

## 响应

与 [list-subjects.md](list-subjects.md) 的单行字段相同。不含 `actual_bid`、`arpu`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 65 | 403 | |
| 主体不存在或已软删 | 404 | |
| 素材账户不存在或已解绑 | 422 | |
| 出价区间或小数位不合法 | 422 | |
| `subject_no` 与其它未删除行重复 | 409 | |
| 多出来的字段（含 `actual_bid`、`arpu`） | 422 | |

## 业务规则

与创建相同：剧场是文本，无外键；`actual_bid`、`arpu` 不出现。没有删除接口。

## 被谁调用

投放主体管理页的编辑。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
