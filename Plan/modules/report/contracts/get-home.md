# 契约：get-home

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/home
作用：首页五张卡和一条曲线。只读已有快照，不调巨量。登录只要 Bearer，不查菜单。

作者：
状态：draft
更新日期：2026-10-14

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | Bearer。不查菜单 |
| surface | query | string | 是 | `manhua`、`uni_drama`、`uni_pitcher_drama`、`uni_pitcher`、`uni_group` |
| charge_mode | query | string | 条件 | 仅 `manhua` 必填，`IAA` 或 `IAP`。另外四个表面禁止带，否则 422。两套分开合计，自选字段共用 |
| date_start | query | string | 否 | `YYYY-MM-DD`，北京时间，含当天。与 `date_end` 成对。都没有表示不选时间。不要缺省成今天 |
| date_end | query | string | 否 | 同上 |
| user_ids | query | integer[] | 否 | 投手用户 id，多选。空表示不筛账户 |
| department_ids | query | integer[] | 否 | 部门 id，多选。只算该部门自己的人（`users.department_id`，`is_deleted = 0`），不含下级，不按 `enabled` 再砍。与 `user_ids` 取并集 |
| curve | query | string | 否 | 本次曲线的键，必须是当前五张卡的键之一，否则 422。不落库。缺省是展示数 |

可见范围：

- 不筛账户时，与对应列表同一批可见行。负责人看全部，判定与报表 `_viewer_id` 相同。漫剧、短剧收益、投手短剧、投手报表：其余人只留自己在投手里的行。漫剧和短剧收益用剧目行，行内仍是该行全部投手的合计。组报表部门用数据范围，为空则自己所在部门，读 `report_uni_group_day`。
- 筛了账户后先和可见范围取交。非负责人在前四个表面上只剩自己，交完为空则五张卡为 0、曲线无点，不退回全部。组报表只留当前部门仍在可见部门里的人。然后只计这些投手自己的数：漫剧读 `report_manhua_promotion_day`（同一 `charge_mode`）；短剧收益和投手短剧读 `report_uni_pitcher_drama_day`；投手报表和组报表读 `report_uni_pitcher_day`。筛过的组报表不再读 `report_uni_group_day`。

## 响应

`data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| surface | string | 入参 |
| charge_mode | string 或 null | 漫剧为 `IAA`/`IAP`，其余 null |
| grain | string | `hour` 或 `day` |
| cards | array | 永远 5 个，顺序固定：展示数、点击率、三个自选 |
| curve | object | `key`、`grain`、`points` |

`cards[]`：`key`、`value`。

展示数：漫剧 `show_cnt`，全域 `all_show_cnt_trend`。点击率键是 `ctr`：点击 / 展示 × 100，两位小数；展示为 0 则为 0。全域点击 `all_click_cnt_trend` 只参与点击率，不能被选进三个自选。漫剧的 `show_cnt` 和 `ctr` 可以再被选进三个。

从没存过时，漫剧三个是 `stat_cost`、`click_cnt`、`convert_cnt`；全域四个表面是 `all_stat_cost_trend`、`all_gmv_trend`、`all_roi_trend`。GET 不把缺省写入。换账号不共用。漫剧 IAA/IAP 共用这一套。

可选集：漫剧是剧目数值字段全部（`ManhuaMetrics`）再加 `promotion_with_cost_count`。全域短剧、投手短剧是 `UniMetrics` 全部。投手报表、组报表再加 `new_drama_count`。固定为 0 的列仍可选，值就是 0。

其它比率用该桶合计后的分子分母，调用现有 `manhua_metrics`、`uni_metrics`。不选账户的漫剧合计先 `fold_manhua_dramas` 再 `manhua_summary`。`promotion_with_cost_count` 在筛了投手时是该桶内 `stat_cost > 0` 的计划去重数。

曲线：只选一个自然日时 `grain = hour`，读小时快照，点为 `{hour, value}`，小时是 `stat_time_hour` 里已是北京时间的钟点。没有快照的小时不出现。跨两天及以上，或不选时间：`grain = day`，读上面的日表，点为 `{date, value}`。没有日行的日期不出现。整段没有行则 `points` 为 `[]`。不补 0。不选时间的卡片是这些有行日期的合计。单日的卡片按同一可见范围和账户规则从小时快照聚合，不读日表。小时上的 `new_project_count` 只计创建时间落在该小时的任务。两个小时的点击率不相加再平均。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 表面、收费模式、日期只传一个、开始晚于结束、曲线不在五张卡里 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 首页 | 五张卡和一条曲线 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-14 | 1 | 否 | 初稿 | |
