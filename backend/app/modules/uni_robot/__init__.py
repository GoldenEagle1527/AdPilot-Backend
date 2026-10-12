"""全域漫剧机器人。

HTTP 开放按推广链接和按剧条件两组规则。
模板 id 和平台 id 只经目录端口确认。不跑定时，也不创建巨量任务。
"""

from app.modules.uni_robot.controller import router

__all__ = ["router"]
