"""Shared-token auth dependency for write/dangerous endpoints.

When ``config.auth_enabled`` is False (default), :func:`verify_token` is a no-op
— zero-config local use is unchanged. When enabled, it requires either:

  * ``Authorization: Bearer <token>`` header, or
  * ``X-KB-Token: <token>`` header

matching the configured token (env ``KB_AUTH_TOKEN`` or runtime-generated).
Mismatches raise 401. GET / read endpoints do not use this dependency.
"""
from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Request, status

from app.config import get_config

logger = logging.getLogger(__name__)


async def verify_token(request: Request) -> None:
    """FastAPI dependency: reject non-read requests without a valid shared token.

    No-op when auth is disabled (the default). Apply to write/dangerous routes
    via ``dependencies=[Depends(verify_token)]``.
    """
    cfg = get_config()
    if not cfg.auth_enabled:
        return  # auth disabled — allow all

    expected = cfg.auth_token
    if not expected:
        # Enabled but no token configured — fail closed (safer than allowing all).
        logger.error(
            "Auth enabled but no token (set KB_AUTH_TOKEN or restart to auto-generate)"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth enabled but no token configured on server",
        )

    # Extract candidate token from either accepted header.
    auth_header = request.headers.get("authorization", "")
    candidate = ""
    if auth_header.lower().startswith("bearer "):
        candidate = auth_header[7:].strip()
    x_token = request.headers.get("x-kb-token", "").strip()
    if not candidate and x_token:
        candidate = x_token

    if candidate and hmac.compare_digest(candidate, expected):
        return  # valid token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: invalid or missing auth token",
    )
