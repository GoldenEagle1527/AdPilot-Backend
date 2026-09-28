# 契约：unbind-advertisers

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/advertisers/unbind
作用：解绑广告主。有执行中广告则整批拒绝并返回计划名。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `63`。只有菜单 32 为 403 |
| advertiser_ids | body | int[] | 是 | 至少 1 个。巨量广告主 id，与列表 `account_id` 相同 |

## 响应

成功 `data` 为 null。解绑与取消投手分配是同一件事：把 `pitcher_user_id` 清空，账户仍留在列表里，不软删。内部走与分配相同的写入。有执行中广告则整批不改。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 63 | 403 | |
| 任一 id 不存在或已解绑 | 422 | 整批不改 |
| 任一户有 `opt_status=ENABLE` 且未删除的广告 | 409 | 整批不部分成功。`message` 为 `存在执行中的广告：` 接计划名。`name` 为空时用 `promotion_id` 文本，多个用顿号。失败信封的 `data` 为 null，计划名在 `message` |

## 业务规则

- 占用按广告主的巨量 id 查 `opt_status=ENABLE` 且未删除的广告。没有这样的行才允许解绑。
- 解绑后投手为空，列表仍返回该户。之后可以再调用分配。
- Excel 的 `unbind` 与本接口同一条规则。

## 被谁调用

广告主账户页的解绑。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
