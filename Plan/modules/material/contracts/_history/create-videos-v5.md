# 契约：create-videos

业务id：material
文档版本：5
方法：POST
路径：/api/v1/material/videos
作用：添加一条视频素材。素材名称后缀由后端按当日日期生成，标签名由前端传入，上传者取当前登录用户，上传时间取落库时间。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| name | body | string | 是 | 素材名称。去首尾空白，1–480 字；落库时拼当日日期后缀，如 `甲` 存成 `甲_20260923` |
| material_type | body | string | 是 | 素材类型：`vertical_video` 竖版视频、`horizontal_video` 横版视频、`horizontal_image` 大图横图、`small_image` 小图、`vertical_image` 大图竖图 |
| file_urls | body | string[] | 是 | 素材文件 url 数组。每条 http/https 开头，≤1024 字；一次 1–50 个 |
| series_id | body | integer | 是 | 短剧。取 [list-manhua-series.md](list-manhua-series.md) 列表里的 `id` |
| platform | body | string | 否 | 投放平台，暂时只有 `tomato` 番茄；不传默认 `tomato` |
| tag | body | string | 是 | 标签名。去首尾空白，1–600 字，原样落库，如 `甲剧0923`。同一文案共用 `material_video_tags` 一行 |
| ownership | body | string | 是 | 归属：`public` 公有、`private` 私有 |
| pitcher_ids | body | integer[] | 是 | 分配的投手用户 id。可空，一次最多 50 个；**不得重复**，重复返回 422，后端不去重。公有、私有都可以传，也可以是空数组。公有时这列不决定谁能看见；私有时这些投手和创建者能看见 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

视频文件先经 [upload-file.md](../../file/contracts/upload-file.md) 转到对象存储，本接口只收返回的 url，不收 multipart。素材名称的日期后缀不收入参：落库时拼当日 `YYYYMMDD`，按北京时间生成。标签名用入参 `tag`，原样落库。

## 响应

`data` 为新增的那一条：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 素材 id |
| name | string | 已拼好日期后缀的素材名称 |
| material_type | string | 素材类型，取值同请求 |
| file_urls | string[] | 素材文件 url 数组，按传入顺序 |
| series_id | string | 短剧 id |
| book_name | string | 短剧名称，落库时按 `series_id` 回填 |
| platform | string | 投放平台 |
| tag | string | 前端传入的标签名 |
| ownership | string | 归属 |
| pitchers | object[] | 分配的投手，按传入顺序，可为空数组。每项 `{ id, nickname }` |
| uploader_id | string | 上传者用户 id |
| uploader_nickname | string | 上传者昵称 |
| created_at | string | 上传时间，北京时间 ISO-8601 带 `+08:00` |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `file_urls: String should match pattern '^https?://'` | 文件 url 不是 http/https、文件数组为空或超 50、标签名为空或超 600 字、素材类型不在枚举、多传字段等入参不合规 |
| 422 | `pitcher_ids: 投手不能重复` | 同一次提交里投手 id 重复 |
| 404 | `短剧不存在` | `series_id` 在漫剧库里查不到 |
| 404 | `用户不存在：9` | `pitcher_ids` 里有用户查不到，或当前登录用户已被删，报出缺的 id |

出参里的昵称一律是查到的真值，不会为空串：查不到任何一个相关用户就整条不写、直接 404。

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 「添加视频素材」 |

## 明确不做

- 视频封面、第一帧抽取（后端不引转码，封面由前端截帧后另行提交）
- 头条素材 id、自动转码与转码时间
- 手动添加自建短剧（只能从常读漫剧库里选）
- 素材共享、绑定计划数 / 消耗计划数等投放侧字段

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 5 | 是 | 新增必填 `tag`。标签名由前端传入并原样落库，不再按短剧名加月日生成 | |
| 2026-09-24 | 4 | 否 | 投手改记关联表。`pitcher_ids` 允许空数组；公有不靠名单决定可见，私有为创建者加被分配的投手 | |
| 2026-09-24 | 3 | 否 | 文件改为先走 `POST /api/v1/files/upload`，本接口仍只收 url | |
| 2026-09-23 | 2 | 否 | 去掉两处兜底：投手重复不再静默去重改 422；昵称查不到不再回空串，缺用户直接 404（message 由「投手不存在」改「用户不存在」） | |
| 2026-09-23 | 1 | 否 | 初稿 | |
