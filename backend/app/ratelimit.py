"""
Rate limiting utilities and configuration.

This module provides a stub implementation and configuration guide for adding
rate limiting to the URL Shortener API. Rate limiting protects against abuse
and denial-of-service attacks.

Production Implementation Options:
1. Redis-backed: Use redis-py + SlowAPI for distributed rate limiting
2. In-memory: Use cachetools for simple single-instance rate limiting
3. Reverse proxy: Use nginx/Caddy for application-level rate limiting
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import os

# Configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_PROVIDER = os.getenv("RATE_LIMIT_PROVIDER", "redis")  # or "memory"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Rate limit policies (requests per time window)
RATE_LIMITS = {
    "create_short_url": {
        "requests": 100,
        "period_seconds": 3600,  # 1 hour
        "by": "ip"
    },
    "redirect": {
        "requests": 1000,
        "period_seconds": 3600,
        "by": "ip"
    },
    "analytics": {
        "requests": 50,
        "period_seconds": 3600,
        "by": "api_key"
    },
    "export": {
        "requests": 10,
        "period_seconds": 3600,
        "by": "api_key"
    }
}


class RateLimiter:
    """
    Abstract rate limiter interface.
    
    Production implementations should:
    1. Track request count per key (IP or API key)
    2. Reset counters periodically
    3. Return remaining requests and retry-after header info
    4. Handle distributed scenarios (multiple servers)
    """
    
    async def check_rate_limit(self, key: str, limit_name: str) -> Dict:
        """
        Check if a request is within rate limits.
        
        Args:
            key: Identifier (IP address or API key)
            limit_name: Name of the rate limit policy
        
        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "reset_after_seconds": int
            }
        """
        raise NotImplementedError("Subclasses must implement check_rate_limit")


class RedisRateLimiter(RateLimiter):
    """Redis-backed rate limiter for distributed deployments.
    
    Implementation requires:
    - redis-py: pip install redis
    - SlowAPI: pip install slowapi
    
    Example usage with FastAPI:
    
    ```python
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.post("/api/v1/shorten")
    @limiter.limit("100/hour")
    def create_short_url(body: ShortenRequest, _=Depends(RateLimitDep)):
        pass
    ```
    """
    
    async def check_rate_limit(self, key: str, limit_name: str) -> Dict:
        """Check rate limit using Redis."""
        # TODO: Implement with redis-py
        # 1. Create key: f"ratelimit:{limit_name}:{key}"
        # 2. INCR and EXPIRE on Redis
        # 3. Return remaining count
        return {"allowed": True, "remaining": -1, "reset_after_seconds": 0}


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for single-instance deployments.
    
    Simple dict-based counter. NOT suitable for multi-instance deployments.
    Use Redis limiter for production with multiple servers.
    """
    
    def __init__(self):
        self.counters: Dict[str, Dict] = {}
    
    async def check_rate_limit(self, key: str, limit_name: str) -> Dict:
        """Check rate limit using in-memory counter."""
        # TODO: Implement with cachetools or manual tracking
        # Current: Always allow (no limit enforcement)
        return {"allowed": True, "remaining": -1, "reset_after_seconds": 0}


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get configured rate limiter instance."""
    if not RATE_LIMIT_ENABLED:
        return None
    
    if RATE_LIMIT_PROVIDER == "redis":
        return RedisRateLimiter()
    elif RATE_LIMIT_PROVIDER == "memory":
        return MemoryRateLimiter()
    else:
        raise ValueError(f"Unknown rate limit provider: {RATE_LIMIT_PROVIDER}")


# Example middleware integration (not yet active in main.py)
"""
To enable rate limiting in main.py, add:

from .ratelimit import get_rate_limiter, RATE_LIMITS

rate_limiter = get_rate_limiter()

async def enforce_rate_limit(request: Request, endpoint_name: str):
    if not rate_limiter:
        return  # Rate limiting disabled
    
    key = request.client.host if request.client else "unknown"
    result = await rate_limiter.check_rate_limit(key, endpoint_name)
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {result['reset_after_seconds']}s"
        )

# Then decorate endpoints:
@app.post("/api/v1/shorten")
async def create_short_url(
    body: ShortenRequest,
    request: Request,
    _=Depends(lambda: enforce_rate_limit(request, "create_short_url"))
):
    ...
"""

