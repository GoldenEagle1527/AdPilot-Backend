from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str


class Envelope(BaseModel, Generic[T]):
    ok: bool
    data: T | None
    error: ErrorBody | None


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def success(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def failure(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def _status_to_code(status_code: int) -> str:
    mapping = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "INTERNAL_ERROR" if status_code >= 500 else "HTTP_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=failure(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = str(first.get("msg", "字段校验失败"))
        message = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=422,
            content=failure("VALIDATION_ERROR", message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            code = str(detail["code"])
            message = str(detail["message"])
        else:
            code = _status_to_code(exc.status_code)
            message = detail if isinstance(detail, str) else "请求失败"
        return JSONResponse(status_code=exc.status_code, content=failure(code, message))

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=failure("INTERNAL_ERROR", "服务端未处理异常"),
        )
