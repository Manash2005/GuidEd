import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Per-route limits: (max_requests, window_seconds)
ROUTE_LIMITS: Dict[str, Tuple[int, int]] = {
    "/api/auth/login": (20, 60),
    "/api/auth/register": (15, 60),
    "/api/agent/recommend": (30, 60),
}
DEFAULT_LIMIT: Tuple[int, int] = (120, 60)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._history: Dict[str, Deque[float]] = defaultdict(deque)

    def _get_client_identifier(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Allow disabling during automated test runs via header or attribute
        if not self.enabled or request.headers.get("x-skip-rate-limit") == "true":
            return await call_next(request)

        client_ip = self._get_client_identifier(request)
        path = request.url.path

        limit, window = DEFAULT_LIMIT
        for prefix, (custom_limit, custom_window) in ROUTE_LIMITS.items():
            if path.startswith(prefix):
                limit = custom_limit
                window = custom_window
                break

        key = f"{client_ip}:{path}"
        now = time.time()
        timestamps = self._history[key]

        # Prune expired timestamps
        cutoff = now - window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            retry_after = int(window - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(max(1, retry_after))}
            )

        timestamps.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
