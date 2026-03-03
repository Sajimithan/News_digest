"""
Global FastAPI exception handlers.

Register all handlers in app/main.py via:
    from app.exceptions.handlers import register_exception_handlers
    register_exception_handlers(app)

All responses share a consistent JSON shape:
    {
        "error": {
            "type":    "<exception class name>",
            "message": "<human-readable description>",
            "details": <optional — omitted when None>
        }
    }
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.errors import DataNotFoundError, InputValidationError, ProviderError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_body(error_type: str, message: str, details: Any = None) -> dict:
    """Build the standard error response body."""
    body: dict = {"error": {"type": error_type, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles FastAPI/Starlette HTTPException (404, 405, etc.)."""
    logger.warning("HTTPException %s on %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("HTTPException", str(exc.detail)),
    )


async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic / FastAPI RequestValidationError (422 Unprocessable Entity)."""
    # Build a compact list of field errors; never include raw values that might contain keys
    field_errors = [
        {"field": " -> ".join(str(loc) for loc in err["loc"]), "msg": err["msg"]}
        for err in exc.errors()
    ]
    logger.warning("RequestValidationError on %s: %s", request.url.path, field_errors)
    return JSONResponse(
        status_code=422,
        content=_error_body("RequestValidationError", "Request validation failed.", details=field_errors),
    )


async def input_validation_handler(request: Request, exc: InputValidationError) -> JSONResponse:
    """Handles our custom InputValidationError (bad date, missing required field, etc.)."""
    details = {"field": exc.field} if exc.field else None
    logger.warning("InputValidationError on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=400,
        content=_error_body("InputValidationError", exc.message, details=details),
    )


async def data_not_found_handler(request: Request, exc: DataNotFoundError) -> JSONResponse:
    """Handles DataNotFoundError — resource exists in the system but has no matching data."""
    logger.info("DataNotFoundError on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=404,
        content=_error_body("DataNotFoundError", exc.message),
    )


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    """
    Handles ProviderError — external API failure.
    Mapped to 502 Bad Gateway because the server's upstream dependency failed.
    API key values are never logged.
    """
    # Log provider name but not the key; exc.message may contain provider-level detail
    logger.error("ProviderError [%s] on %s: %s", exc.provider, request.url.path, exc.message)
    return JSONResponse(
        status_code=502,
        content=_error_body(
            "ProviderError",
            f"External news provider '{exc.provider}' failed.",
            details={"provider": exc.provider},
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any unhandled exception.
    Logs the full traceback (server-side only) and returns a 500 with a safe message.
    """
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body("InternalServerError", "An unexpected server error occurred."),
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Call this once in app/main.py after creating the FastAPI instance:
        register_exception_handlers(app)
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(InputValidationError, input_validation_handler)
    app.add_exception_handler(DataNotFoundError, data_not_found_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
