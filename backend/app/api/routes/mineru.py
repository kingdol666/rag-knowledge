"""
MinerU engine admin routes — inspect the dual-mode engine (remote endpoint /
local subprocess with automatic fallback) and restart/re-probe it on demand.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.api.routes.parse import _get_mineru_manager
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mineru", tags=["MinerU Engine"])


def _status_payload() -> dict[str, Any]:
    mgr = _get_mineru_manager()
    if mgr is None:
        return {"running": False, "available": False,
                "message": "MinerU manager not initialized"}
    # Dual-mode facade exposes a rich status(); legacy single managers fall
    # back to the old field-by-field payload.
    status_fn = getattr(mgr, "status", None)
    if callable(status_fn):
        return status_fn()
    proc = getattr(mgr, "_process", None)  # noqa: SLF001 — read-only introspection
    return {
        "available": True,
        "running": mgr.is_running,
        "host": mgr.host,
        "port": mgr.port,
        "api_url": mgr.api_url,
        "pid": proc.pid if proc is not None else None,
    }


@router.get("/status")
async def mineru_status() -> dict[str, Any]:
    """Report the current MinerU engine state: configured mode, effective
    engine (remote/local), remote endpoint availability, and local subprocess
    health. Legacy keys (running/available/api_url) are preserved."""
    return _status_payload()


@router.post("/restart", dependencies=[Depends(verify_token)])
async def mineru_restart() -> dict[str, Any]:
    """Restart the serving engine: local → subprocess restart (fresh free port
    in auto-port mode); remote → re-probe the endpoint. Returns the
    post-restart status."""
    mgr = _get_mineru_manager()
    if mgr is None:
        return {"success": False, "error": "MinerU manager not initialized",
                "status": _status_payload()}
    try:
        ok = mgr.restart(timeout=120.0)
    except Exception as exc:  # noqa: BLE001 — surface failure to the caller
        logger.exception("MinerU restart raised")
        return {"success": False, "error": f"{type(exc).__name__}: {exc}",
                "status": _status_payload()}
    return {"success": ok, "status": _status_payload()}


@router.post("/probe", dependencies=[Depends(verify_token)])
async def mineru_probe() -> dict[str, Any]:
    """Force re-probe the remote endpoint (bypasses the negative cache) and
    return the fresh dual-mode status. Useful right after fixing remote.base_url
    or bringing a self-hosted mineru-api back up."""
    mgr = _get_mineru_manager()
    if mgr is None:
        return {"success": False, "error": "MinerU manager not initialized",
                "status": _status_payload()}
    remote = getattr(mgr, "remote", None)
    if remote is not None:
        remote.probe(force=True)
    return {"success": True, "status": _status_payload()}
