# 契约：batch-public-videos

业务id：material
文档版本：1
方法：POST
路径：/api/v1/material/videos/batch-public
作用：把自己上传的多条视频素材一次改成公有。有一条对不上就整批不改。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| video_ids | body | integer[] | 是 | 要转公有的视频素材 id。至少 1 个，不得重复 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。只能改自己上传且未删除的。

已经是公有的再提交一次，仍然成功，归属保持 `public`。

别人的、已软删的、或不存在的，整批返回 404，已经对得上的也不改。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| ids | string[] | 改过的素材 id，顺序与传入的 `video_ids` 一致 |
| ownership | string | 恒为 `public` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `video_ids: 视频不能重复` | 空数组、重复 id、缺字段、多传字段 |
| 404 | `视频素材不存在：9` | 有素材不存在、已软删、或不是自己上传的 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 勾选后「转公有」 |

## 明确不做

- 批量改回私有（单条改公有或私有见 [change-video-ownership.md](change-video-ownership.md)）

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 1 | 否 | 说明：单条改归属另开 change-video-ownership | |
| 2026-09-24 | 1 | 否 | 初稿 | |
