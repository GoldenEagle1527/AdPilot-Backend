# 契约：create-task

业务id：uni-native-task
文档版本：2
方法：POST
路径：/api/v1/uni-native-tasks
作用：本地新增一条端原生投放任务。不上传素材，不调用巨量。状态写成 `saved`。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| template_id | body | integer | 是 | 未删除的全域模板 id。标准模板当不存在 |
| series_id | body | integer | 是 | `manhua_series.id`。表不在当前库时拒绝，不造短剧行 |
| project_budget | body | number | 否 | 项目预算，单位元。不传则抄模板。大于 0，最多两位小数 |
| roi_coefficient | body | number | 否 | ROI 系数。不传则抄模板。0–9999.999，最多三位小数 |
| accounts | body | array | 是 | 至少 1 行，最多 50。每行 `douyin_account_id` 与 `advertiser_id` 一一对应。抖音号、账户各自不能重复 |
| accounts[].douyin_account_id | body | integer | 是 | 未删除的全域抖音号，且 `douyin_pitcher` 里已分给当前投手 |
| accounts[].advertiser_id | body | integer | 是 | 巨量广告主 id。须为当前投手名下、`sync_status=active`、未软删 |
| promotion_links | body | array | 否 | IAA / IAP 文本，可空，最多 50。不传时，若 `theater_promotion_links` 在库里，用这部剧一条启用的 IAA `promotion_url` 填 `link_text`。表不在或没有 IAA 链则仍为空。不写入标准投放的专辑链接 |
| promotion_links[].charge_mode | body | string | 是 | `IAA` 或 `IAP` |
| promotion_links[].link_text | body | string | 是 | 去首尾空白，1–2048 字 |
| video_ids | body | array of integer | 否 | 视频素材 id，须属于该短剧，且上传者或投手归属是当前用户。`material_videos` 不在库时不能传。可空，不重复，最多 200 |
| title_ids | body | array of integer | 否 | 当前用户自己的标题库 id。`material_titles` 不在库时不能传。可空，不重复，最多 100 |
| batch_titles | body | array of string | 否 | 临时标题，1–512 字。只存在任务上，不插入标题库。可空，最多 100 |

多传字段返回 422。不收 `status`。服务端固定写成 `saved`，`executed_at` 为空。

示例：

```json
{
  "template_id": 11,
  "series_id": 8,
  "project_budget": "66.50",
  "accounts": [{ "douyin_account_id": 4, "advertiser_id": 90001 }],
  "promotion_links": [{ "charge_mode": "IAA", "link_text": "https://iaa.example/a" }],
  "video_ids": [],
  "title_ids": [],
  "batch_titles": ["临时标题"]
}
```

## 响应

新建后的整条记录，字段同 [list-tasks.md](list-tasks.md) 的列表项。成功 HTTP 200。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `模板不存在` | 不是未删除的全域模板 |
| 404 | `短剧不存在` | 短剧 id 没有未删除行 |
| 404 | `抖音号不存在` | 抖音号 id 没有未删除行 |
| 400 | `短剧库不存在` | 当前库没有 `manhua_series` |
| 400 | `只能使用全域抖音号` | 用了标准号 |
| 400 | `抖音号未分配给当前投手` | 全域号没分给当前用户 |
| 400 | `账户不存在、未分配给当前投手或已失效` | 广告主不是当前投手的有效户 |
| 400 | `视频素材表不存在` | 传了视频 id，但没有 `material_videos` |
| 400 | `视频不存在、不属于该短剧或未归属当前投手` | 视频 id 对不上 |
| 400 | `标题库不存在` | 传了标题库 id，但没有 `material_titles` |
| 400 | `标题不存在或不属于当前账号` | 标题 id 对不上 |
| 422 | `抖音号重复` | 账户行、视频或标题 id 重复，金额越界，或多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 新建并保存 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 2 | 否 | 省略 `promotion_links` 时，剧场表存在则用该剧 IAA 推广链填一条 `link_text` | |
| 2026-09-30 | 1 | 否 | 初稿 | |
