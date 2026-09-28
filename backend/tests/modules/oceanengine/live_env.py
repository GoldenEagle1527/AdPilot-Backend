"""从仓库根 test.env 读取巨量应用号和密钥。不打印密钥。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OceanEngineTestCredentials:
    """测试用的开放平台应用凭证。"""

    app_id: int
    secret: str


def test_env_path() -> Path:
    """仓库根的 test.env。"""
    return Path(__file__).resolve().parents[4] / "test.env"


def load_test_credentials() -> OceanEngineTestCredentials:
    """解析 APP_ID 与 Secret。文件不存在或键空缺时抛出 FileNotFoundError / ValueError。"""
    path = test_env_path()
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("test.env 是空文件，请先保存 APP_ID 和 Secret")
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
        elif "=" in line:
            key, value = line.split("=", 1)
        else:
            continue
        values[key.strip().lower()] = value.strip().strip('"').strip("'")
    app_text = values.get("app_id", "")
    secret = values.get("secret", "")
    if not app_text.isdigit():
        raise ValueError("test.env 的 APP_ID 不是数字")
    if not secret:
        raise ValueError("test.env 的 Secret 为空")
    return OceanEngineTestCredentials(app_id=int(app_text), secret=secret)
