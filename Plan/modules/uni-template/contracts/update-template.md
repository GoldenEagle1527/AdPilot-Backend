# 契约：update-template

业务id：uni-template
文档版本：1
方法：PUT
路径：/api/v1/uni-templates/{template_id}
作用：整表保存一条全域模板。不改任何投手的抖音号分配。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| template_id | path | integer | 是 | 模板 id |
| name | body | string | 是 | 同 [create-template.md](create-template.md)。自己原来的名字不算重名 |
| subject_id | body | integer | 是 | 须为未删除的全域主体，变现模式与本次提交一致 |
| charge_mode | body | string | 是 | 投放变现模式，可以改 |
| project_budget | body | number | 是 | 项目预算 |
| roi_coefficient | body | number | 是 | ROI 系数 |
| aigc_dynamic_creative | body | boolean | 是 | AIGC 动态创意 |
| title_select_mode | body | string | 是 | `manual` 或 `auto` |

这是整表替换，不是补丁。多传字段返回 422。不收标准模板的 `gender`、`age_bands`。

## 响应

保存后的整条记录，字段同 [list-templates.md](list-templates.md) 的列表项。`douyin_accounts` 仍是当前投手已有的分配。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `模板不存在` | id 不存在、已软删，或这条是标准模板 |
| 404 | `主体不存在` | 主体 id 不存在或已软删 |
| 400 | `主体不是全域投放` | 主体是标准投放 |
| 400 | `主体收费模式与模板不一致` | 主体的 IAA/IAP 和本次提交不同 |
| 409 | `模板名称已存在` | 别的未删除全域模板在同一变现模式下已用这个名称 |
| 422 | `name: ...` | 缺必填、枚举不认识、越界、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板管理 | 编辑 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 1 | 否 | 文档：写明不收标准模板的 `gender`、`age_bands`，多传仍 422 | |
| 2026-09-30 | 1 | 否 | 初稿 | |
