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

工作目录是 `backend/`。配置读 `deployment/prod.yaml`（`ADPILOT_ENV=prod`），库和 Redis 都在 `192.168.111.40`。

```bash
cd backend
ADPILOT_ENV=prod python main.py
```

完成标准：进程听在 `8300`，改过的接口在 `http://127.0.0.1:8300/docs` 上得到预期状态码。测完停掉进程，把端口让出来。

表结构有变时，仍在 `backend/` 下先执行 `ADPILOT_ENV=prod alembic upgrade head`，再起服务。已有迁移就升级，不要为灌已有数据再 `revision --autogenerate`。

## 提交

业务改动在 `feat/<business>/<short>` 上提交，合进 `main` 后再让用户更新服务器。`deployment/prod.yaml` 不入库。

## 交给用户的服务器命令

代码在 `main` 上之后，把下面整段发给用户，让他们在宝塔机器的仓库根执行。不要代跑。

```bash
cd /www/wwwroot/AdPilot-Backend
git pull origin main
docker compose up -d --build
```

这次提交改了表时，再附上：

```bash
cd /www/wwwroot/AdPilot-Backend/backend
ADPILOT_ENV=prod alembic upgrade head
```

只动 `AdPilot-Backend` 这一个容器。宝塔里其它 Python 项目保持原样。
