# 契约：delete-product-snapshot

业务id：uni-template
文档版本：1
方法：DELETE
路径：/api/v1/uni-templates/product-snapshots/{snapshot_id}
作用：软删一份产品模板。标准投放删除的是同一条。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。全域模板菜单 `60` |
| snapshot_id | path | integer | 是 | 未删除的产品模板 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 模板 id |
| deleted | boolean | 恒为 `true` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有全域模板菜单 |
| 404 | `产品快照不存在` | 不存在或已软删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板 | 删除模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 1 | 否 | 初稿。对应 3.3.1 产品信息截图里的「删除模版」 | |
