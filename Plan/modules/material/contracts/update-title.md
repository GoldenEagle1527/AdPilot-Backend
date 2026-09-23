# 契约：update-title

业务id：material
文档版本：1
方法：PATCH
路径：/api/v1/material/titles/{title_id}
作用：改一条素材标题。**只准改标题名和分类**，且只能改自己上传的那条。对应列表行的「修改标题」弹窗。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| title_id | path | integer | 是 | 标题主键 |
| title | body | string | 是 | 标题名称，去首尾空白，1–512 字 |
| category | body | string | 是 | `paid` 付费标题、`common` 通用标题 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调；能改哪条由「只能是自己上传的」决定。

body 只收这两个字段，多传别的（如 `uploader_id`、`created_at`）返回 422。上传者和上传时间不可改。

别人上传的标题按**不存在**处理，返回 404，不区分「无权」以免泄露存在性。

## 响应

改后的整条记录，字段同 [list-titles.md](list-titles.md) 的 **TitleItem**。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `title: String should have at most 512 characters` | 标题名为空白或超 512 字、分类不是 `paid`/`common`、body 多带字段 |
| 404 | `标题不存在` | 标题不存在、已软删、或不是自己上传的 |
| 409 | `标题已存在` | 自己在目标分类下已有同名标题（不含本条） |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/标题 | 行按钮「修改标题」弹窗「素材标题编辑」 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
