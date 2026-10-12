# 契约：delete-product-snapshot

业务id：standard-delivery
文档版本：1
方法：DELETE
路径：/api/v1/standard-delivery/product-snapshots/{snapshot_id}
作用：软删一份产品模板。全域编辑页删除的是同一条。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `104` |
| snapshot_id | path | integer | 是 | 未删除的产品快照 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 快照 id |
| deleted | boolean | 恒为 `true` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有产品快照菜单 |
| 404 | `产品快照不存在` | 不存在或已软删 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 标准模板 | 删除产品模板 |
| 全域模板 | 同一条数据，也可走 [delete-product-snapshot.md](../../uni-template/contracts/delete-product-snapshot.md) |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 1 | 否 | 初稿。产品说明第 12 条和截图里的「删除模版」 | |
