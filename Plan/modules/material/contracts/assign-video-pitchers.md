# 契约：assign-video-pitchers

业务id：material
文档版本：3
方法：POST
路径：/api/v1/material/videos/{video_id}/pitchers
作用：上传者或仍在共享里的人，提交自己分出去的投手完整名单。名单里没有的取消，别人分的同一投手不动。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| video_id | path | integer | 是 | 视频素材主键 |
| user_ids | body | integer[] | 是 | 当前操作人分出去的投手完整名单。一次最多 50 个，不得重复。已在名单里的不动，名单里没有的取消，取消过又出现的恢复。空数组表示这个人分的投手全部取消。不影响别人分的投手 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。能操作的人是上传者，或 `material_video_shares` 里还没被取消的那个人。其他人按素材不存在处理。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 素材 id |
| added | object[] | 这次真正新分或恢复的投手，按传入顺序。每项 `{ id, nickname }` |
| removed | object[] | 这次真正取消的投手，按传入顺序。每项 `{ id, nickname }` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `user_ids: 投手不能重复` | 名单重复、超过 50 个、缺字段、多传字段 |
| 404 | `视频素材不存在` | 素材不存在、已软删，或当前用户不是上传者、也不在共享里 |
| 404 | `用户不存在：9` | `user_ids` 里有用户查不到，报出缺的 id |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 共享人添加或取消投手 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 3 | 是 | `add_user_ids` / `remove_user_ids` 收成当前操作人的完整名单 `user_ids`。快照 [_history/assign-video-pitchers-v2.md](_history/assign-video-pitchers-v2.md) | |
| 2026-09-24 | 2 | 是 | 同一接口同时添加和取消。`pitcher_ids` 改为 `add_user_ids`，新增 `remove_user_ids`。出参改为 `added` / `removed`。快照 [_history/assign-video-pitchers-v1.md](_history/assign-video-pitchers-v1.md) | |
| 2026-09-24 | 1 | 否 | 初稿 | |
