# 契约：list-titles

业务id：material
文档版本：1
方法：GET
路径：/api/v1/material/titles
作用：分页列出**当前登录用户自己上传**的素材标题。按分类单选、标题名模糊筛选，按上传时间倒序。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| category | query | string | 否 | 下拉单选：`paid` 付费标题、`common` 通用标题。不传=全部 |
| title | query | string | 否 | 标题名称，模糊。`%` 和 `_` 按字面量处理 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调；能看到什么由数据范围决定。

**数据范围恒为本人**：没有 `uploader_id` 入参，后端一律按 Token 里的用户过滤，别人上传的标题查不到。列表里的「上传者」列因此恒为自己。

排序固定 `created_date` 倒序、同秒按 `id` 倒序，不接受排序入参。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | TitleItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**TitleItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 本库主键（整数自增，JSON 为十进制字符串） |
| title | string | 标题名称 |
| category | string | `paid` 付费标题、`common` 通用标题 |
| uploader_id | string | 上传者用户 id，恒为当前登录用户 |
| uploader_nickname | string | 上传者昵称，用户已删则为空串 |
| created_at | string | 上传时间，北京时间 `+08:00` |

前端列表里的「标题总消耗」本轮不出：没有投放数据源，表上也没建列。

## 错误

无本接口特有错误。共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/标题 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
