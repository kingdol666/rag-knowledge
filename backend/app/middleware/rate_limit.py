"""Lightweight in-memory rate limiter (sliding-window per client IP).

No external dependencies — uses a simple dict of deques. Suitable for
single-process uvicorn deployments (the default for this project).

For multi-worker deployments, replace with Redis-backed limiter.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── Config (sane defaults; override via config.yml server.rate_limit) ──

_DEFAULT_ENABLED = True
_DEFAULT_WINDOW_SEC = 60          # sliding window size
_DEFAULT_MAX_REQUESTS = 120       # requests per window per IP (general)
_DEFAULT_HEAVY_MAX = 20           # for write-heavy endpoints (parse, mineru)

# Paths that get the stricter "heavy" limit (CPU/IO intensive operations).
_HEAVY_PATH_PREFIXES = (
    "/api/v1/parse",
    "/api/v1/mineru",
)

# Paths exempt from rate limiting (health probes, docs).
_EXEMPT_PATHS = frozenset({
    "/",
    "/health",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RateLimiter:
    """Sliding-window rate limiter — O(1) amortized per request."""

    def __init__(
        self,
        enabled: bool = _DEFAULT_ENABLED,
        window_sec: int = _DEFAULT_WINDOW_SEC,
        max_requests: int = _DEFAULT_MAX_REQUESTS,
        heavy_max: int = _DEFAULT_HEAVY_MAX,
    ) -> None:
        self.enabled = enabled
        self.window_sec = window_sec
        self.max_requests = max_requests
        self.heavy_max = heavy_max
        # general[ip] = deque of timestamps
        self._general: dict[str, deque[float]] = defaultdict(deque)
        self._heavy: dict[str, deque[float]] = defaultdict(deque)
        # Periodic cleanup counter — evict stale entries every N requests
        self._cleanup_counter = 0
        self._cleanup_interval = 500

    def _client_ip(self, request: Request) -> str:
        # Trust X-Forwarded-For only if behind a known proxy; default to direct IP.
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_heavy(self, path: str) -> bool:
        return any(path.startswith(p) for p in _HEAVY_PATH_PREFIXES)

    def _check_bucket(
        self, bucket: dict[str, deque[float]], key: str, limit: int, now: float,
    ) -> tuple[bool, int]:
        """Returns (allowed, remaining). Evicts expired entries in-place."""
        dq = bucket[key]
        cutoff = now - self.window_sec
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= limit:
            return False, 0
        dq.append(now)
        return True, limit - len(dq)

    def _maybe_cleanup(self) -> None:
        """Evict IPs with empty deques to prevent unbounded memory growth."""
        self._cleanup_counter += 1
        if self._cleanup_counter < self._cleanup_interval:
            return
        self._cleanup_counter = 0
        now = time.monotonic()
        cutoff = now - self.window_sec
        for bucket in (self._general, self._heavy):
            stale = [ip for ip, dq in bucket.items() if not dq or dq[-1] < cutoff]
            for ip in stale:
                del bucket[ip]

    def check(self, request: Request) -> tuple[bool, int, int]:
        """Returns (allowed, limit, remaining)."""
        if not self.enabled:
            return True, 0, 0
        path = request.url.path
        if path in _EXEMPT_PATHS:
            return True, 0, 0

        ip = self._client_ip(request)
        now = time.monotonic()
        self._maybe_cleanup()

        if self._is_heavy(path):
            allowed, remaining = self._check_bucket(self._heavy, ip, self.heavy_max, now)
            limit = self.heavy_max
        else:
            allowed, remaining = self._check_bucket(self._general, ip, self.max_requests, now)
            limit = self.max_requests

        return allowed, limit, remaining


# Singleton — configured by main.py during startup
_limiter: RateLimiter | None = None


def init_rate_limiter(config_dict: dict | None = None) -> None:
    """Initialize the global rate limiter from config.yml server.rate_limit."""
    global _limiter
    cfg = (config_dict or {}).get("rate_limit", {})
    _limiter = RateLimiter(
        enabled=cfg.get("enabled", _DEFAULT_ENABLED),
        window_sec=cfg.get("window_sec", _DEFAULT_WINDOW_SEC),
        max_requests=cfg.get("max_requests", _DEFAULT_MAX_REQUESTS),
        heavy_max=cfg.get("heavy_max", _DEFAULT_HEAVY_MAX),
    )
    if _limiter.enabled:
        logger.info(
            "Rate limiter: enabled (general=%d/%ds, heavy=%d/%ds)",
            _limiter.max_requests, _limiter.window_sec,
            _limiter.heavy_max, _limiter.window_sec,
        )
    else:
        logger.info("Rate limiter: disabled")


def get_limiter() -> RateLimiter:
    if _limiter is None:
        init_rate_limiter()
    assert _limiter is not None
    return _limiter


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """ASGI middleware — injects X-RateLimit headers, returns 429 on excess."""
    limiter = get_limiter()
    if not limiter.enabled:
        return await call_next(request)

    allowed, limit, remaining = limiter.check(request)
    if not allowed:
        logger.warning("Rate limit exceeded for %s on %s", limiter._client_ip(request), request.url.path)
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please slow down.",
                "retry_after_sec": limiter.window_sec,
            },
            headers={
                "Retry-After": str(limiter.window_sec),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    response = await call_next(request)
    if limit > 0:
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
