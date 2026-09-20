---
name: adpilot-add-module
description: Adds a new FastAPI business package under app/modules and mounts it. Use when creating a new business module, opening a new domain package, or copying Plan/modules/_template for a backend block.
---

# 新建业务包

本仓已有框架和 `system_admin`。不要重搭进程、不要建 `app/routers`。

## 步骤

1. 稳定 id：计划里 kebab-case（如 `ad-delivery`），Python 包 snake_case（`ad_delivery`）。
2. 若还要写计划：复制 `Plan/modules/_template/` → `Plan/modules/<kebab>/`，改 `说明.md`（职责 + 「不自建权限台」），在该块 `后端.md` 留空表。投放/素材/报表未开块前不要为了菜单树节点名而开包。
3. 建包：

```
backend/app/modules/<snake>/
  __init__.py          # 导出 router
  api/
  schemas/
  domain/              # 按需；表模型只住这里
```

4. `main.py` 只加一行 `include_router`。路径前缀 `/api/v1/<kebab>/...`。
5. 鉴权：`from app.modules.system_admin import require_menu`，例如 `Depends(require_menu("32"))`（节点 id 看菜单树）。禁止 import `system_admin.domain.models`。
6. 配置/CORS/信封/engine 用 `app.core`，禁止新开引擎或 dotenv。
7. 迁移：新表用 Alembic 新 revision，不要再 `create_all` 糊进 `20260920_01`。
8. 测试目录：`backend/tests/modules/<snake>/`（仓库里测试目录目前是空的，新包一起建）。

## 不要

- 自建角色/权限码表
- 把领域模型放进 `core`
- 在本仓写前端页面
- 按菜单种子里的 102 个名字预建投放 CRUD
