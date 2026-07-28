"""Meditation API Routes — status, run, history, signals, config."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.services.experience_meditation_service import meditation_scheduler
from app.services.agent_harness_manager import agent_harness
from app.services.kb_meditation_config import get_meditation_config, update_meditation_config, get_all_kb_meditation_configs
from app.services.meditation_db import list_signals, update_signal_feedback, list_runs, get_run, get_pending_signals
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meditation", tags=["Meditation"])


# ── Status ─────────────────────────────────────────────────────────

@router.get("/status")
async def meditation_status():
    """Get global meditation status including scheduler, harness health, circuit breaker."""
    scheduler_status = meditation_scheduler.status
    harness_status = await agent_harness.get_all_harness_status()
    kb_configs = get_all_kb_meditation_configs()

    return {
        "success": True,
        "scheduler": scheduler_status,
        "harnesses": harness_status["harnesses"],
        "circuit_breaker": harness_status["circuit_breaker"],
        "kb_configs": kb_configs,
    }


@router.get("/harness-status")
async def harness_status():
    """Get detailed harness health check status."""
    return {"success": True, **(await agent_harness.get_all_harness_status())}


@router.get("/models")
async def meditation_models():
    """Get available OMP models for meditation harness selection.

    Calls `omp models --json` to get the real list of configured models.
    Falls back to a default list if OMP is not available.
    """
    import subprocess, json as _json
    try:
        result = subprocess.run(
            ["omp", "models", "--json"],
            capture_output=True, timeout=15,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = _json.loads(result.stdout)
            models = data.get("models", [])
            # Simplify for frontend consumption
            simplified = []
            for m in models:
                simplified.append({
                    "id": m.get("selector", m.get("id", "")),
                    "name": m.get("name", m.get("id", "")),
                    "provider": m.get("provider", ""),
                    "context_window": m.get("contextWindow", 0),
                    "max_tokens": m.get("maxTokens", 0),
                })
            return {"success": True, "models": simplified, "source": "omp"}
    except Exception as e:
        logger.warning("Failed to get OMP models: %s", e)

    # Fallback: return known defaults
    return {
        "success": True,
        "models": [
            {"id": "", "name": "使用引擎默认模型", "provider": ""},
        ],
        "source": "fallback",
    }
# ── Run ────────────────────────────────────────────────────────────

@router.post("/run", dependencies=[Depends(verify_token)])
async def meditation_run(body: dict = None):
    """Manually trigger a meditation run. body: {kb_id?, trigger?}"""
    body = body or {}
    kb_id = body.get("kb_id", "")
    trigger = body.get("trigger", "manual")

    if kb_id:
        # KB-specific run
        return await _run_kb_meditation(kb_id, trigger)
    else:
        # Global run (all enabled KBs)
        report = await meditation_scheduler.run_meditation_now()
        return {"success": not report.get("error"), "report": report}


async def _run_kb_meditation(kb_id: str, trigger: str) -> dict:
    """Run meditation for a specific KB using agent harness."""
    config_result = get_meditation_config(kb_id)
    if not config_result.get("success"):
        return config_result

    config = config_result["config"]
    kb_path = config_result["kb_path"]

    # Get pending signals
    lookback_days = config.get("interval_hours", 24) // 24 or 7
    signals = get_pending_signals(kb_id, days=lookback_days)

    if not signals:
        return {"success": True, "message": "No pending signals for this KB", "signals_count": 0}

    # Spawn agent
    result = await agent_harness.synthesize_experiences(
        kb_path=kb_path,
        kb_id=kb_id,
        signals=signals,
        kb_config=config,
        trigger=trigger,
    )

    return result


# ── History ─────────────────────────────────────────────────────────

@router.get("/history")
async def meditation_history(kb_id: str = "", limit: int = 20):
    """List recent meditation runs."""
    runs = list_runs(kb_id=kb_id, limit=limit)
    return {"success": True, "count": len(runs), "runs": runs}


@router.get("/history/{run_id}")
async def meditation_run_detail(run_id: int):
    """Get a single run record."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return {"success": True, "run": run}


# ── Signals ─────────────────────────────────────────────────────────

@router.get("/signals")
async def meditation_signals(kb_id: str = "", days: int = 7, limit: int = 100):
    """List meditation signals."""
    signals = list_signals(kb_id=kb_id, days=days, limit=limit)
    return {"success": True, "count": len(signals), "signals": signals}


@router.post("/feedback", dependencies=[Depends(verify_token)])
async def meditation_feedback(body: dict):
    """Update signal feedback. body: {signal_id, feedback: -1|0|1}"""
    signal_id = body.get("signal_id", 0)
    feedback = body.get("feedback", -1)
    if not signal_id:
        raise HTTPException(status_code=400, detail="signal_id required")
    ok = update_signal_feedback(signal_id, feedback)
    return {"success": ok, "signal_id": signal_id, "feedback": feedback}


# ── Config ──────────────────────────────────────────────────────────

@router.get("/config")
async def meditation_config(kb_id: str = ""):
    """Get meditation config for all KBs or a specific KB."""
    if kb_id:
        return get_meditation_config(kb_id)
    configs = get_all_kb_meditation_configs()
    return {"success": True, "count": len(configs), "configs": configs}


@router.put("/config", dependencies=[Depends(verify_token)])
async def meditation_config_update(body: dict):
    """Update meditation config for a KB. body: {kb_id, config: {...}}"""
    kb_id = body.get("kb_id", "")
    updates = body.get("config", {})
    if not kb_id:
        raise HTTPException(status_code=400, detail="kb_id required")
    if not updates:
        raise HTTPException(status_code=400, detail="config required")
    return update_meditation_config(kb_id, updates)
