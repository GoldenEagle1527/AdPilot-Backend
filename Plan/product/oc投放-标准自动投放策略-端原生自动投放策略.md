# oc投放-标准自动投放策略-端原生自动投放策略

# 规则功能与巨量接口配合

| 规则类型 | 这个模板是干什么的 | 巨量接口怎么配合 |
| --- | --- | --- |
| **自动关闭广告规则** | 根据最近投放时间、竞价策略、消耗、回收率等条件，自动暂停不符合要求的广告 | 先调用巨量**自定义报表接口**获取广告最近 N 小时消耗等数据；中台判断达到关停条件后，再调用**广告状态更新接口**将对应广告改为暂停。报表接口负责“查数据”，状态更新接口负责“关广告”。 |
| **自动关闭项目规则** | 项目创建超过设定时长后，自动暂停整个项目 | 调用**获取项目列表**拿到 `project_id` 和项目基础信息；达到设定的创建时长后，调用**批量更新项目状态**接口，把项目改成暂停。 |
| **自动开启广告规则** | 对已经关闭的广告，在最近 N 小时回收率重新达到标准后恢复投放 | 先通过广告/报表数据判断广告当前状态及最近 N 小时表现；满足开启条件后，调用**广告状态更新接口**把广告重新启用。 |
| **自动删除项目规则** | 项目创建超过设定天数后，自动删除项目 | 先通过**获取项目列表**判断项目创建时间；满足模板条件后，调用**批量删除项目**。官方接口会返回删除成功的 `project_ids` 和删除失败信息。 |
| **自动重置账户名称** | 定时把广告账户名称按内部规范重新命名 | 这个功能与项目/广告接口不同。巨量官方 MCP 能力里明确存在“修改广告主信息，可更改账户名称”等账户管理能力，官方文档没有可直接写死的标准 REST URL 和完整必填字段，保留该规则，接入时需确认当前账户权限是否开放“修改广告主信息”。 |
| **素材起量规则** | 当素材对应项目的消耗、回收率、ROI 系数、创建时间达到要求时，对素材执行起量 | 先查投放数据判断条件；满足后调用巨量**素材一键起量**相关能力。官方接口清单明确有“开启素材起量”“获取素材起量方案列表”“获取素材起量状态”“关停素材起量任务”等接口。 |
| **自动更新变现 ROI 系数和预算规则** | 当项目的 ROI、预算、消耗、回收表现达到配置条件时，同时调整 ROI 目标和预算 | 先通过**项目列表 + 自定义报表**获取当前项目及消耗数据；符合条件后分别调用**项目 ROI 目标更新接口**和**项目预算更新接口**。官方 SDK/接口清单明确存在 `/project/roigoal/update/` 与 `/project/budget/update/`。 |

# 巨量官方 API 对接

| 功能 | 巨量官方 API | 方法 | 关键入参 |
| --- | --- | --- | --- |
| **获取规则判断所需投放数据** | `https://api.oceanengine.com/open_api/v3.0/report/custom/get/` | GET | `advertiser_id` 必填；以及报表的 `dimensions`、`metrics`、时间范围等。用于查询广告/项目消耗、转化等指标。巨量官方将其定义为 V3 自定义报表。([商业开放平台](https://open.oceanengine.com/labels/7/docs/1741387668314126?utm_source=chatgpt.com)) |
| **获取项目列表** | `https://api.oceanengine.com/open_api/v3.0/project/list/` | GET | `advertiser_id` 为核心账户参数；可结合过滤条件查具体项目。返回内容包含 `project_id`、项目名称及项目相关信息。([商业开放平台](https://open.oceanengine.com/labels/34/docs/1740937147595776?utm_source=chatgpt.com)) |
| **暂停/开启项目** | `https://api.oceanengine.com/open_api/v3.0/project/status/update/` | POST | 核心必需对象：`advertiser_id`、需要操作的 `project_id/project_ids`、目标状态。关闭时设为暂停状态，开启时设为启用状态。官方接口名称为“批量更新项目状态”。([商业开放平台](https://open.oceanengine.com/labels/7/docs/1740941413906432?utm_source=chatgpt.com)) |
| **删除项目** | `https://api.oceanengine.com/open_api/v3.0/project/delete/` | POST | `advertiser_id` + 需要删除的 `project_ids`。返回删除成功项目列表以及失败项目和失败原因。([商业开放平台](https://open.oceanengine.com/labels/7/docs/1740944781036608?utm_source=chatgpt.com)) |
| **暂停/开启广告** | `https://api.oceanengine.com/open_api/v3.0/promotion/status/update/` | POST | 核心对象为 `advertiser_id`、广告 `promotion_id/promotion_ids` 和目标状态；暂停与开启使用同一个状态更新能力，只是目标状态不同。官方 SDK 当前列有该 V3 接口。([GitHub](https://github.com/oceanengine/ad_open_sdk_java?utm_source=chatgpt.com)) |
| **更新项目预算** | `https://api.oceanengine.com/open_api/v3.0/project/budget/update/` | POST | 核心为 `advertiser_id`、目标项目 `project_id/project_ids`、新的 `budget`。用于你模板中的“调整预算”。官方 SDK 当前明确提供该接口。([GitHub](https://github.com/oceanengine/ad_open_sdk_java?utm_source=chatgpt.com)) |
| **更新项目 ROI 目标** | `https://api.oceanengine.com/open_api/v3.0/project/roigoal/update/` | POST | 核心为 `advertiser_id`、目标 `project_id/project_ids` 以及新的 ROI 目标值。用于“自动更新变现 ROI 系数和预算规则”。官方 SDK 当前明确提供该接口。([GitHub](https://github.com/oceanengine/ad_open_sdk_java?utm_source=chatgpt.com)) |
| **开启素材起量** | `https://api.oceanengine.com/open_api/v3.0/tools/material_raise/create/` | POST | 官方接口清单确认该路径为“开启素材起量”；需要关联投放账户以及素材起量对应对象。“消耗、回收率、ROI、项目创建时间”等都由中台先判断，满足后才调用该接口。([商业开放平台](https://open.oceanengine.com/labels/7/docs/1699352157034496?utm_source=chatgpt.com)) |
| **获取素材起量状态** | 巨量开放平台“获取素材起量状态”接口 | GET | 官方检索结果明确：`advertiser_id` 必填、`project_ids` 必填，用于查询指定项目下的素材起量状态。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **重置账户名称** | “修改广告主信息”能力 | — | 官方能力说明确认可修改“账户名称、联系人、手机号、备注”等； REST URL 和必填字段，这里暂不写死 URL。([商业开放平台](https://open.oceanengine.com/labels/7/docs/1847297391943370?utm_source=chatgpt.com)) |

接口规则：

**第一，模板里的条件不是巨量 API 参数。**  
比如：

`最近 3 小时 + 消耗 ≥ 500 + 回收率 < 80%`

这组条件是中台根据报表数据判断的。判断成立后，才调用 `promotion/status/update/`。

**第二，一个规则可能对应多个巨量 API。**  
例如“自动更新变现 ROI 系数和预算规则”不是一个巨量接口完成，而是：

`查项目/查报表 → project/roigoal/update → project/budget/update`