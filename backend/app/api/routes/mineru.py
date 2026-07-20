"""
MinerU engine admin routes — inspect the running mineru-api (which now lands on
an auto-picked free port) and restart it on demand.
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
    proc = mgr._process  # noqa: SLF001 — read-only introspection
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
    """Report the current MinerU engine state (auto-picked port + health)."""
    return _status_payload()


@router.post("/restart", dependencies=[Depends(verify_token)])
async def mineru_restart() -> dict[str, Any]:
    """Stop mineru-api and start it again (lands on a fresh free port in
    auto-port mode). Returns the post-restart status."""
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
