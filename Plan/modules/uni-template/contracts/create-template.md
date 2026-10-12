# 契约：create-template

业务id：uni-template
文档版本：1
方法：POST
路径：/api/v1/uni-templates
作用：新增一条全域模板。不分配抖音号，也不创建投放任务。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| name | body | string | 是 | 模板名称，去首尾空白，1–128 字。同一变现模式下未删除的全域模板不重名 |
| subject_id | body | integer | 是 | `delivery_subject.id`。须未删除、`delivery_mode=uni`，且 `charge_mode` 与模板相同 |
| charge_mode | body | string | 是 | 投放变现模式：`IAA`、`IAP` |
| project_budget | body | number | 是 | 项目预算，单位元，大于 0，最多两位小数 |
| roi_coefficient | body | number | 是 | ROI 系数，0–9999.999，最多三位小数 |
| aigc_dynamic_creative | body | boolean | 是 | AIGC 动态创意 |
| title_select_mode | body | string | 是 | `manual` 手动、`auto` 自动 |

多传字段返回 422。不收标准模板的出价面板、每账户广告条数、`gender`、`age_bands`。

示例：

```json
{
  "name": "全域甲",
  "subject_id": 7,
  "charge_mode": "IAA",
  "project_budget": "88.50",
  "roi_coefficient": "1.250",
  "aigc_dynamic_creative": true,
  "title_select_mode": "manual"
}
```

## 响应

新建后的整条记录，字段同 [list-templates.md](list-templates.md) 的列表项。`douyin_accounts` 为 `[]`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `主体不存在` | 主体 id 不存在或已软删 |
| 400 | `主体不是全域投放` | 主体是标准投放 |
| 400 | `主体收费模式与模板不一致` | 主体的 IAA/IAP 和模板不同 |
| 409 | `模板名称已存在` | 同一变现模式下的全域模板重名 |
| 422 | `name: ...` | 名称空白、超长、枚举不认识、预算或 ROI 越界、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板管理 | 新增 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 1 | 否 | 文档：写明不收标准模板的 `gender`、`age_bands`，多传仍 422 | |
| 2026-09-30 | 1 | 否 | 初稿 | |
