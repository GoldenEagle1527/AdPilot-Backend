"""测试用的假剧场平台和假全域模板。

应用启动不导入本模块。业务代码只依赖 app.modules.uni_robot.port.UniRobotCatalog。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.envelope import ApiError


@dataclass(frozen=True)
class CatalogEntry:
    """目录里的一条假数据。id 不透明，名称只给测试辨认。"""

    id: int
    name: str


# 与三方剧场已灌的番茄（1）、鸥溪（22）错开，避免测试误当成真实平台。
FAKE_PLATFORMS: tuple[CatalogEntry, ...] = (
    CatalogEntry(9101, "假番茄"),
    CatalogEntry(9102, "假鸥溪"),
)

FAKE_TEMPLATES: tuple[CatalogEntry, ...] = (
    CatalogEntry(8101, "假全域批量模板甲"),
    CatalogEntry(8102, "假全域批量模板乙"),
)


class FakeUniRobotCatalog:
    """按上面两份假目录回答端口。不写数据库。"""

    def __init__(self) -> None:
        self.template_calls: list[int] = []
        self.platform_calls: list[int] = []

    async def require_template(self, template_id: int) -> int:
        """假模板里有这个 id 才交回它。"""
        self.template_calls.append(template_id)
        if template_id not in {row.id for row in FAKE_TEMPLATES}:
            raise ApiError(400, "全域模板不存在")
        return template_id

    async def require_platform(self, platform_id: int) -> int:
        """假平台里有这个 id 才交回它。"""
        self.platform_calls.append(platform_id)
        if platform_id not in {row.id for row in FAKE_PLATFORMS}:
            raise ApiError(400, "剧场平台不存在")
        return platform_id
