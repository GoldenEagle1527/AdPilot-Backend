# 契约：upload-image

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/images
作用：上传产品主图。只收本地文件，概念上是 `UPLOAD_BY_FILE`。

作者：
状态：draft
更新日期：2026-10-08

## 请求

`multipart/form-data`。不收图片 URL。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `32` |
| advertiser_id | form | int | 是 | 广告账户 |
| image_file | form | file | 是 | 本地图片文件。空文件 400 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_id | int | 原样 |
| image_id | string | 假客户端返回 `img-` 加十六进制。不是视频的 `local-` 号 |

信封与其它接口相同：`{"code": 200, "message": "成功", "data": ...}`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 32 | 403 | |
| 文件为空 | 400 | `图片文件为空` |
| 返回的 id 空着或像视频 `local-` | 502 | `图片 id 无效` |
| 真客户端 | 503 | `图片上传接口未定`。不发起开放平台请求 |
| 未装客户端或未配 secret | 503 | `巨量未配置` |

## 业务规则

- 不提供 URL 上传。
- 假路径不落图片表，只把 `image_id` 交还给确认提交。
- 主图 id 不要拿视频上传的 `local-{hex}` 去填。

## 被谁调用

确认提交组 `product_info.image_ids` 之前，先拿这里的 `image_id`。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 1 | 否 | 初稿 | |
