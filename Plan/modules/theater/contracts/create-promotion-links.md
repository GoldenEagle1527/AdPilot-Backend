# 契约：create-promotion-links

业务id：theater
文档版本：3
方法：POST
路径：/api/v1/theater/promotion-links
作用：投手人工新增端原生推广链。系统调接口没拿到链时，从常读后台复制 URL，按档位一次可填最多五条；每个非空档位落一行。对应「三方剧场/端原生推广链」新增弹窗。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| series_id | body | integer | 是 | 剧名，漫剧流转剧库主键。下拉搜索选项取漫剧库列表接口 |
| iaa | body | string | 否 | IAA 推广链，去首尾空白，1–2048 字；空或不传表示本档不建 |
| medium | body | string | 否 | 中额推广链，同上 |
| small | body | string | 否 | 小额推广链，同上 |
| extra_small | body | string | 否 | 超小额推广链，同上 |
| ultra_small | body | string | 否 | 超超小额推广链，同上 |

五个档位至少填一个非空 URL。空白串按未填处理。多传字段（含 `theater_app_id`）返回 422。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

落库约定（调用方不传）：

| 列 | 值 |
| --- | --- |
| source | `manual` |
| promotion_id | null |
| task_id | null |
| theater_app_id | 按档位自动挂：`IAA`→应用表 `delivery_mode=IAA` 第一条有效应用；其余档位→`IAP` 第一条。对应不上为空 |
| is_enabled | `true` |
| recharge_template_name | 对应档位名：`IAA` / `中额` / `小额` / `超小额` / `超超小额` |
| media_config_type | IAA 为 `3`，其余档为 `2` |
| publish_time | 短剧 `estimate_publish_time`，没有则为 null |
| promotion_create_time | 本次写入时的北京时间 |

「第一条」：未删除且有效，按 `id` 升序。业务上 IAA/IAP 各一条；若有多条取 id 最小。

示例：

```json
{
  "series_id": 8,
  "iaa": "https://example.com/iaa",
  "medium": "https://example.com/mid",
  "small": "",
  "extra_small": null,
  "ultra_small": "https://example.com/ultra"
}
```

上例落三行：IAA、中额、超超小额。

并发：

1. 写入前对该短剧行 `FOR UPDATE`，人工与定时落库串行。
2. 同剧同 URL、同剧同档位（`recharge_template_name`）已存在则跳过；定时落链同样规则，不覆盖人工。
3. 该剧有 `running` 同步任务时，人工新增返回 409（调常读期间不持锁，避免两边各插一条）。
4. 人工新增成功后，同剧 `pending`/`queued` 任务标为失败（原因「已人工新增推广链」），避免稍后定时再落。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | PromotionLinkItem[] | 本次新建的行，顺序与档位固定顺序一致（IAA → 中额 → 小额 → 超小额 → 超超小额，跳过未填） |

PromotionLinkItem 字段同 [list-promotion-links.md](list-promotion-links.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `短剧不存在` | `series_id` 不存在或已删除 |
| 409 | `该短剧正在同步推广链，请稍后再试` | 同剧有爬虫处理中的同步任务 |
| 409 | `推广链已存在` | 填的 URL/档位在该剧下都已有，一条都没新建 |
| 422 | `Value error, 至少填写一条推广链` | 五个档位都空 |
| 422 | `body.iaa: String should have at most 2048 characters` | URL 超长 |
| 422 | `body.foo: Extra inputs are not permitted` | 多传字段 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/端原生推广链 | 「新增」弹窗提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 3 | 是 | 去掉入参 `theater_app_id`，按档位 IAA/IAP 自动挂应用 | |
| 2026-09-29 | 2 | 是 | 入参必填 `theater_app_id` | |
| 2026-09-29 | 1 | 否 | 初稿 | |
