# 巨量广告广告列表

`GET /api/v1/ocean-ads/promotions`

要有菜单 34。只返回当前登录人数据范围内的广告。传入的 `account_id` 对不上时，这一页是空的。

`promotion_name` 是下拉选中的广告全名，精确匹配 `oe_promotion.name`。下拉选项是 `GET /api/v1/ocean-ads/promotion-names`。产品说广告名称不重复，一个名称对应一条广告。

`promotion_link` 是完整推广链接，精确匹配 `oe_promotion.promotion_links` 里的某一条。创建广告时从报文 `promotion_materials.playlet_series_url_list` 抄下来。

`series_name` 模糊匹配 `manhua_series.book_name`。列表里的短剧名称是 `book_name`，短剧 id 是 `manhua_series.book_id`。广告上的 `oe_promotion.series_id` 指向 `manhua_series.id`，创建广告时从任务上的 `series_id` 抄下来。

列表里的项目名称是 `oe_project.name`，项目 id 是 `oe_project.ocean_project_id`，广告 id 是 `oe_promotion.promotion_id`。

返回的 `promotion_id`、`project_id`、`book_id`、`account_id` 是字符串。巨量的 id 有 19 位，超出 JS 数字能精确表示的范围。查询参数照旧。

收益和比率从素材小时表加总后按稿子计算。除数是 0 时比率是 0.00。`budget` 是 `oe_promotion.budget`，创建广告时从报文 `budget` 抄下，没有则为空。`reject_reasons` 是当前页向 `GET /open_api/v3.0/promotion/reject_reason/get/` 要到的拒绝原因。查到了但没有原因是空数组。这一批接口失败时是 `-`。

## 变更历史

| 日期 | 版本 | 破坏？ | 改了什么 | 谁 |
|------|------|--------|----------|----|
| 2026-10-14 | 2 | 是 | 返回的 `promotion_id`、`project_id`、`book_id`、`account_id` 从数字改成字符串。旧版见 `_history/list-promotions-v1.md` | 李伟峰 |
