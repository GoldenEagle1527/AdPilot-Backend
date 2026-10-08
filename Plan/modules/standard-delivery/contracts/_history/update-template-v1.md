# 契约：update-template

业务id：standard-delivery
文档版本：1
方法：PUT
路径：/api/v1/standard-delivery/templates/{template_id}
作用：整表保存模板的名称、主体、出价面板和每账户广告条数。收费模式不可改。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条模板现有的收费模式 |
| template_id | path | integer | 是 | 模板 id |
| name | body | string | 是 | 同新增 |
| subject_id | body | integer | 是 | 同新增。仍须是标准投放，且收费模式与这条模板一致 |
| bid_panels | body | string[] | 否 | 同新增。付费模板保存后不能是空的 |
| ads_per_account | body | integer | 是 | 1–100 |

不收 `charge_mode`。多传返回 422。

## 响应

保存后的整条记录，字段同 [list-templates.md](list-templates.md) 的列表项。

## 错误

与 [create-template.md](create-template.md) 相同，另加：

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `模板不存在` | id 不存在或已软删 |

重名检查会排除自己。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板管理 | 保存 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
