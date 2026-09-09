"""Global API authentication middleware (2026-09-09).

Intercepts every ``/api/*`` request and enforces token auth:

  1. MCP service token (env ``MCP_AUTH_TOKEN``)  -> identity ``mcp-service``, full access
  2. User API token (``sk-...`` from /api/v1/auth/tokens) -> identity = owning user
  3. Legacy shared token (``KB_AUTH_TOKEN``)     -> identity ``legacy-admin`` (compat)

Anything else gets ``401 {"error": "unauthorized", ...}``.

Whitelisted (no token required):
  * ``/api/v1/health``                        — liveness for ragctl / monitors
  * ``/api/v1/auth/register|login|verify``    — auth bootstrap endpoints
  * static/docs paths are outside ``/api/*``  — untouched by design

When ``server.auth.enabled=false`` (maintenance escape hatch) the middleware
lets everything through — the default is now **true** per product decision.
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_config
from app.services import auth_service

logger = logging.getLogger(__name__)

# Paths that never require a token (exact or prefix match on the path only).
WHITELIST_EXACT = {
    "/api/v1/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/verify",
}

MCP_IDENTITY = {"id": "svc-mcp", "username": "mcp-service", "role": "service"}
LEGACY_IDENTITY = {"id": "svc-legacy", "username": "legacy-admin", "role": "admin"}


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.headers.get("x-kb-token", "").strip()


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": True, "error_type": "unauthorized",
                 "message": f"认证失败: {detail}",
                 "hint": "请在 Authorization 头携带 Bearer <token>；"
                         "通过 /api/v1/auth/register 注册、/auth/login 登录、/auth/tokens 创建 token"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)  # docs/static live outside /api/*

        if path in WHITELIST_EXACT or path.rstrip("/") in WHITELIST_EXACT:
            return await call_next(request)

        cfg = get_config()
        if not cfg.auth_enabled:
            return await call_next(request)  # maintenance mode

        token = _extract_token(request)
        if not token:
            return _unauthorized("缺少 token")

        # 1) dedicated MCP service token
        if auth_service.is_mcp_token(token):
            request.state.auth_user = dict(MCP_IDENTITY, via="mcp")
            request.state.auth_scopes = ["read", "write", "admin"]
            return await call_next(request)

        # 2) per-user API token
        result = auth_service.verify_access_token(token)
        if result is not None:
            u, t = result["user"], result["token"]
            request.state.auth_user = {
                "id": u["id"], "username": u["username"], "role": u["role"], "via": "user-token",
            }
            request.state.auth_scopes = t.get("scopes", [])
            return await call_next(request)

        # 3) legacy shared token (backwards compat with KB_AUTH_TOKEN)
        legacy = cfg.auth_token
        if legacy and secrets_compare(token, legacy):
            request.state.auth_user = dict(LEGACY_IDENTITY, via="legacy-shared")
            request.state.auth_scopes = ["read", "write", "admin"]
            return await call_next(request)

        reason = "token 无效、已撤销或已过期"
        return _unauthorized(reason)


def secrets_compare(a: str, b: str) -> bool:
    import secrets as _s
    return _s.compare_digest(a or "", b or "")
