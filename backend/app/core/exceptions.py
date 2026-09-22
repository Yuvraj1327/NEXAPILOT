"""
Application-level exceptions and their FastAPI handlers.

Every error the API returns — expected or not — comes back in the same
JSON shape so the frontend only has to handle one error contract:

    {
        "error": {
            "code": "SOME_ERROR_CODE",
            "message": "Human readable message",
            "details": null | {...}
        }
    }
"""

import logging
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("nexapilot")


class AppError(Exception):
    """Base class for all deliberate, application-raised errors.

    Raise a subclass of this (or this directly) anywhere in the app to get
    a consistent, typed error response without reaching for raw
    HTTPException. Keep messages user-safe — they can reach the frontend.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, *, details: Optional[Any] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


def _error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all centralized exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's raw exc.errors() can include a non-JSON-serializable
        # "ctx": {"error": ValueError(...)} entry whenever a field_validator
        # raises ValueError (e.g. a malformed wallet address) -- run it
        # through jsonable_encoder (the same helper FastAPI's own default
        # handler uses) so those exception objects become plain strings.
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed.",
            details=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            exc.status_code,
            "HTTP_ERROR",
            str(exc.detail) if exc.detail else "An HTTP error occurred.",
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error while handling %s %s", request.method, request.url)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "DATABASE_ERROR",
            "A database error occurred. Please try again shortly.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while handling %s %s", request.method, request.url)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred.",
        )
