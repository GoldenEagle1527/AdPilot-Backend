# 契约：create-app

业务id：theater
文档版本：1
方法：POST
路径：/api/v1/theater/apps
作用：新增一条三方剧场应用。新增后一律为有效。对应应用列表的「新增」弹窗。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| platform_id | body | integer | 是 | 平台 id。平台须**已启用**且勾选了所选剧场类型（选端原生要求 `supports_native=true`，选小程序要求 `supports_mini_program=true`） |
| name | body | string | 是 | 剧场名称，去首尾空白，1–128 字。同平台下不能与未删除的应用重名 |
| theater_type | body | string | 是 | 剧场类型：`mini_program` 小程序、`native` 端原生。入参不拦小程序；两个平台默认都没勾小程序，选小程序会因平台不支持返回 400 |
| delivery_mode | body | string | 是 | 投放模式，单选：`IAA`、`IAP` |
| style | body | string | 是 | 剧场风格：`live_action` 真人剧、`manhua` 漫剧 |
| ad_source | body | string | 是 | 广告来源名称，人工填写，巨量审核广告时使用。去首尾空白，1–64 字 |

需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。

body 只收以上字段，多传（如 `is_valid`、`id`）返回 422。状态不可在新增时指定。

示例：

```json
{
  "platform_id": 1,
  "name": "甲剧场",
  "theater_type": "native",
  "delivery_mode": "IAA",
  "style": "manhua",
  "ad_source": "甲来源"
}
```

## 响应

新增后的整条记录，字段同 [list-apps.md](list-apps.md) 的 **AppItem**，`is_valid` 恒为 `true`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `delivery_mode: Input should be 'IAA' or 'IAP'` | 投放模式不认识，或传了数组 |
| 422 | `name: String should have at most 128 characters` | 名称或广告来源为空白或超长、枚举不认识、多带字段 |
| 404 | `平台不存在` | 平台 id 不存在或已软删 |
| 400 | `平台已禁用：番茄` | 平台已禁用 |
| 400 | `平台番茄不支持小程序` | 平台没勾所选剧场类型 |
| 409 | `剧场名称已存在` | 同平台下已有未删除的同名应用 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/应用列表 | 「新增」弹窗提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
