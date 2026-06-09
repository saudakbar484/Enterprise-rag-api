from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import logger


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "http_error",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": request.url.path},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("database_error", extra={"error": str(exc), "path": request.url.path})
    return JSONResponse(
        status_code=503,
        content={"error": "Database connection failure", "path": request.url.path},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_error", extra={"error": str(exc), "path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "path": request.url.path},
    )
