# oc投放-智能投放-标准自动投放策略-小程序规则

接口参考具体参考巨量官方文档：

| 功能 | 巨量官方 API | 方法 | 关键入参 | 在你们规则里的使用方式 |
| --- | --- | --- | --- | --- |
| **获取投放数据** | 自定义报表 `report_custom_get_v3` | 巨量开放平台报表能力 | `advertiser_id`、报表维度、指标、时间范围 | 用来取消耗、点击、转化等数据。模板里的“消耗 > 1000”“最近N小时”等条件，都先通过报表数据判断。巨量同时提供 `report_custom_config_get_v3` 查询当前可用指标和维度。([商业开放平台](https://open.oceanengine.com/mcp?app_id=1841425772187712&utm_source=chatgpt.com)) |
| **一键起量** | `https://api.oceanengine.com/open_api/2/tools/task_raise/create/` | POST | `advertiser_id`、`budget_mode` 等 | 当中台判断消耗、回收率等满足“一键起量规则”后，调用这个接口创建优选起量任务。`budget_mode` 官方可选 `LIMIT`、`NO_LIMIT`。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1733956164012035&utm_source=chatgpt.com)) |
| **修改预算** | `https://ad.oceanengine.com/open_api/v1.0/qianchuan/ad/budget/update/` | POST | `advertiser_id`；`data[].ad_id`；`data[].budget` | 用于“自动更新预算”“关键行为预算调整”等。先判断规则是否命中，再把对应广告 `ad_id` 和新的预算 `budget` 传给巨量。 |
| **上传转码后视频** | `https://api.oceanengine.com/open_api/v3.0/tools/ebp/video/upload/` | POST | 视频文件相关字段 + 对应账户信息 | “素材自动转码”先在内部完成转码，之后调用这个接口把新视频重新上传到巨量。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1855448450527623&utm_source=chatgpt.com)) |
| **获取工作台账户** | `https://api.oceanengine.com/open_api/2/ebp/advertiser/list/` | GET | `enterprise_organization_id`、`account_source` | 用来获取系统可操作的广告账户。`account_source` 官方可选 `AD`、`LOCAL`、`QIANCHUAN`。后续所有广告、项目、素材操作都要先明确对应账户。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1829550825614739&utm_source=chatgpt.com)) |
| **更新字节小程序资产** | `https://api.oceanengine.com/open_api/v3.0/tools/micro_app/update/` | POST | `advertiser_id`、`instance_id`、`app_page[]`、`tag_info` | 小程序投流需要同步小程序页面、落地参数，可通过这个接口更新小程序资产。`app_page` 中可维护 `link`、`start_page`、`start_param`，操作类型支持 `NEW`、`MODIFY`、`DELETE`。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1780614097935372&utm_source=chatgpt.com)) |
| **新建字节小程序资产** | `https://api.oceanengine.com/open_api/v3.0/tools/ebp/micro_applet/create/` | POST | `account_id`、`account_type`、`app_id`、`schema_info[]` | 首次把小程序接入巨量资产时使用。`schema_info` 里包括 `link`、`start_page`、`start_param`。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1847487532455299&utm_source=chatgpt.com)) |
| **小程序资产共享** | `https://api.oceanengine.com/open_api/v3.0/tools/bp_asset_management/share/` | POST | `organization_id`、`instance_id`、`asset_type`、`share_mode` | 如果一个小程序资产需要共享给多个广告账户使用，就用这个接口。`asset_type` 支持 `APPLETS`、`BYTED_APPLETS`、`WECHAT_GAME` 等。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1773089427219584&utm_source=chatgpt.com)) |

小程序自动投放策略功能逻辑：

| 规则类型 | 这个模板是干什么的 | 巨量接口怎么配合 |
| --- | --- | --- |
| **一键起量规则** | 当广告消耗、当日回收率、总回收率达到设定标准后，对表现好的广告执行起量 | 先调用**报表接口**获取消耗、回收相关数据 → 条件满足 → 调用巨量的**起量任务接口**。巨量有“新建优选起量任务”能力。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1733956164012035&utm_source=chatgpt.com)) |
| **自动更新变现ROI系数和预算规则** | 根据当前ROI系数、预算、回收率、消耗情况，自动调整ROI系数和预算 | 先查广告/项目当前配置 + 投放报表 → 满足规则 → 调用**项目/广告修改接口**修改ROI相关配置，同时调用预算修改能力。这里需要开发重点确认当前小程序投放类型是否开放“ROI系数”字段的修改权限，不能直接假定所有账户都支持。 |
| **自动更新关键行为预算规则** | 当某个关键行为达到设定条件后，自动提高或调整对应广告预算 | 报表接口查询当天关键行为数据 → 判断 → 调用**广告/项目预算更新接口**修改预算。 |
| **自动更新预算规则** | 当当天消耗达到预算的一定比例，比如消耗＞80%预算时，自动把预算提高到新的金额 | 获取当天消耗 + 当前预算 → 中台判断百分比 → 调用**预算修改接口**。这个规则不需要把“80%”传给巨量，80%只是中台的触发条件。 |
| **自动关闭低耗素材规则** | 定期找出长期没有获得消耗或消耗过低的素材，停止继续参与投放 | 先查询素材对应的投放消耗 → 找到低耗素材 → **不要简单理解成“暂停素材”**。巨量素材本身更接近资源资产，实际需要停止使用该素材的广告/创意，或者使用巨量提供的素材清理能力。官方提供素材标签、低效素材识别等能力。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **自动关闭广告规则** | 最近N小时内，广告的消耗、回收率、竞价策略等达到关停条件时自动暂停广告 | 报表接口查询最近N小时数据 → 判断条件 → 调用**广告状态更新接口**，把广告改为暂停。 |
| **自动关闭项目规则** | 项目创建超过指定小时后，自动把项目停止 | 查询项目列表/项目创建时间 → 达到条件 → 调用**项目状态更新接口**关闭项目。 |
| **自动开启广告规则** | 对已经暂停的广告，如果最近N小时对应业务回收达到要求，则重新开启 | 查询暂停广告 + 对应时间段数据 → 回收率达到阈值 → 调用**广告状态更新接口**重新开启。 |
| **自动清理素材资源** | 清理长期不用、低消耗、历史较久的素材资源；可以区分转码素材、自动剪辑素材 | 获取素材列表、素材创建时间、素材消耗和素材标签 → 筛选满足条件的资源 → 调用素材清理/删除能力。巨量目前确实提供素材列表、素材评估标签、清理任务相关能力。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **自动删除广告规则** | 当某个项目已经产生较大消耗后，把同项目里长期0消耗或低消耗广告删除 | 查项目及项目下广告 → 获取各广告当天消耗 → 筛出≤设定金额的广告 → 调用**删除广告/删除单元接口**。巨量开放平台有“删除单元”能力，返回成功删除的 `promotion_ids` 和失败信息。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **自动删除项目规则** | 项目创建超过N天，同时累计消耗满足设定条件时，把项目清掉 | 查询项目创建时间 + 累计消耗 → 判断 → 调用**删除项目接口**。巨量官方开放平台已有“删除项目”能力。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **自动重置账户名称** | 定时统一整理广告账户名称，比如按照内部命名规范重新命名 | 这个和投放策略不同，属于**账户管理能力**。先获取账户列表 → 按内部命名规则生成新名称 → 调用账户资料修改能力。 |
| **自动删除广告素材规则** | 当广告整体已经有较高消耗时，把该广告下0消耗/低消耗素材删除 | 获取广告消耗 → 获取广告关联素材 → 获取各素材消耗 → 删除满足条件的素材或解除其投放关系。这里和“删除广告”不同，操作对象是素材。 |
| **素材起量规则** | 当素材所在项目的消耗、回收率、ROI、项目创建时间达到标准后，为优质素材启动起量 | 先查项目/素材报表 → 条件满足 → 调用巨量的**素材起量相关能力**。官方当前可以查询“素材起量状态”，说明平台存在对应的素材起量体系。([商业开放平台](https://open.oceanengine.com/search/index.html?s=qianchuan%2Funi_promotion%2Flist%2F&utm_source=chatgpt.com)) |
| **素材自动转码规则** | 当素材当天小时消耗从高位下降到低位时，对素材进行转码，重新产出可使用版本 | 先查素材小时消耗 → 判断是否从X元以上下降到Y元以下 → 满足后触发**素材转码能力**。素材平台自己的处理；转码完成后，再通过巨量视频上传接口重新上传素材。巨量支持视频素材上传。([商业开放平台](https://open.oceanengine.com/tools/visual_debug.html?docId=1855448450527623&utm_source=chatgpt.com)) |