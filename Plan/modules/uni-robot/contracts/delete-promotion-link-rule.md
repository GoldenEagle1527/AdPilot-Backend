# 契约：delete-promotion-link-rule

业务id：uni-robot
文档版本：1
方法：DELETE
路径：/api/v1/uni-robot/promotion-link-rules/{rule_id}
作用：软删一条按推广链接规则。行仍留在库里，列表不再出现。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |

无请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 被软删的规则 id |
| deleted | boolean | 恒为 true |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按剧条件 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 删除按推广链接规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
