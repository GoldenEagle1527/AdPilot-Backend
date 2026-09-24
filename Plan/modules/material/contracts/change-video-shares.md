# 契约：change-video-shares

业务id：material
文档版本：3
方法：POST
路径：/api/v1/material/videos/{video_id}/shares
作用：上传者提交这条素材共享人的完整名单。名单里没有的人取消共享，他已经分出去的投手保留。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| video_id | path | integer | 是 | 视频素材主键 |
| user_ids | body | integer[] | 是 | 共享人的完整名单。不得重复。已在名单里的不动，名单里没有的取消共享，取消过又出现的恢复。空数组表示全部取消 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。只有上传者能调。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 素材 id |
| added | object[] | 这次真正新共享或恢复的人，按传入顺序。每项 `{ id, nickname }` |
| removed | object[] | 这次真正取消的人，按传入顺序。每项 `{ id, nickname }` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `user_ids: 共享人不能重复` | 名单重复、缺字段、多传字段 |
| 404 | `视频素材不存在` | 素材不存在、已软删，或不是自己上传的 |
| 404 | `用户不存在：9` | `user_ids` 里有用户查不到，报出缺的 id |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 上传者添加或取消共享 |

## 明确不做

- 取消共享时连带删掉这个人分过的投手

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 3 | 否 | `user_ids` 不再限制最多 50 个 | |
| 2026-09-24 | 2 | 是 | `add_user_ids` / `remove_user_ids` 收成一个完整名单 `user_ids`。快照 [_history/change-video-shares-v1.md](_history/change-video-shares-v1.md) | |
| 2026-09-24 | 1 | 否 | 初稿。一个接口同时添加和取消共享 | |
