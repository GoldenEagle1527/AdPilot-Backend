"""全局响应信封。所有接口只返回 {code, message, data}，异常也在这里收口。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """统一响应体。成功 code 为 200，失败 code 与 HTTP 状态一致。"""

    code: int
    message: str
    data: T | None


class ApiError(Exception):
    """业务失败。抛它就行，HTTP 状态即 code，message 给人看。"""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message


def success(data: Any = None, message: str = "成功") -> dict[str, Any]:
    """成功信封。"""
    return {"code": 200, "message": message, "data": data}


def failure(code: int, message: str) -> dict[str, Any]:
    """失败信封。"""
    return {"code": code, "message": message, "data": None}


def _json(code: int, message: str) -> JSONResponse:
    """按失败信封出 JSONResponse。"""
    return JSONResponse(status_code=code, content=failure(code, message))


def register_exception_handlers(app: FastAPI) -> None:
    """全局异常捕获：业务失败、入参校验、HTTP 异常、未捕获异常都收成同一套信封。"""

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return _json(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = str(first.get("msg", "字段校验失败"))
        return _json(422, f"{loc}: {msg}" if loc else msg)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "请求失败"
        return _json(exc.status_code, message)

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        return _json(500, "服务端未处理异常")
