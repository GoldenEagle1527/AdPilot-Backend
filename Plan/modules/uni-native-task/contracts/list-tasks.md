# 契约：list-tasks

业务id：uni-native-task
文档版本：5
方法：GET
路径：/api/v1/uni-native-tasks
作用：分页列出当前登录投手自己的端原生投放任务。执行中和完成可以按本任务的巨量项目 id 查看项目；失败不返回这些编号。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |
| date_start | query | string | 否 | 创建日期起，`YYYY-MM-DD`，含当天，北京时间 |
| date_end | query | string | 否 | 创建日期止，`YYYY-MM-DD`，含当天，北京时间。不能早于 `date_start` |
| series_name | query | string | 否 | 剧名，模糊。短剧表不在当前库时，带了剧名就返回空页 |

只返回 `pitcher_user_id` 为当前用户、且未软删的任务。

## 响应

`data` 为分页：`list` / `total` / `page` / `page_size`。`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 任务 id |
| template_id | string | 全域模板 id |
| template_name | string | 模板名称 |
| project_budget | string | 任务上的项目预算，两位小数。保存时从模板抄来，可被覆盖 |
| roi_coefficient | string | 任务上的 ROI 系数，三位小数 |
| pitcher_user_id | string | 创建任务的投手 |
| series_id | string | `manhua_series.id` |
| book_name | string | 剧名。短剧表不在时为空串 |
| series_short_name | string | 剧名前两个字。不足两个字用原名 |
| theater_name | string | 剧场名。取这条任务所选全域模板上的投放主体里单选的剧场，不是短剧自己的编号。剧名下面那行编号不返回 |
| accounts | array | 抖音号与账户，见下表。顺序与保存时一致 |
| ocean_project_ids | integer[] | 本任务各账户的巨量项目 id，顺序与 `accounts` 一致。`running`、`done` 才有数；`saved`、`failed` 以及迁移后的旧任务为 `[]`。不是按短剧打开全域项目整页 |
| promotion_links | array | 推广链文本，见下表 |
| videos | array | `{ "id", "name" }`。视频表不在时为 `[]` |
| titles | array | `{ "id", "title" }`，来自标题库。标题库不在时为 `[]` |
| batch_titles | array of string | 临时标题。不在标题库里 |
| status | string | `saved` 仅机器人落库到提交之间的短暂状态。`running` 执行中，`done` 完成（假客户端结束），`failed` 失败 |
| failure_reason | string or null | 失败原因。成功为空 |
| materials_uploaded | boolean | 素材是否已通过客户端上传完成 |
| executed_at | string or null | `done` 时为假客户端结束的北京时间，否则 null |
| created_at | string | 北京时间，精确到秒 |
| updated_at | string | 北京时间，精确到秒 |

`accounts` 每一项：`douyin_account_id`、`aweme_id`、`douyin_name`、`advertiser_account_id`、`advertiser_id`、`name`、`ocean_project_id`。前四个 id 除 `advertiser_id` 外都是字符串；`advertiser_id` 是巨量广告主 id。`ocean_project_id` 是巨量项目 id（整数或 null），不是账户表自增主键。`running`、`done` 返回该账户上的编号；`failed` 和未创建时为 null，即使库里已经记下编号，也不当作可点的「查看项目」数据。

`promotion_links` 每一项：`charge_mode`（`IAA` 或 `IAP`）、`link_text`、`recharge_template_name`（档位名。自动带出时是剧场 `recharge_template_name`；手填没传则为空串）。

空结果是 `list: []` 且 `total: 0`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 422 | `日期段起不能晚于止` | 起日晚于止日，或多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 列表。执行中和完成可查看本任务建出的项目 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 5 | 否 | 增加 `theater_name`，取模板上投放主体的剧场名。不返回剧名下面的编号 | |
| 2026-10-12 | 4 | 否 | 推广链增加档位名 `recharge_template_name`。没有则为空串 | |
| 2026-10-12 | 3 | 否 | 增加 `ocean_project_id`、`ocean_project_ids`。`running`、`done` 返回巨量项目 id；`failed` 和未创建返回空。状态补 `failed`、`failure_reason` | |
| 2026-10-09 | 2 | 否 | 目录已记版本 2，与提交后的 `running`、`done` 对齐 | |
| 2026-09-30 | 1 | 否 | 初稿 | |
