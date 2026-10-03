"""AppError and the handlers that render every error as {"error": {code, message, details, request_id}}.

Every error is logged once here with its code, so the access line plus this line explain any
failed request. Unexpected exceptions get a full traceback in the log and a generic message
in the response (never internals). Docs: docs/api/errors.md.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.logging import REQUEST_ID_HEADER, request_id_var

log = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details


def not_found(code: str, what: str) -> AppError:
    return AppError(code, f"{what} not found", 404)


def _body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details, "request_id": request_id_var.get()}}


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        log.log(
            logging.WARNING if exc.status >= 500 else logging.INFO,
            "%s (%d): %s",
            exc.code,
            exc.status,
            exc.message,
            extra={"event": "http.error", "error_code": exc.code, "status": exc.status},
        )
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        fields = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "problem": e["msg"]} for e in exc.errors()
        ]
        log.info(
            "VALIDATION_ERROR (422): %s",
            fields,
            extra={"event": "http.error", "error_code": "VALIDATION_ERROR", "status": 422},
        )
        return JSONResponse(_body("VALIDATION_ERROR", "Request is invalid", {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "VALIDATION_ERROR")
        log.info(
            "%s (%d): %s",
            code,
            exc.status_code,
            exc.detail,
            extra={"event": "http.error", "error_code": code, "status": exc.status_code},
        )
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
            extra={"event": "http.error", "error_code": "INTERNAL_ERROR", "status": 500},
        )
        # Rendered outside RequestContextMiddleware, so the header is added here.
        return JSONResponse(
            _body("INTERNAL_ERROR", "Unexpected server error"),
            status_code=500,
            headers={REQUEST_ID_HEADER: request_id_var.get()},
        )
