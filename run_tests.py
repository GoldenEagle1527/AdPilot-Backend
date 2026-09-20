"""在 Compose 网里跑 unittest（本机 Windows 直连映射端口对 asyncpg 不稳定）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    cmd = ["docker", "compose", "--profile", "test", "run", "--rm", "test"]
    if len(sys.argv) > 1:
        quoted = " ".join(sys.argv[1:])
        cmd.extend(["sh", "-c", f"alembic upgrade head && python -m unittest {quoted}"])
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
