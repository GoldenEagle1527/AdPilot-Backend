# oc投放-智能投放-标准自动投放策略-（免费）漫剧端原生机器人

# 规则功能说明

| 规则类型 | 这个模板是干什么的 | 巨量接口怎么配合 |
| --- | --- | --- |
| **根据NB的条件自动创建付费批量任务规则** | 按周期检查当前 NB / 最大转化项目，满足“投放时间 + 消耗 + 回收率”条件后，触发内部后续任务；同时限制每部剧使用的新账户数、最大视频素材数和每天执行时间段 | 先通过**项目列表接口**获取当前项目及投放配置，用于识别 NB / 最大转化项目；再通过**自定义报表接口**获取指定时间段的消耗数据；回收率如果来自自己的付费收入，则由内部业务数据计算；需要新账户时通过**工作台账户列表接口**获取可用广告账户。巨量负责“项目、消耗、账户”数据，最终创建任务是内部动作。 |
| **根据剧条件自动创建批量任务规则** | 针对指定剧场，在设定统计时间内检查该剧的消耗和回收率，达到条件后触发内部任务；同时控制每部剧使用的新账户数、最大视频素材数 | “剧场”是自己的业务对象，巨量没有“剧场”字段。先把剧场与巨量广告账户/项目建立映射，再通过**自定义报表接口**按对应 `advertiser_id / project_id` 获取消耗；回收率由业务收入和巨量消耗组合计算；新账户通过**工作台账户列表接口**取得。 |
| **根据推广链自动创建批量任务规则** | 针对指定剧场对应的推广链，按每天/周期检查并触发内部任务，同时限制新账户数和最大视频素材数 | “推广链”不是巨量标准业务对象，以内部推广链 ID 关联巨量 `advertiser_id / project_id / promotion_id`。需要账户池时调用**工作台账户列表接口**；如果需要检查推广链对应的巨量项目，可调用**项目列表接口**获取项目数据。最终任务创建仍是内部系统动作。 |

# 巨量官方API对接

| 功能 | 巨量官方 API | 方法 | 关键入参 |
| --- | --- | --- | --- |
| **获取巨量广告项目，识别 NB / 最大转化项目** | `https://api.oceanengine.com/open_api/v3.0/project/list/` | GET | **必填：**`advertiser_id`。常用可选：`filtering`、`fields`、`page`、`page_size`。接口返回项目列表及项目投放配置，根据项目返回的投放配置字段识别是否属于 NB / 最大转化。巨量官方 SDK 当前明确提供 `ProjectListV30Api`，路径就是 `/open_api/v3.0/project/list/`。 |
| **获取消耗、素材等报表数据** | `https://api.oceanengine.com/open_api/v3.0/report/custom/get/` | GET | **官方确认必填：**`advertiser_id`。实际查询时还需传 `dimensions`、`metrics`；按统计时间传 `start_time`、`end_time`，需要筛项目/广告时传 `filters`。`data_topic` 可使用 `BASIC_DATA`，素材维度可使用 `MATERIAL_DATA`。 |
| **查询当前报表支持哪些指标和维度** | `https://api.oceanengine.com/open_api/v3.0/report/custom/config/get/` | GET | **必填：**`advertiser_id`、`data_topics`。例如 `BASIC_DATA` 查询基础投放指标，`MATERIAL_DATA` 查询素材数据。用于确认“消耗”等指标在当前账户是否可直接查询。 |
| **获取可使用的新广告账户** | `https://api.oceanengine.com/open_api/2/ebp/advertiser/list/` | GET | **必填：**`enterprise_organization_id`、`account_source`。你们这里是巨量广告业务，`account_source = AD`。接口用于获取升级版巨量引擎工作台下可以使用的广告账户列表。 |
| **查询视频/素材资源** | `https://api.oceanengine.com/open_api/2/file/material/list/` | GET | 公开资料核心必填包含 `advertiser_id`、`material_source`。用于获取素材资源信息；“每部剧最大视频素材数”可通过内部剧场/推广链和素材的映射关系控制，不建议直接把这个数量当成巨量接口限制。 |

**剧场、推广链、每部剧新账户数、最大素材数、周期、每天执行时间，全部是中台规则；巨量 API 只负责提供账户、项目、消耗、素材等基础数据。满足规则后，再由内部系统创建对应任务。**