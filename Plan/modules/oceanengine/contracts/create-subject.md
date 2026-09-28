# 契约：create-subject

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/subjects
作用：创建投放主体。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。不接收 `actual_bid`、`arpu`，传入则 422。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `65` |
| name | body | string | 是 | |
| subject_no | body | int | 是 | 主体 id，未删除行内唯一 |
| short_name | body | string \| null | 否 | |
| delivery_mode | body | string | 是 | `standard` 或 `uni` |
| theater_name | body | string | 是 | 剧场名称，文本，无外键 |
| theater_kind | body | string | 是 | 剧场类型，文本。约定「小程序」或「端原生」。本阶段页面只应选出端原生 |
| charge_mode | body | string | 是 | 收费模式，文本。约定 `IAA` 或 `IAP` |
| min_bid | body | number | 是 | 最多 2 位小数 |
| max_bid | body | number | 是 | 最多 2 位小数，且 `min_bid <= max_bid` |
| roi_goal | body | number \| null | 否 | 最多 3 位小数 |
| department_id | body | int \| null | 否 | 空表示各部门都能用 |
| material_account_id | body | int | 是 | 广告主列表里的 advertiser_id，且该户未解绑 |
| dual_bid | body | bool | 是 | 真 = 出价加 ROI，假 = 只出价 |
| bid_panel | body | string \| null | 否 | |

## 响应

与 [list-subjects.md](list-subjects.md) 的单行字段相同，并含新 `id`。成功 `data` 为这一行。不含 `actual_bid`、`arpu`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 65 | 403 | |
| 素材账户不存在或已解绑 | 422 | |
| 出价区间或小数位不合法 | 422 | |
| `subject_no` 与未删除行重复 | 409 | |
| 多出来的字段（含 `actual_bid`、`arpu`） | 422 | `extra=forbid` |

## 业务规则

- 剧场没有外键。剧场模块落地后只在内部补关联，对外这三个文本字段不改名、不改类型。
- 不提供删除接口。
- 归属部门为空：以后投放任务里各部门都能用。有值则只有该部门（含其数据权限覆盖到的使用场景）。本接口的管理写入不按这个范围拦截。

## 被谁调用

投放主体管理页的新建。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
