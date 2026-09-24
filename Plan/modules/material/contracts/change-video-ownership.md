# 契约：change-video-ownership

业务id：material
文档版本：1
方法：POST
路径：/api/v1/material/videos/{video_id}/ownership
作用：把自己上传的一条视频素材改成公有或私有。共享和投手归属不动。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| video_id | path | integer | 是 | 视频素材主键 |
| ownership | body | string | 是 | `public` 公有、`private` 私有 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。只有上传者能调。

已经是目标归属再提交一次，仍然成功。不改共享行，不改投手归属行。

别人上传的、已软删的、或不存在的，返回 404，不区分「无权」。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 素材 id |
| ownership | string | 改后的归属，`public` 或 `private` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `ownership: Input should be 'public' or 'private'` | 归属不是这两个值、缺字段、多传字段 |
| 422 | `video_id: Input should be a valid integer` | 路径不是整数 |
| 404 | `视频素材不存在` | 素材不存在、已软删、或不是自己上传的 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 行上把这一条改成公有或私有 |

## 明确不做

- 批量改回私有（批量只提供转公有）

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 1 | 否 | 初稿 | |
