# FastAPI 布局

状态：accepted  
真源是仓库里的 `backend/app/`。本文件是对照表。第一块如何挂载见 [../architecture/融合.md](../architecture/融合.md)。

仓库根另有 `deployment/*.yaml`（配置）与 `dockerfile/`（应用镜像）。不要在本目录再写 dotenv。

```
backend/
  pyproject.toml
  alembic.ini
  alembic/
  许可证.md
  app/
    main.py                 create_app()，只挂载包
    core/                   shared 白名单（含 db、redis、CORS、信封）
    modules/
      system_admin/         第一块；包内再拆 router 文件
      <next>/
  tests/modules/system_admin/
```

新增业务 = 加一个包 + 一行 `include_router`。不改 `system_admin` 内部文件。

`core` 配 CORS、engine、Redis。本进程 **只提供 API**。生产不要在这里托管前端静态资源（ADR 0012）。数据层：[数据层.md](数据层.md)。

不要：按层堆 `app/routers`、`app/models`。不要全站 `permissions.py`（授权在 `system_admin`）。不要引入 psycopg。
