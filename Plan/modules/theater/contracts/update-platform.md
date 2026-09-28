# 契约：update-platform

业务id：theater
文档版本：1
方法：PATCH
路径：/api/v1/theater/platforms/{platform_id}
作用：改一个平台的启用状态、小程序和端原生开关。**平台名称、平台码不可改**，平台也不能新建或删除。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| platform_id | path | integer | 是 | 平台 id：`1` 番茄、`22` 鸥溪 |
| is_enabled | body | boolean | 否 | 启用状态：`true` 启用、`false` 禁用 |
| supports_mini_program | body | boolean | 否 | 是否支持小程序 |
| supports_native | body | boolean | 否 | 是否支持端原生 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

三个字段**至少传一个**，不传或传 `null` 的字段保持原值。一个都没给（或全是 `null`）返回 422。

body 只收这三个字段，多传别的（如 `name`、`code`、`sort_order`）返回 422。

示例：

```json
{ "is_enabled": false }
```

## 响应

改后的整条记录，字段同 [list-platforms.md](list-platforms.md) 的 **PlatformItem**。`updated_at` 为改后的时间。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `Value error, 至少修改一项` | body 为空或三个字段全为 `null` |
| 422 | `name: Extra inputs are not permitted` | body 多带字段 |
| 404 | `平台不存在` | 平台 id 不存在或已软删 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/平台列表 | 行内切换启用状态、勾选小程序/端原生 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
