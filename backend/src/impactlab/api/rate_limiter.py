"""In-memory rate limiter with sliding window counter for API hardening."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import ClassVar

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RateLimiter:
    """Sliding window rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 120, heavy_limit_per_minute: int = 20) -> None:
        self.requests_per_minute = requests_per_minute
        self.heavy_limit_per_minute = heavy_limit_per_minute
        self._history: dict[str, list[float]] = defaultdict(list)
        self._heavy_history: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, client_ip: str, is_heavy: bool = False) -> tuple[bool, int]:
        """Check if client IP exceeded rate limits.

        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        window_start = now - 60.0

        history = self._heavy_history if is_heavy else self._history
        limit = self.heavy_limit_per_minute if is_heavy else self.requests_per_minute

        # Prune old timestamps
        timestamps = [ts for ts in history[client_ip] if ts > window_start]
        history[client_ip] = timestamps

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + 60.0 - now))
            return True, retry_after

        timestamps.append(now)
        return False, 0


limiter = RateLimiter(requests_per_minute=240, heavy_limit_per_minute=30)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware to enforce rate limiting and security headers."""

    HEAVY_PATHS: ClassVar[set[str]] = {"/api/v1/experiments", "/experiments"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health check and docs
        path = request.url.path
        if (
            path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        # Allow test client or local overrides if configured
        client_ip = request.client.host if request.client else "127.0.0.1"
        is_heavy = request.method == "POST" and any(path.startswith(p) for p in self.HEAVY_PATHS)

        limited, retry_after = limiter.is_rate_limited(client_ip, is_heavy=is_heavy)
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
