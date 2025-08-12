import logging
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from app.shared.exceptions import (
    DomainException,
    EntityNotFound,
    EntityAlreadyExists,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    ExternalServiceError,
)

logger = logging.getLogger(__name__)


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """Handle domain-specific exceptions"""
    logger.warning(f"Domain exception: {exc}")

    if isinstance(exc, EntityNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Entity not found",
                "detail": str(exc),
                "entity_type": exc.entity_type,
                "entity_id": exc.entity_id,
            },
        )

    elif isinstance(exc, EntityAlreadyExists):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Entity already exists",
                "detail": str(exc),
                "entity_type": exc.entity_type,
                "field": exc.field,
                "value": exc.value,
            },
        )

    elif isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": str(exc),
                "field": exc.field,
                "message": exc.message,
            },
        )

    elif isinstance(exc, UnauthorizedError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Unauthorized", "detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    elif isinstance(exc, ForbiddenError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Forbidden", "detail": str(exc)},
        )

    elif isinstance(exc, ExternalServiceError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "External service error",
                "detail": str(exc),
                "service": exc.service,
            },
        )

    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Domain error", "detail": str(exc)},
        )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request validation error",
            "detail": "Invalid request data",
            "errors": exc.errors(),
        },
    )


async def http_exception_handler(
    request: Request, exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP exception: {exc}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database errors"""
    logger.error(f"Database error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database error",
            "detail": "An error occurred while processing your request. Please try again later.",
            "type": "database_error",
        },
    )


async def redis_exception_handler(request: Request, exc: RedisError) -> JSONResponse:
    """Handle Redis errors"""
    logger.error(f"Redis error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Cache service error",
            "detail": "An error occurred with the cache service. Please try again later.",
            "type": "cache_error",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "type": "internal_error",
        },
    )


def setup_exception_handlers(app):
    """Set up all exception handlers for the FastAPI app"""

    # Domain exceptions
    app.add_exception_handler(DomainException, domain_exception_handler)

    # Request validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    # Redis errors
    app.add_exception_handler(RedisError, redis_exception_handler)

    # General exceptions (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
