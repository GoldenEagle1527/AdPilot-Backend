# 契约：list-apps

业务id：theater
文档版本：1
方法：GET
路径：/api/v1/theater/apps
作用：分页列出三方剧场应用。五个筛选都是下拉单选，按创建时间倒序。对应「智能投放/全域模板管理/三方剧场/应用列表」；创建投放广告页面取有效应用也用本接口（传 `is_valid=true`）。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| platform_id | query | integer | 否 | 平台 id，取自 [list-platforms.md](list-platforms.md)：`1` 番茄、`22` 鸥溪。不传=全部 |
| theater_type | query | string | 否 | 剧场类型：`mini_program` 小程序、`native` 端原生。不传=全部 |
| delivery_mode | query | string | 否 | 投放模式：`IAA`、`IAP`。不传=全部 |
| style | query | string | 否 | 剧场风格：`live_action` 真人剧、`manhua` 漫剧。不传=全部 |
| is_valid | query | boolean | 否 | 状态：`true` 有效、`false` 无效。不传=全部 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。应用是全员共用配置，不做数据范围过滤。多传别的 query 参数返回 422。

排序固定 `created_date` 倒序、同秒按 `id` 倒序，不接受排序入参。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | AppItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**AppItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 本库主键（整数自增，JSON 为十进制字符串） |
| platform_id | string | 平台 id（十进制字符串） |
| platform_name | string | 平台名称，如 `番茄` |
| name | string | 剧场名称 |
| theater_type | string | `mini_program` 小程序、`native` 端原生 |
| delivery_mode | string | 投放模式：`IAA`、`IAP` |
| style | string | `live_action` 真人剧、`manhua` 漫剧 |
| ad_source | string | 广告来源名称 |
| is_valid | boolean | 状态：`true` 有效、`false` 无效 |
| created_at | string | 创建时间，北京时间 `+08:00`，精确到秒 |
| updated_at | string | 更新时间，北京时间 `+08:00`，精确到秒 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `delivery_mode: Input should be 'IAA' or 'IAP'` | `page`/`page_size` 越界、枚举值不认识、`is_valid` 非布尔、多传参数 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/应用列表 | 列表与筛选 |
| 创建投放广告 | 取有效应用做下拉（`is_valid=true`） |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
