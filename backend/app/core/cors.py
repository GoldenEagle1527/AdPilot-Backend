from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings


def apply_cors(app: FastAPI, settings: Settings) -> None:
    """按配置挂 CORS。`*` 表示任意 Origin（不能带 Cookie 凭证）。"""
    wildcard = settings.cors_origins == ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if wildcard else settings.cors_origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )
