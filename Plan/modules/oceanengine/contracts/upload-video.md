# 契约：upload-video

方法：POST  
路径：/api/v1/oceanengine/videos  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

JSON（`extra=forbid`）：`advertiser_id`、`video_url`。

`mock=true` 时追加夹具 `VIDEOS`，`video_id` 为 `mock-video-N`，`status=完成`，返回该条。`mock=false` 走 `POST /open_api/2/file/video/ad/`。未配 secret：503，`巨量未配置`。
