# 契约：list-video-tags

业务id：material
文档版本：1
方法：GET
路径：/api/v1/material/video-tags
作用：分页列出当前登录用户能看见的视频素材用过的标签，供下拉模糊选择。

作者：
状态：draft
更新日期：2026-09-24

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| name | query | string | 否 | 标签名，模糊。`%` 和 `_` 按字面量处理。对应添加页传入的标签，如 `甲剧0923` |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

只返回未删除、且至少被一条当前用户能看见的素材引用的标签。可见范围与 [list-videos.md](list-videos.md) 相同：公有都能看；私有只有创建者和被分配的投手能看。

排序固定 `name` 升序、同名按 `id` 升序。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | TagItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**TagItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 标签主键（整数自增，JSON 为十进制字符串）。选中后作为 list-videos 的 `tag_id` |
| name | string | 标签文案 |

## 错误

无本接口特有错误。共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/视频 | 标签下拉 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-24 | 1 | 否 | 初稿 | |
