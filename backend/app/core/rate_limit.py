"""
Rate limiting middleware for API endpoints
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from app.core.config import settings
from app.core.redis import redis_client


def get_redis_client():
    """Get Redis client for rate limiting storage"""
    return redis_client.client


def get_client_id(request: Request):
    """Get client identifier for rate limiting"""
    # Try to get user ID from JWT token if authenticated
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_client_id,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2",  # Use db=2 for rate limiting
    enabled=settings.RATE_LIMIT_ENABLED,
)


def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting for FastAPI app"""
    if settings.RATE_LIMIT_ENABLED:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Common rate limit decorators
def auth_rate_limit():
    """Rate limit for authentication endpoints (stricter)"""
    return limiter.limit("5/minute")


def api_rate_limit():
    """Rate limit for general API endpoints"""
    return limiter.limit(f"{settings.RATE_LIMIT_REQUESTS_PER_MINUTE}/minute")


def burst_rate_limit():
    """Rate limit for burst operations"""
    return limiter.limit(f"{settings.RATE_LIMIT_BURST}/second")