# oc投放-标准自动投放策略-端原生投手补广告

# 规则功能说明

| 规则类型 | 这个模板是干什么的 | 巨量接口怎么配合 |
| --- | --- | --- |
| **自动补计划规则** | 按每天指定时间和“消耗数据统计时间”检查当前端原生广告。当某个广告/项目达到需要补量的条件后，复制已有广告配置，新建指定数量的广告；同时根据规则类型分别使用“关键行为预算 / 变现ROI预算 / 付费ROI预算”作为新广告的预算策略。 | 先通过**广告列表接口**获取已有广告及所属项目，找到需要复制的广告；再通过**自定义报表接口**获取指定统计时间内的消耗等数据；满足补广告条件后，不是调用“复制广告”接口，而是读取原广告配置后调用**创建广告接口**重新创建广告；如果新广告预算需要单独调整，再调用**广告预算更新接口**。巨量新版支持在已有项目下新增广告，复用原项目配置。 |

# 巨量官方 API 对接

| 功能 | 巨量官方 API | 方法 | 关键入参 |
| --- | --- | --- | --- |
| **获取现有广告，确定要复制哪条广告** | `https://api.oceanengine.com/open_api/v3.0/promotion/list/` | GET | 核心必填：`advertiser_id`；可通过 `filtering` 按 `project_id`、`promotion_id`、状态等筛选。返回广告列表，用于取得现有广告及对应 `promotion_id`、`project_id` 等信息。巨量官方 SDK 明确提供 `PromotionListV30Api`。 |
| **获取原广告配置，作为“复制广告”的来源** | `https://api.oceanengine.com/open_api/v3.0/promotion/list/` | GET | `advertiser_id` 必填；通过过滤指定原广告。产品逻辑上，“复制广告”实际是读取原广告配置后重新创建，不是简单传一个“copy\_id”。巨量新版后台本身也支持引用已有广告设置进行二次编辑。 |
| **创建新的补量广告** | `https://api.oceanengine.com/open_api/v3.0/promotion/create/` | POST | 官方 V3 创建广告接口。核心必需对象包括 `advertiser_id`、`project_id`，以及广告创编所需的素材、预算/出价、推广内容等配置。具体必填项会随项目的营销目的、投放模式不同而变化，基于原广告配置复用对应字段。巨量官方 SDK明确存在 `PromotionCreateV30Api`。 |
| **获取消耗等投放数据** | `https://api.oceanengine.com/open_api/v3.0/report/custom/get/` | GET | `advertiser_id`；以及 `dimensions`、`metrics`、`start_time`、`end_time` 等。用于中台页面里的“消耗数据统计时间”，判断哪些广告需要补。巨量 Marketing API 支持将投放数据接入内部系统进行实时投放决策。 |
| **修改新广告预算** | `https://api.oceanengine.com/open_api/v3.0/promotion/budget/update/` | POST | 核心对象：`advertiser_id`、目标 `promotion_id`、新的预算值。用于新广告创建完成后，根据“关键行为预算 / 变现ROI预算 / 付费ROI预算”给补出来的广告设置目标预算。 |

# 操作链路

到执行时间 → 查消耗 → 找出需要补的原广告 → 读取原广告配置 → 按“复制广告数量”循环调用 `promotion/create` → 根据规则类型设置对应预算。