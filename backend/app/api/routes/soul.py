"""SOUL API 路由 — /api/v1/soul/*

对齐 experience.py 路由模式: GET 免鉴权,写操作 Depends(verify_token)。
MCP 工具为薄封装;长任务(learn/learn-all/ask-async)由 kb-mcp 层 task_registry 包裹。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps.auth import verify_token
from app.services import soul_config, soul_service, soul_router
from app.services import soul_learn, soul_memory, soul_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/soul", tags=["soul"])


def _err(status: int, code: str, detail: str = "") -> HTTPException:
    return HTTPException(status_code=status, detail={"error": code, "detail": detail})


@router.post("/ask")
async def soul_ask(req: dict[str, Any]):
    """人格注入问答。async_mode 由 kb-mcp 层处理(本端点同步执行)。"""
    query = (req.get("query") or "").strip()
    if not query:
        raise _err(400, "invalid_query", "query 必填")
    result = await soul_service.soul_ask(
        query=query,
        soul_kb_id=(req.get("soul_kb_id") or "").strip(),
        task_goal=(req.get("task_goal") or "").strip(),
        task_type=(req.get("task_type") or "").strip(),
        context_override=(req.get("context_override") or ""),
        conversation_id=(req.get("conversation_id") or ""),
    )
    if not result.get("success"):
        code = result.get("error", "internal")
        status = 408 if code == "timeout" else (404 if code == "kb_not_found" else 400)
        raise _err(status, code, result.get("detail", ""))
    return result


@router.get("/list")
async def soul_list():
    """列出全部非模板 SOUL 库(含 profile 摘要与配置)。"""
    souls = []
    for item in soul_config.list_soul_kbs(include_template=False):
        kb_id = item["kb_id"]
        try:
            cfg = soul_config.read_soul_config(kb_id)
            summary = soul_profile.read_profile_summary(kb_id)
        except Exception:
            cfg = soul_config.SoulConfig()
            summary = ""
        souls.append({
            "kb_id": kb_id,
            "name": item.get("name", ""),
            "summary": summary[:200],
            "kb_scope": cfg.kb_scope,
            "domain_labels": cfg.domain_labels,
            "supported_task_types": cfg.supported_task_types,
            "is_template": bool(cfg.is_template),
        })
    return souls


@router.post("/init")
async def soul_init(req: dict[str, Any]):
    """后端侧初始化(库已由 kb-mcp 层经 web API 创建后调用)。

    等价于 /bootstrap(兼容 §11.1 契约)。模板库创建亦走此路径。
    """
    soul_kb_id = (req.get("soul_name") or req.get("soul_kb_id") or "").strip()
    return await _bootstrap_impl(
        soul_kb_id,
        kb_scope=req.get("kb_scope") or [],
        domain_labels=req.get("domain_labels") or [],
        supported_task_types=req.get("supported_task_types") or [],
    )


@router.post("/bootstrap")
async def soul_bootstrap(req: dict[str, Any]):
    """soul_init 后半段: soul-config.yml 原子写 + 初始 profile-summary + meditation config + 子目录。"""
    soul_kb_id = (req.get("soul_kb_id") or "").strip()
    return await _bootstrap_impl(
        soul_kb_id,
        kb_scope=req.get("kb_scope") or [],
        domain_labels=req.get("domain_labels") or [],
        supported_task_types=req.get("supported_task_types") or [],
    )


async def _bootstrap_impl(soul_kb_id: str, kb_scope: list[str],
                          domain_labels: list[str], supported_task_types: list[str]) -> dict:
    if not soul_kb_id or not soul_kb_id.startswith(soul_config.SOUL_PREFIX):
        raise _err(400, "invalid_soul_name", "名称必须以 soul- 前缀开头")
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found", "库不存在(请先经 web API 创建)")
    valid, reasons = soul_config.validate_scope(kb_scope)
    if any("soul-" in r for r in reasons):
        raise _err(400, "scope_contains_soul_kb", "; ".join(reasons))
    if kb_scope and not valid:
        raise _err(400, "scope_kb_missing", "; ".join(reasons))

    cfg = soul_config.SoulConfig(
        kb_scope=kb_scope or [],
        is_template=False,
        route_weight=1.0,
        domain_labels=domain_labels or [],
        supported_task_types=supported_task_types or [],
    )
    soul_config.write_soul_config(soul_kb_id, cfg)
    soul_config.ensure_soul_dirs(soul_kb_id)

    # 初始 profile summary(失败不阻塞)
    try:
        summary = await soul_profile.generate_profile_summary(soul_kb_id)
    except Exception as e:
        logger.warning("initial profile summary failed for %s: %s", soul_kb_id, e)
        summary = ""

    # meditation config: mode=soul, enabled=false, budget=0.15
    try:
        from app.services.kb_meditation_config import update_meditation_config
        update_meditation_config(soul_kb_id, {
            "meditation_mode": "soul",
            "enabled": False,
            "max_budget_usd": 0.15,
            "max_questions_per_run": 10,
        })
        meditation_created = True
    except Exception as e:
        logger.warning("meditation config failed for %s: %s", soul_kb_id, e)
        meditation_created = False

    return {
        "success": True,
        "kb_id": soul_kb_id,
        "name": soul_kb_id,
        "soul_config_written": True,
        "profile_summary_generated": bool(summary),
        "meditation_config_created": meditation_created,
    }


@router.put("/{soul_kb_id}/config")
async def soul_config_update(soul_kb_id: str, req: dict[str, Any],
                             _: None = Depends(verify_token)):
    """更新 kb_scope/domain_labels/supported_task_types/route_weight(人工/管理员)。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    if soul_config.is_template_kb(soul_kb_id):
        raise _err(400, "is_template", "模板库配置不可修改")

    cfg = soul_config.read_soul_config(soul_kb_id)
    old_scope = list(cfg.kb_scope)
    if "kb_scope" in req:
        valid, reasons = soul_config.validate_scope(req["kb_scope"] or [])
        if any("soul-" in r for r in reasons):
            raise _err(400, "scope_contains_soul_kb", "; ".join(reasons))
        if req["kb_scope"] and not valid:
            raise _err(400, "scope_kb_missing", "; ".join(reasons))
        cfg.kb_scope = req["kb_scope"] or []
    if "domain_labels" in req:
        cfg.domain_labels = req["domain_labels"] or []
    if "supported_task_types" in req:
        cfg.supported_task_types = req["supported_task_types"] or []
    if "route_weight" in req:
        try:
            cfg.route_weight = max(0.0, min(2.0, float(req["route_weight"])))
        except (TypeError, ValueError):
            raise _err(400, "invalid_route_weight")

    soul_config.write_soul_config(soul_kb_id, cfg)
    soul_router.invalidate_cache(soul_kb_id)

    stale = 0
    if set(old_scope) != set(cfg.kb_scope):
        try:
            stale = await soul_memory.mark_stale_scope(soul_kb_id, soul_config.scope_hash(old_scope))
        except Exception as e:
            logger.warning("stale marking failed: %s", e)

    try:
        await soul_profile.generate_profile_summary(soul_kb_id)
        profile_refreshed = True
    except Exception:
        profile_refreshed = False

    return {
        "success": True,
        "kb_id": soul_kb_id,
        "stale_memory_count": stale,
        "profile_cache_invalidated": True,
        "profile_refreshed": profile_refreshed,
    }


@router.delete("/{soul_kb_id}")
async def soul_delete(soul_kb_id: str, purge_experiences: bool = False,
                      _: None = Depends(verify_token)):
    """删除前自动 checkpoint(快照保留)。KB 删除本身由 kb-mcp 层经 web API 执行。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    try:
        cp = await soul_memory.create_checkpoint(soul_kb_id)
        checkpoint_id = cp.get("checkpoint_id", "")
    except Exception as e:
        logger.warning("pre-delete checkpoint failed: %s", e)
        checkpoint_id = ""
    soul_router.invalidate_cache(soul_kb_id)
    return {
        "success": True,
        "kb_id": soul_kb_id,
        "checkpoint_saved": checkpoint_id,
        "purged": bool(purge_experiences),
        "note": "KB 删除请经 kb-mcp soul_delete 工具(web 层执行)",
    }


@router.post("/router")
async def router_route(req: dict[str, Any]):
    """独立路由工具(可审计入口)。"""
    query = (req.get("query") or "").strip()
    if not query:
        raise _err(400, "invalid_query")
    result = await soul_router.route(
        query, task_goal=(req.get("task_goal") or ""),
        task_type=(req.get("task_type") or ""))
    return {"success": True, **result}


@router.get("/router/status")
async def router_status():
    return {"success": True, **await soul_router.get_router_status()}


@router.get("/{soul_kb_id}/status")
async def status(soul_kb_id: str, summary_window: int = Query(30)):
    result = await soul_service.soul_status(soul_kb_id, summary_window)
    if not result.get("success"):
        raise _err(404, result.get("error", "kb_not_found"), result.get("detail", ""))
    return result


@router.post("/{soul_kb_id}/learn")
async def learn(soul_kb_id: str, req: dict[str, Any], _: None = Depends(verify_token)):
    """自主学习(同步执行;kb-mcp 层包裹为异步任务)。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    if soul_config.is_template_kb(soul_kb_id):
        raise _err(400, "is_template")
    doc_paths = req.get("doc_paths") or []
    limit = int(req.get("limit") or 5)
    if not doc_paths:
        raise _err(400, "missing_docs", "doc_paths 必填")
    report = await soul_learn.learn_docs(soul_kb_id, doc_paths, limit=limit)
    return {"success": True, "task_id": None, "report": report}


@router.post("/{soul_kb_id}/learn-all")
async def learn_all(soul_kb_id: str, req: dict[str, Any], _: None = Depends(verify_token)):
    max_docs = int(req.get("max_docs") or 20)
    dry_run = bool(req.get("dry_run"))
    report = await soul_learn.learn_all(soul_kb_id=soul_kb_id or "", max_docs=max_docs, dry_run=dry_run)
    return {"success": True, "task_id": None, "report": report}


@router.post("/{soul_kb_id}/eval")
async def eval_answer(soul_kb_id: str, req: dict[str, Any]):
    """单条四维自评(AC26)。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    result = await soul_learn.eval_answer(
        req.get("question", ""), req.get("answer", ""),
        req.get("evidence_paths") or [], soul_kb_id)
    return {"success": True, **result}


@router.post("/{soul_kb_id}/checkpoint")
async def checkpoint(soul_kb_id: str, _: None = Depends(verify_token)):
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    return {"success": True, **await soul_memory.create_checkpoint(soul_kb_id)}


@router.post("/{soul_kb_id}/review-drafts")
async def review_drafts(soul_kb_id: str, req: dict[str, Any],
                        _: None = Depends(verify_token)):
    action = req.get("action") or "list"
    draft_type = req.get("type") or "memory"
    if action == "list":
        return {"success": True, **await soul_memory.list_drafts(soul_kb_id, draft_type)}
    if action == "approve":
        result = await soul_memory.approve_draft(
            soul_kb_id, req.get("draft_id") or "", force=bool(req.get("force")))
        if not result.get("success"):
            raise _err(400, result.get("error", "approve_failed"), result.get("detail", ""))
        return {"success": True, **result}
    if action == "reject":
        return {"success": True, **await soul_memory.reject_draft(
            soul_kb_id, req.get("draft_id") or "")}
    raise _err(400, "invalid_action", "action ∈ list|approve|reject")


@router.post("/{soul_kb_id}/calibrate")
async def calibrate(soul_kb_id: str, _: None = Depends(verify_token)):
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    result = await soul_learn.calibrate(soul_kb_id)
    return {"success": True, **result}


@router.post("/{soul_kb_id}/reflect")
async def reflect(soul_kb_id: str, _: None = Depends(verify_token)):
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    return {"success": True, **await soul_memory.reflect(soul_kb_id)}


@router.post("/{soul_kb_id}/rollback")
async def rollback(soul_kb_id: str, req: dict[str, Any], _: None = Depends(verify_token)):
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    result = await soul_memory.rollback_to_checkpoint(
        soul_kb_id, req.get("checkpoint_id") or "")
    if not result.get("success"):
        raise _err(404, result.get("error", "checkpoint_not_found"), result.get("detail", ""))
    return {"success": True, **result}


@router.post("/{soul_kb_id}/export")
async def export_training(soul_kb_id: str, req: dict[str, Any],
                          _: None = Depends(verify_token)):
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    result = await soul_memory.export_training_data(
        soul_kb_id,
        min_score=float(req.get("min_score") or 4.0),
        limit=int(req.get("limit") or 1000))
    return {"success": True, **result}
