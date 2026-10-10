---
name: adpilot-local-baota
description: >-
  Runs AdPilot backend checks on the developer machine with python main.py,
  then hands BaoTa update commands to the user. Use when starting a local
  API, testing a change before commit, deploying or updating the harbor
  server, or when the user mentions 宝塔, python main.py, 本地起服务, or 更新服务器.
---

# 本地测，宝塔手动更新

本机用 `python main.py` 起临时进程测接口。测通并提交后，把更新命令交给用户，由用户在宝塔那台机器上执行。代理不登录宝塔，不 SSH 到 `192.168.111.40`。

## 本地

工作目录是 `backend/`。只读 `deployment/dev.yaml`（不要设置 `ADPILOT_ENV`，或设为 `dev`）。`postgres` / `redis` 在本机解析不到时会落到 `127.0.0.1` 上的 Docker。

禁止在本机使用 `ADPILOT_ENV=prod`。禁止对本机以外的库或 Redis 做迁移、清库、灌种。配置加载时若主机不是本机地址，进程直接报错退出。确要连远程必须同时设置 `ADPILOT_ALLOW_REMOTE=1`；本机测试不要设这个变量。

```bash
cd backend
python main.py
```

完成标准：进程听在 `8300`，改过的接口在 `http://127.0.0.1:8300/docs` 上得到预期状态码。测完停掉进程，把端口让出来。

表结构有变时，仍在 `backend/` 下先执行 `alembic upgrade head`，再起服务。已有迁移就升级，不要为灌已有数据再 `revision --autogenerate`。

## 提交

业务改动在 `feat/<business>/<short>` 上提交，合进 `main` 后再让用户更新服务器。`deployment/prod.yaml` 不入库。

## 交给用户的服务器命令

代码在 `main` 上之后，把命令交给用户，让他们在宝塔机器上执行。不要代跑。

先拉代码，再重启。重启在仓库根：

```bash
cd /www/wwwroot/AdPilot-Backend
git pull origin main
docker compose up -d --build
```

这次提交改了表时，再附上迁移。迁移在 `backend/`：

```bash
cd /www/wwwroot/AdPilot-Backend/backend
alembic revision --autogenerate -m "说明"
alembic upgrade head
```

`说明` 换成这次表变更的一句话。只动 `AdPilot-Backend` 这一个容器。宝塔里其它 Python 项目保持原样。

## 更新前核对线上库

表变更可能和线上现状对不上时（列已在、类型不同、手工改过表、迁移链和模型不一致），先看服务器上的库，再决定能不能按上面两行直接迁。

看的时候只读：`SELECT`、`information_schema`、`\d`、`alembic_version`。对照模型和将要生成的 revision，能对上就把迁移命令交给用户。对不上就先改仓库里的迁移，改完再交命令。

看服务器上的库时严禁任何修改：不执行 `INSERT` / `UPDATE` / `DELETE` / DDL，不在这台库上跑 `alembic upgrade` 或 `revision`。
