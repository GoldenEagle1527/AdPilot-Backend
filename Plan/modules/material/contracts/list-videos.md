# 契约：list-videos

业务id：material
文档版本：2
方法：GET
路径：/api/v1/material/videos
作用：分页列出当前登录用户能看见的视频素材。公有都能看；私有只有创建者和被分配的投手能看。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| tag_id | query | integer | 否 | 视频标签 id。下拉单选后的精确值，选项来自 [list-video-tags.md](list-video-tags.md) |
| name | query | string | 否 | 视频名称，模糊。`%` 和 `_` 按字面量处理。对应添加页自动生成的名称 |
| id | query | integer | 否 | 视频 id，精确 |
| series_id | query | integer | 否 | 短剧 id。下拉单选后的精确值 |
| pitcher_id | query | integer | 否 | 归属投手用户 id。下拉单选后的精确值，匹配添加页配置的投手 |
| uploader_id | query | integer | 否 | 上传者用户 id。下拉单选后的精确值 |
| file_name | query | string | 否 | 上传文件名，对素材文件地址做模糊匹配 |
| ownership | query | string | 否 | 归属：`public` 公有、`private` 私有。不传为全部 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

可见范围先于筛选：公有素材当前用户都能看到；私有素材只有 `uploader_id` 是自己，或 `material_video_pitchers` 里有自己，才能看到。`ownership` 不传时两种都查，仍受这个范围限制。

下拉的模糊搜索在选项接口完成。本接口收到的是选中后的精确 id。名称和文件名在这里模糊。

排序固定 `created_date` 倒序、同秒按 `id` 倒序。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | VideoItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**VideoItem** 与 [create-videos.md](create-videos.md) 出参相同。昵称或短剧名查不到时为空串，不因此 404。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `ownership: Input should be 'public' or 'private'` | 归属不在枚举、页码不合法、多传字段 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 2 | 是 | 查询条件 `tag`（标签文案）改为 `tag_id`（标签表主键） | |
| 2026-09-24 | 1 | 否 | 初稿 | |
