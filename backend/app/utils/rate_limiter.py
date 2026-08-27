"""Rate limiting middleware using SlowAPI."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "default": "100/minute",
    "websocket": "10/minute",
    "api_heavy": "20/minute",
    "api_light": "200/minute",
}


def get_rate_limit_handler():
    """Get rate limit exceeded handler."""
    return _rate_limit_exceeded_handler
