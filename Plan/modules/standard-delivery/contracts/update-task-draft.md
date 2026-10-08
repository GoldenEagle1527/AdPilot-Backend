# 契约：update-task-draft

业务id：standard-delivery
文档版本：3
方法：PUT
路径：/api/v1/standard-delivery/task-drafts/{draft_id}
作用：整表保存自己的任务草稿。账户、视频、标题按本次提交替换。换模板时收费模式必须和原来的一致。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条草稿的收费模式 |
| draft_id | path | integer | 是 | 草稿 id |
| body | body | object | 是 | 字段与 [create-task-draft.md](create-task-draft.md) 相同 |

仍然只有一个 `douyin_account_id`，可以不传。正文须带 `album_url` 和 `project_operation`。广告开关、版位、项目预算、商品库可以不传，确认提交用模板。不收 `asset_ids`。

## 响应

保存后的整条记录，字段同 [get-task-draft.md](get-task-draft.md)。

## 错误

与 [create-task-draft.md](create-task-draft.md) 相同，另加：

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `投放草稿不存在` | 不存在、已软删，或不是当前投手的 |
| 400 | `模板收费模式与草稿不一致` | 新模板的 IAA/IAP 和草稿原来的不同 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 再次保存草稿 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 3 | 否 | 正文跟随新增草稿：广告开关、版位、项目预算、商品库、抖音号可以不传 | |
| 2026-10-08 | 2 | 是 | 正文跟随新增草稿，必须带专辑链接和两个开关。快照见 [_history/update-task-draft-v1.md](_history/update-task-draft-v1.md) | |
| 2026-09-29 | 1 | 否 | 初稿 | |
