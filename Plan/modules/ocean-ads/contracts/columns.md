# 巨量广告自定义列

存在服务端，不存在浏览器。表是 `user_menu_configs`：一行是一个用户、一个菜单、一份 JSON。不使用 `role_menus`。菜单用 `menu_nodes.id`，现在是整数，不另造 UUID。

勾选和顺序放在配置的 `columns` 里。这个用户在这个菜单上有配置，就按他的返回。没有配置，返回该菜单的默认列和默认顺序。点表头的正序倒序仍走各列表自己的 `sort_by`、`sort_order`，不写进配置。

`menu_id` 只接受有自定义列的菜单：32 账户、33 项目、34 广告、35 素材。调用人必须有这个菜单。全域项目 37 和全部广告 36 不在这里。

## 读取

`GET /api/v1/ocean-ads/columns?menu_id=`

返回 `menu_id` 和 `columns`。`columns` 是列名，按展示顺序。

## 保存

`PUT /api/v1/ocean-ads/columns`

正文 `menu_id` 和 `columns`。`columns` 至少 1 个，不能重复，列名必须属于该菜单。整份替换这一用户这一菜单的 `columns`，不是追加。

默认列：

- 32：`account_name`、`account_id`、`balance`、`stat_cost`、`revenue_today`、`revenue_total`、`revenue_today_rate`、`revenue_total_rate`、`show_cnt`、`cpm`、`click_cnt`、`ctr`、`cpc`
- 33：`project_name`、`project_id`、`project_status`、`show_cnt`、`cpm`、`stat_cost`、`click_cnt`、`ctr`、`account_name`、`budget`、`revenue_today`、`revenue_total`、`revenue_today_rate`、`revenue_total_rate`、`convert_cnt`、`convert_cost`、`convert_rate`、`active`、`recycle_amount`、`active_arpu`、`active_cost`、`cpc`、`promotion_links`、`account_id`
- 34：`promotion_name`、`promotion_id`、`promotion_status`、`stat_cost`、`revenue_today`、`revenue_total`、`revenue_today_rate`、`revenue_total_rate`、`show_cnt`、`cpm`、`click_cnt`、`ctr`、`cpc`、`convert_cnt`、`convert_rate`、`budget`、`account_name`、`convert_cost`、`active`、`active_cost`、`recycle_amount`、`active_arpu`、`project_name`、`project_id`、`series_name`、`promotion_links`、`book_id`、`account_id`
- 35：`material_id`、`material_name`、`stat_cost`、`convert_cnt`、`convert_cost`、`show_cnt`、`click_cnt`、`ctr`、`cpc`、`convert_rate`、`promotion_id`、`promotion_name`、`project_id`、`project_name`、`account_id`、`account_name`
