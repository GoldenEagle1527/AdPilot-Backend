# 契约：list-promotion-link-rules

业务id：uni-robot
文档版本：1
方法：GET
路径：/api/v1/uni-robot/promotion-link-rules
作用：分页列出未删除的按推广链接规则。不列出按剧条件。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| name | query | string | 否 | 规则名称，模糊。去首尾空白，空串当不传；`%` 和 `_` 按字面量处理 |
| is_enabled | query | boolean | 否 | 开关。不传为全部 |

无请求体。多传别的 query 返回 422。排序固定创建时间倒序、同秒按 id 倒序。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | LinkRuleItem[] | 字段同 [get-promotion-link-rule.md](get-promotion-link-rule.md)。空结果是 `[]` |
| total | integer | |
| page | integer | |
| page_size | integer | |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `page: ...` | `page` / `page_size` 越界、`is_enabled` 非布尔、多传参数 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 列出按推广链接规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
