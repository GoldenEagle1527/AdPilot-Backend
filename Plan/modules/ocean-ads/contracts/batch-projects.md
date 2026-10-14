# 巨量广告项目批量改状态

`POST /api/v1/ocean-ads/projects/batch`

要有菜单 33。只改当前登录人数据范围内、还没删除的项目。看不了的项目 id 不报错，也不出现在返回里。传 1 个项目 id 就是列表上的单个开关，传多个就是批量。

正文：

- `project_ids`：项目 id，即 `oe_project.ocean_project_id`，1 到 100 个
- `action`：`开启`、`暂停`、`删除`

开启、暂停会通知巨量：

- 项目：`POST /open_api/v3.0/project/status/update/`，`opt_status` 为 `ENABLE` 或 `DISABLE`，一次最多 10 条
- 该项目下未删除的广告：`POST /open_api/v3.0/promotion/status/update/`，同样一次最多 10 条

巨量返回成功的才改本库 `opt_status`。有失败项时，成功的已写入，接口返回 502。

删除也通知巨量，本库仍是软删除。产品 2026-10-13 确认开启、暂停、删除都要通知巨量。单个开关和批量同一种做法。

- 项目：`POST /open_api/v3.0/project/delete/`，`project_ids` 一次最多 10 个
- 该项目下未删除的广告：`POST /open_api/v3.0/promotion/delete/`，`promotion_ids` 一次最多 10 个

巨量返回成功的，`oe_project`、`oe_promotion` 的 `is_deleted` 写成 1，`deleted_at` 记下时间。有失败项时，成功的已写入，接口返回 502。

返回 `project_ids` 和 `promotion_count`。

`project_ids` 正文里传字符串或数字都接受，19 位的巨量 id 要传字符串才不丢位。返回的 `project_ids` 是字符串数组。

## 变更历史

| 日期 | 版本 | 破坏？ | 改了什么 | 谁 |
|------|------|--------|----------|----|
| 2026-10-14 | 2 | 是 | 正文 `project_ids` 可传字符串。返回的 `project_ids` 从数字改成字符串。旧版见 `_history/batch-projects-v1.md` | 李伟峰 |
