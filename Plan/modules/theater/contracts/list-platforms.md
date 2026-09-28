# 契约：list-platforms

业务id：theater
文档版本：1
方法：GET
路径：/api/v1/theater/platforms
作用：分页列出三方剧场平台。按平台名称模糊、启用状态单选筛选，按排序升序。对应「智能投放/全域模板管理/三方剧场/平台列表」。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| name | query | string | 否 | 平台名称，模糊。去首尾空白，空串当不传；`%` 和 `_` 按字面量处理。不传=全部 |
| is_enabled | query | boolean | 否 | 启用状态下拉单选：`true` 启用、`false` 禁用。不传=全部 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。平台是全员共用配置，不做数据范围过滤。多传别的 query 参数返回 422。

平台不开放新建，库里固定两条：番茄（id `1`、平台码 `1011`）、鸥溪（id `22`、平台码 `4504`），默认都启用、都支持端原生、都不支持小程序。

排序固定 `sort_order` 升序、同序按 `id` 升序，不接受排序入参。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | PlatformItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**PlatformItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 平台 id（十进制字符串），番茄 `"1"`、鸥溪 `"22"` |
| name | string | 平台名称 |
| code | string | 平台码，番茄 `"1011"`、鸥溪 `"4504"` |
| sort_order | integer | 排序，越小越靠前 |
| is_enabled | boolean | 启用状态：`true` 启用、`false` 禁用 |
| supports_mini_program | boolean | 「小程序」勾选。勾上后，其它页面选小程序时能用这个平台 |
| supports_native | boolean | 「端原生」勾选。勾上后，其它页面选端原生时能用这个平台 |
| created_at | string | 创建时间，北京时间 `+08:00`，精确到秒 |
| updated_at | string | 更新时间，北京时间 `+08:00`，精确到秒 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `is_enabled: Input should be a valid boolean` | `page`/`page_size` 越界、`is_enabled` 非布尔、多传参数 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/平台列表 | 列表与筛选 |
| 三方剧场/应用列表 | 新增应用时的平台下拉（取启用的） |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
