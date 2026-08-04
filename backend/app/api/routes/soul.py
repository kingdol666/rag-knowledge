"""SOUL API 路由 — /api/v1/soul/*

对齐 experience.py 路由模式: GET 免鉴权,写操作 Depends(verify_token)。
MCP 工具为薄封装;长任务(learn/learn-all/ask-async)由 kb-mcp 层 task_registry 包裹。
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from app.api.deps.auth import verify_token
from app.services import soul_config, soul_service, soul_router
from app.services import soul_learn, soul_memory, soul_profile
from app.services import soul_task_runner
from app.services.agent_harness_manager import agent_harness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/soul", tags=["soul"])


def _err(status: int, code: str, detail: str = "") -> HTTPException:
    return HTTPException(status_code=status, detail={"error": code, "detail": detail})




async def _finish_run_with_metrics(run_id: str, rep: dict) -> None:
    """结束训练运行: 从最终 report 汇总指标写入 SQLite(runs 表)。"""
    from app.services import soul_training_db
    per_round = rep.get("per_round") or []
    reward = rep.get("reward")
    if reward is None and per_round:
        rewards = [r.get("reward") for r in per_round if r.get("reward") is not None]
        if rewards:
            reward = rewards[-1]
    soul_training_db.set_metrics(
        run_id,
        questions=rep.get("questions_generated"),
        memories=rep.get("memories_created"),
        docs=rep.get("docs_processed"),
        rounds=rep.get("rounds_completed"),
        cost_usd=rep.get("cost_estimate"),
        reward=reward,
    )
    soul_training_db.finish_run(run_id, "done", rep)


def backend_output_tmp() -> str:
    """tmp 目录(与 parse 路由同源): backend/tmp 或系统 temp。"""
    try:
        from app.services.mineru_service import _resolve_output_dir  # noqa
    except Exception:
        pass
    repo_root = Path(__file__).resolve().parents[4]
    tmp_dir = repo_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_dir)




@router.post("/qdcvr-ask")
async def soul_qdcvr_ask(req: dict[str, Any]):
    """QDCVR + SOUL 组合问答: 先检索知识库(两阶段+去重+硬阈值), 再注入人格增强回答。"""
    query = (req.get("query") or "").strip()
    if not query or len(query) > 4000:
        raise _err(400, "invalid_query", "query 长度 1-4000")
    result = await soul_service.soul_qdcvr_ask(
        query=query,
        soul_kb_id=req.get("soul_kb_id") or "",
        task_goal=req.get("task_goal") or "",
        task_type=req.get("task_type") or "",
        top_k=int(req.get("top_k") or 5),
    )
    if not result.get("success"):
        code = result.get("error", "internal")
        status = 408 if code == "timeout" else (404 if code == "kb_not_found" else 400)
        raise _err(status, code, result.get("detail", ""))
    return result


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
    """列出全部非模板 SOUL 库(含 profile 摘要与配置 + meditation 运行摘要)。"""
    souls = []
    for item in soul_config.list_soul_kbs(include_template=False):
        kb_id = item["kb_id"]
        try:
            cfg = soul_config.read_soul_config(kb_id)
            summary = soul_profile.read_profile_summary(kb_id)
        except Exception:
            cfg = soul_config.SoulConfig()
            summary = ""
        # meditation 摘要(harness/model/定时状态)
        med = {}
        try:
            from app.services.kb_meditation_config import get_meditation_config
            mc = get_meditation_config(kb_id).get("config", {})
            med = {
                "harness": mc.get("harness", "omp"),
                "model": mc.get("model", ""),
                "enabled": bool(mc.get("enabled", False)),
                "meditation_mode": mc.get("meditation_mode", "experience"),
                "interval_hours": mc.get("interval_hours", 24),
                "rounds_per_run": int(mc.get("rounds_per_run", 1) or 1),
                "max_questions_per_run": int(mc.get("max_questions_per_run", 10) or 10),
                "max_budget_usd": float(mc.get("max_budget_usd", 0.15) or 0.15),
            }
        except Exception:
            pass
        souls.append({
            "kb_id": kb_id,
            "name": item.get("name", ""),
            "summary": summary[:200],
            "kb_scope": cfg.kb_scope,
            "domain_labels": cfg.domain_labels,
            "supported_task_types": cfg.supported_task_types,
            "is_template": bool(cfg.is_template),
            "meditation": med,
        })
    return souls


@router.get("/settings")
async def soul_settings():
    """SOUL 系统级设置: 默认 harness/model + 各 harness 可用性。"""
    from app.config import config as _cfg
    harness_status = await agent_harness.get_all_harness_status()
    return {
        "success": True,
        "default_harness": _cfg.soul_default_harness,
        "default_model": _cfg.soul_default_model,
        "harnesses": harness_status.get("harnesses", {}),
    }


@router.post("/init")
async def soul_init(req: dict[str, Any]):
    """后端侧初始化(库已由 kb-mcp 层经 web API 创建后调用)。

    等价于 /bootstrap(兼容 §11.1 契约)。模板库创建亦走此路径。
    """
    soul_kb_id = (req.get("soul_name") or req.get("soul_kb_id") or "").strip()
    return await _bootstrap_impl(
        soul_kb_id,
        kb_scope=req.get("kb_scope") if req.get("kb_scope") else ["*"],
        domain_labels=req.get("domain_labels") or [],
        supported_task_types=req.get("supported_task_types") or [],
        harness=req.get("harness") or "",
        model=req.get("model") or "",
    )


@router.post("/bootstrap")
async def soul_bootstrap(req: dict[str, Any]):
    """soul_init 后半段: soul-config.yml 原子写 + 初始 profile-summary + meditation config + 子目录。"""
    soul_kb_id = (req.get("soul_kb_id") or "").strip()
    return await _bootstrap_impl(
        soul_kb_id,
        kb_scope=req.get("kb_scope") if req.get("kb_scope") else ["*"],
        domain_labels=req.get("domain_labels") or [],
        supported_task_types=req.get("supported_task_types") or [],
        harness=req.get("harness") or "",
        model=req.get("model") or "",
    )


async def _bootstrap_impl(soul_kb_id: str, kb_scope: list[str],
                          domain_labels: list[str], supported_task_types: list[str],
                          harness: str = "", model: str = "") -> dict:
    if not soul_kb_id:
        raise _err(400, "invalid_soul_name", "名称必须以 soul- 前缀开头")
    # UUID 或路径 → 相对路径(前缀校验含在解析内: 非 soul- 库返回 None)
    resolved = soul_config.resolve_soul_kb_path(soul_kb_id)
    if not resolved:
        raise _err(400, "invalid_soul_name", "名称必须以 soul- 前缀开头且为已存在的 SOUL 库")
    if not soul_config.resolve_soul_kb_path(resolved):
        raise _err(404, "kb_not_found", "库不存在(请先经 web API 创建)")
    valid, reasons = soul_config.validate_scope(kb_scope)
    if any(r == "scope_contains_soul_kb" for r in reasons):
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
        from app.config import config as _app_config
        default_harness = _app_config.soul_default_harness
        updates: dict[str, Any] = {
            "meditation_mode": "soul",
            "enabled": False,
            "max_budget_usd": 0.15,
            "max_questions_per_run": 10,
        }
        # harness/model: 显式传入优先, 否则全局默认(配置驱动)
        updates["harness"] = (harness or default_harness).strip() or default_harness
        updates["model"] = model or _app_config.soul_default_model
        update_meditation_config(soul_kb_id, updates)
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
        if any(r == "scope_contains_soul_kb" for r in reasons):
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
    """自主学习。async_mode=True 时后端异步执行并返回 task_id
    (GET /api/v1/soul/tasks/{task_id} 轮询进度), 默认同步(兼容旧调用方)。

    训练协程用 asyncio.shield 保护: 客户端断开/超时不取消训练,
    长轮次训练(rounds>1)仍完整执行到最后一轮。
    """
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    if soul_config.is_template_kb(soul_kb_id):
        raise _err(400, "is_template")
    doc_paths = req.get("doc_paths") or []
    limit = int(req.get("limit") or 5)
    rounds = int(req.get("rounds") or 1)
    if not doc_paths:
        raise _err(400, "missing_docs", "doc_paths 必填")
    if req.get("async_mode"):
        from app.services import soul_training_db

        async def _task(tid: str):
            gate_cb = await soul_task_runner.gated_progress_cb(tid)
            run_id = soul_training_db.start_run(
                soul_config.resolve_soul_kb_path(soul_kb_id) or soul_kb_id,
                "soul_learn", task_id=tid, mode="docs")

            async def _cb(p):
                await gate_cb(p)
                soul_training_db.log_event(run_id, p.get("phase", "info"), p)
                soul_training_db.update_progress(
                    run_id, questions=p.get("questions"),
                    memories=p.get("memories"),
                    docs=p.get("docs_processed"),
                    rounds=p.get("round"),
                    cost_usd=p.get("cost_estimate"),
                    reward=p.get("reward"))

            rep = await asyncio.shield(soul_learn.learn_docs(
                soul_kb_id, doc_paths, limit=limit, rounds=rounds,
                progress_cb=_cb))
            await _finish_run_with_metrics(run_id, rep)
            return rep
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_learn",
            {"soul_kb_id": soul_kb_id, "doc_paths": len(doc_paths), "rounds": rounds})
        return {"success": True, "task_id": task_id, "status": "running"}
    report = await asyncio.shield(soul_learn.learn_docs(soul_kb_id, doc_paths, limit=limit, rounds=rounds))
    return {"success": True, "task_id": None, "report": report}


@router.post("/learn-all")
async def learn_all_global(req: dict[str, Any], _: None = Depends(verify_token)):
    """全库自举: 遍历全部 SOUL × kb_scope(不指定 soul_kb_id 时)。"""
    max_docs = int(req.get("max_docs") or 20)
    dry_run = bool(req.get("dry_run"))
    rounds = int(req.get("rounds") or 1)
    if req.get("async_mode"):
        from app.services import soul_training_db

        async def _task(tid: str):
            gate_cb = await soul_task_runner.gated_progress_cb(tid)
            run_id = soul_training_db.start_run("*", "soul_learn_all", task_id=tid, mode="all")

            async def _cb(p):
                await gate_cb(p)
                soul_training_db.log_event(run_id, p.get("phase", "info"), p)
                soul_training_db.update_progress(
                    run_id, questions=p.get("questions"),
                    memories=p.get("memories"), docs=p.get("docs_processed"),
                    rounds=p.get("round"), cost_usd=p.get("cost_estimate"),
                    reward=p.get("reward"))

            rep = await asyncio.shield(soul_learn.learn_all(
                soul_kb_id="", max_docs=max_docs, dry_run=dry_run, rounds=rounds,
                progress_cb=_cb))
            await _finish_run_with_metrics(run_id, rep)
            return rep
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_learn_all", {"soul_kb_id": "*", "max_docs": max_docs, "rounds": rounds})
        return {"success": True, "task_id": task_id, "status": "running"}
    report = await asyncio.shield(soul_learn.learn_all(soul_kb_id="", max_docs=max_docs, dry_run=dry_run, rounds=rounds))
    return {"success": True, "task_id": None, "report": report}


@router.post("/{soul_kb_id}/learn-all")
async def learn_all(soul_kb_id: str, req: dict[str, Any], _: None = Depends(verify_token)):
    max_docs = int(req.get("max_docs") or 20)
    dry_run = bool(req.get("dry_run"))
    rounds = int(req.get("rounds") or 1)
    if req.get("async_mode"):
        from app.services import soul_training_db

        async def _task(tid: str):
            gate_cb = await soul_task_runner.gated_progress_cb(tid)
            run_id = soul_training_db.start_run(
                soul_config.resolve_soul_kb_path(soul_kb_id) or soul_kb_id or "",
                "soul_learn_all", task_id=tid, mode="all")

            async def _cb(p):
                await gate_cb(p)
                soul_training_db.log_event(run_id, p.get("phase", "info"), p)
                soul_training_db.update_progress(
                    run_id, questions=p.get("questions"),
                    memories=p.get("memories"), docs=p.get("docs_processed"),
                    rounds=p.get("round"), cost_usd=p.get("cost_estimate"),
                    reward=p.get("reward"))

            rep = await asyncio.shield(soul_learn.learn_all(
                soul_kb_id=soul_kb_id or "", max_docs=max_docs, dry_run=dry_run, rounds=rounds,
                progress_cb=_cb))
            await _finish_run_with_metrics(run_id, rep)
            return rep
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_learn_all",
            {"soul_kb_id": soul_kb_id or "", "max_docs": max_docs, "rounds": rounds})
        return {"success": True, "task_id": task_id, "status": "running"}
    report = await asyncio.shield(soul_learn.learn_all(soul_kb_id=soul_kb_id or "", max_docs=max_docs, dry_run=dry_run, rounds=rounds))
    return {"success": True, "task_id": None, "report": report}


@router.get("/tasks")
async def list_tasks(status: str = ""):
    """列出最近 SOUL 长任务(训练/审批), 可选 status 过滤。"""
    return {"success": True, "tasks": soul_task_runner.list_soul_tasks(status)}


@router.get("/tasks/{task_id}")
async def task_status(task_id: str):
    """SOUL 长任务进度: {status, progress, result, error, elapsed_seconds}。"""
    rec = soul_task_runner.get_soul_task(task_id)
    if not rec:
        raise _err(404, "task_not_found")
    return {"success": True, **soul_task_runner.public_task_view(rec)}


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
    draft_ids = req.get("draft_ids") or []
    if isinstance(draft_ids, str):
        draft_ids = [draft_ids]
    if not draft_ids and req.get("draft_id"):
        draft_ids = [req["draft_id"]]
    force = bool(req.get("force"))
    if action in ("approve", "reject") and len(draft_ids) > 1:
        # 批量审批异步化: 单条审批含向量/图谱/BM25 索引 + profile 刷新(可达 ~20s/条),
        # 批量串行同步会超时; async_mode=True(默认) 提交到 soul_task_runner 立即返回 task_id
        if req.get("async_mode", True):
            async def _task(tid: str):
                ok: list[dict] = []
                bad: list[dict] = []
                for i, did in enumerate(draft_ids):
                    if action == "approve":
                        r = await soul_memory.approve_draft(
                            soul_kb_id, did, force=force, draft_type=draft_type)
                    else:
                        r = await soul_memory.reject_draft(
                            soul_kb_id, did, draft_type=draft_type)
                    (ok if r.get("success") else bad).append({**r, "draft_id": did})
                    soul_task_runner.update_progress(tid, {
                        "processed": i + 1, "total": len(draft_ids),
                        "approved": len(ok), "rejected": len(bad), "action": action,
                    })
                if bad and not ok:
                    return {"success": False, "error": bad[0].get("error", "approve_failed"),
                            "detail": bad[0].get("detail", ""), "results": ok + bad}
                merged: dict = {"success": True, "results": ok + bad}
                for key in ("approved", "indexed"):
                    vals = [r[key] for r in ok if isinstance(r.get(key), (bool, list))]
                    if vals and isinstance(vals[0], list):
                        merged[key] = [v for lst in vals for v in lst]
                    elif vals:
                        merged[key] = all(vals)
                if bad:
                    merged["partial_failures"] = [
                        {"draft_id": r.get("draft_id", ""), "error": r.get("error")} for r in bad]
                return merged
            task_id = soul_task_runner.submit_soul_task(
                _task, "soul_review",
                {"soul_kb_id": soul_kb_id, "action": action,
                 "draft_ids": len(draft_ids), "draft_type": draft_type})
            return {"success": True, "task_id": task_id, "status": "running",
                    "total": len(draft_ids), "action": action}
        # 同步批量(显式 async_mode=False)
        results: list[dict] = []
        for did in draft_ids:
            if action == "approve":
                results.append({**await soul_memory.approve_draft(
                    soul_kb_id, did, force=force, draft_type=draft_type),
                    "draft_id": did})
            else:
                results.append({**await soul_memory.reject_draft(
                    soul_kb_id, did, draft_type=draft_type),
                    "draft_id": did})
        ok = [r for r in results if r.get("success")]
        bad = [r for r in results if not r.get("success")]
        if bad and not ok:
            raise _err(400, bad[0].get("error", "approve_failed"), bad[0].get("detail", ""))
        merged: dict = {"success": True, "results": results}
        for key in ("approved", "indexed"):
            vals = [r[key] for r in ok if isinstance(r.get(key), (bool, list))]
            if vals and isinstance(vals[0], list):
                merged[key] = [v for lst in vals for v in lst]
            elif vals:
                merged[key] = all(vals)
        if bad:
            merged["partial_failures"] = [
                {"draft_id": r.get("draft_id", ""), "error": r.get("error")} for r in bad]
        return merged
    draft_id = (draft_ids or [""])[0] if draft_ids else ""
    if action == "approve":
        result = await soul_memory.approve_draft(
            soul_kb_id, draft_id, force=force, draft_type=draft_type)
        if not result.get("success"):
            raise _err(400, result.get("error", "approve_failed"), result.get("detail", ""))
        return {"success": True, **result}
    if action == "reject":
        return {"success": True, **await soul_memory.reject_draft(
            soul_kb_id, draft_id, draft_type=draft_type)}
    raise _err(400, "invalid_action", "action ∈ list|approve|reject")


@router.post("/{soul_kb_id}/train-rl")
async def train_rl(soul_kb_id: str, req: dict[str, Any], _: None = Depends(verify_token)):
    """RL 强化训练(好奇心探索 × 评价 Agent × 策略更新)。

    async_mode=True(默认): 后端异步执行并返回 task_id, GET /api/v1/soul/tasks/{id}
    轮询进度(progress: {phase: learn|reward, round, rounds, reward, drafts_created})。

    每轮: 1) learn_incremental 好奇心学习 2) evaluate_persona 评价 Agent 四维打分
    3) generate_cognition_drafts 低分维度 → 认知草稿(待审批, 审批后合并入
    soul-definition.md 对应章节, 实现"评价驱动的结构优化")
    """
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    if soul_config.is_template_kb(soul_kb_id):
        raise _err(400, "is_template")
    rounds = max(1, int(req.get("rounds") or 1))

    from app.services import soul_reward

    if req.get("async_mode", True):
        from app.services import soul_training_db

        async def _task(tid: str):
            gate_cb = await soul_task_runner.gated_progress_cb(tid)
            run_id = soul_training_db.start_run(
                soul_config.resolve_soul_kb_path(soul_kb_id) or soul_kb_id,
                "soul_train_rl", task_id=tid, mode="rl")

            async def _cb(p):
                await gate_cb(p)
                soul_training_db.log_event(run_id, p.get("phase", "info"), p)
                soul_training_db.update_progress(
                    run_id, questions=p.get("questions"),
                    memories=p.get("memories"), docs=p.get("docs_processed"),
                    rounds=p.get("round"), cost_usd=p.get("cost_estimate"),
                    reward=p.get("reward"))

            rep = await asyncio.shield(soul_reward.train_rl(
                soul_kb_id, rounds=rounds, progress_cb=_cb))
            await _finish_run_with_metrics(run_id, rep)
            return rep
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_train_rl", {"soul_kb_id": soul_kb_id, "rounds": rounds})
        return {"success": True, "task_id": task_id, "status": "running"}
    report = await asyncio.shield(soul_reward.train_rl(soul_kb_id, rounds=rounds))
    return {"success": True, "task_id": None, "report": report}


@router.post("/{soul_kb_id}/evaluate")
async def evaluate(soul_kb_id: str, _: None = Depends(verify_token)):
    """评价 Agent 对人格当前表现的四维评分(RL 奖励信号, 可单独调用)。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    from app.services import soul_reward
    return {"success": True, **await soul_reward.evaluate_persona(soul_kb_id)}


@router.post("/{soul_kb_id}/cognition-drafts")
async def gen_cognition_drafts(soul_kb_id: str, req: dict[str, Any],
                               _: None = Depends(verify_token)):
    """生成认知草稿(策略更新建议): 基于一次即时评价, 低分维度产出优化行。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    from app.services import soul_reward
    evaluation = req.get("evaluation") or await soul_reward.evaluate_persona(soul_kb_id)
    if req.get("async_mode", True):
        async def _task(tid: str):
            return await asyncio.shield(soul_reward.generate_cognition_drafts(
                soul_kb_id, evaluation,
            ))
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_cognition", {"soul_kb_id": soul_kb_id})
        return {"success": True, "task_id": task_id, "status": "running",
                "evaluation": evaluation}
    return {"success": True, **await soul_reward.generate_cognition_drafts(
        soul_kb_id, evaluation)}


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
        min_score=float(req["min_score"]) if "min_score" in req and req["min_score"] is not None else 4.0,
        limit=int(req.get("limit") or 1000))
    return {"success": True, **result}


@router.get("/{soul_kb_id}/reward-history")
async def reward_history(soul_kb_id: str, limit: int = Query(50)):
    """RL 进化曲线: reports/reward-history.jsonl 逐轮 reward/四维得分。"""
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    from app.services.soul_reward import read_reward_history
    records = read_reward_history(soul_kb_id, limit=limit)
    return {"success": True, "records": records, "count": len(records)}


@router.get("/{soul_kb_id}/persona-docs")
async def persona_docs(soul_kb_id: str):
    """人格定义文档(宪法层 4 文档)内容列表 — 供前端定义查看器渲染。

    返回 {docs: [{name, content, updated_at}], evolution_lines: N}
    每个文档为原始 markdown; evolution_lines 为该文档中 RL 认知草稿
    追加行数(以 cognition-drafts 已批准草稿统计)。
    """
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    from app.services import soul_reward
    return {"success": True, **await soul_reward.read_persona_docs(soul_kb_id)}



@router.get("/{soul_kb_id}/folder")
async def soul_folder(soul_kb_id: str):
    """SOUL 文件夹架构总览 — 返回全部分区及其文件列表。

    返回 ``{success, structure: {sections: [{key, name, description, entries: [...]}]}}``。
    每个 entry: ``{name, type(md|json|yaml|jsonl|text), size, mtime, content?, meta?}``。
    空目录也有 entries:[] + 用途描述。
    """
    if not soul_config.resolve_soul_kb_path(soul_kb_id):
        raise _err(404, "kb_not_found")
    from app.services import soul_folder as _sf
    result = _sf.read_soul_folder(soul_kb_id)
    if not result.get("success"):
        raise _err(404, result.get("error", "unknown"))
    return result

# ═══════════════════════════════════════════════════════════════════════
# §任务控制 + 训练历史 + 补天蒸馏(前端/CLI/Agent 三入口)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str, _: None = Depends(verify_token)):
    """暂停运行中的 SOUL 长任务(训练/审批)。在下一轮边界生效,
    当前 LLM 调用不中断。SQLite 训练历史同步标记 paused。"""
    if not soul_task_runner.pause_soul_task(task_id):
        raise _err(400, "task_not_pausable", "任务不存在或已结束")
    from app.services import soul_training_db
    run = soul_training_db.get_run_by_task(task_id)
    if run:
        soul_training_db.mark_paused(run["id"])
    return {"success": True, "task_id": task_id, "status": "paused"}


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, _: None = Depends(verify_token)):
    """继续已暂停的任务。"""
    if not soul_task_runner.resume_soul_task(task_id):
        raise _err(400, "task_not_resumable", "任务不存在或未暂停")
    from app.services import soul_training_db
    run = soul_training_db.get_run_by_task(task_id)
    if run:
        soul_training_db.mark_resumed(run["id"])
    return {"success": True, "task_id": task_id, "status": "running"}


@router.get("/training/history")
async def training_history(soul_kb_id: str = "", limit: int = Query(30)):
    """训练历史(SQLite 持久化): 最近运行列表(含 reward/成本/轮次)。
    soul_kb_id 接受 UUID 或路径名(统一解析为路径名查询)。"""
    from app.services import soul_training_db
    if soul_kb_id:
        soul_kb_id = soul_config.resolve_soul_kb_path(soul_kb_id) or soul_kb_id
    runs = soul_training_db.list_runs(soul_kb_id=soul_kb_id or "", limit=limit)
    return {"success": True, "runs": runs, "count": len(runs)}


@router.get("/training/runs/{run_id}")
async def training_run_detail(run_id: str):
    """单次训练运行详情 + 阶段事件流(实时进度可视化数据源)。"""
    from app.services import soul_training_db
    run = soul_training_db.get_run(run_id)
    if not run:
        raise _err(404, "run_not_found")
    events = soul_training_db.get_run_events(run_id)
    return {"success": True, "run": run, "events": events}


@router.post("/distill")
async def distill_persona(req: dict[str, Any], _: None = Depends(verify_token)):
    """补天蒸馏创建 SOUL(前端/CLI/Agent 通用入口)。

    输入: {name, kb_scope?, domain_labels?, supported_task_types?, harness?,
           personality_req? 人格需求描述, source_material? 源材料(聊天记录/文档/描述)}

    流程: LLM 蒸馏(agent_harness, soul_distill prompt) → persona.md/work.md/
    meta.json → 建库 + 4 文档(模板+蒸馏融合) + bootstrap + 索引。
    personality_req/source_material 均缺省时退化为模板人格(soul_init 语义)。
    async_mode=True(默认) 异步执行返回 task_id。
    """
    name = (req.get("name") or req.get("soul_name") or "").strip()
    if not name:
        raise _err(400, "invalid_name", "name 必填")
    if not name.startswith("soul-"):
        name = f"soul-{name}"
    personality_req = (req.get("personality_req") or "").strip()
    source_material = (req.get("source_material") or "").strip()
    if not personality_req and not source_material:
        # 无蒸馏输入 → 退化为模板初始化
        from app.services import soul_config as _sc
        scope = req.get("kb_scope") or ["*"]
        labels = req.get("domain_labels") or []
        types = req.get("supported_task_types") or []
        harness = req.get("harness") or ""
        if req.get("async_mode", True):
            async def _task(tid: str):
                return await asyncio.shield(_template_init_soul(
                    name, scope, labels, types, harness, tid))
            task_id = soul_task_runner.submit_soul_task(
                _task, "soul_init", {"soul_name": name})
            return {"success": True, "task_id": task_id, "status": "running",
                    "mode": "template"}
        return {"success": True, "mode": "template",
                **await _template_init_soul(name, scope, labels, types, harness, "")}

    from app.services import soul_distill
    if req.get("async_mode", True):
        async def _task(tid: str):
            return await asyncio.shield(soul_distill.distill_and_create(
                name=name,
                kb_scope=req.get("kb_scope") or ["*"],
                domain_labels=req.get("domain_labels") or [],
                supported_task_types=req.get("supported_task_types") or [],
                harness=req.get("harness") or "",
                personality_req=personality_req,
                source_material=source_material,
                progress_cb=await soul_task_runner.gated_progress_cb(tid)))
        task_id = soul_task_runner.submit_soul_task(
            _task, "soul_distill", {"soul_name": name})
        return {"success": True, "task_id": task_id, "status": "running",
                "mode": "distill"}
    return {"success": True, "mode": "distill",
            **await soul_distill.distill_and_create(
                name=name,
                kb_scope=req.get("kb_scope") or ["*"],
                domain_labels=req.get("domain_labels") or [],
                supported_task_types=req.get("supported_task_types") or [],
                harness=req.get("harness") or "",
                personality_req=personality_req,
                source_material=source_material)}


async def _template_init_soul(name: str, kb_scope: list, domain_labels: list,
                              supported_task_types: list, harness: str,
                              task_id: str) -> dict:
    """模板初始化(与前端 /api/soul/init 同语义, 供 distill 端点退化路径)。"""
    from app.services import soul_training_db
    run_id = soul_training_db.start_run(
        name, "soul_init", task_id=task_id or None, mode="template")
    try:
        from app.services import soul_distill
        rep = await soul_distill.create_from_template(
            name, kb_scope, domain_labels, supported_task_types, harness)
        soul_training_db.finish_run(run_id, "done", rep)
        return rep
    except Exception as e:
        soul_training_db.finish_run(run_id, "error", {"error": str(e)})
        raise


@router.post("/distill-files")
async def distill_files(
    req: Request,
    files: list[UploadFile] = File(default=...),
    _: None = Depends(verify_token),
):
    """补天蒸馏创建 SOUL — 批量上传自定义文档(前端/CLI 通用)。

    支持类型: md/txt/markdown/csv · json(对话导出) · eml/mbox(邮件) ·
    xlsx/xls(表格) · docx · pdf/png/jpg/jpeg/webp/bmp/pptx(MinerU OCR)。
    文件保存到 tmp/soul-distill-<uuid>/ → 逐文件解析为文本(带文件名头)
    → 汇总作为 source_material 进入蒸馏 prompt → 建库 + 4 文档 + 索引。

    其他字段(name/kb_scope/domain_labels/harness/personality_req)以
    multipart form 字段传入; async_mode 默认 True 返回 task_id。
    """
    form = await req.form()
    name = (form.get("name") or form.get("soul_name") or "").strip()
    if not name:
        raise _err(400, "invalid_name", "name 必填")
    if not name.startswith("soul-"):
        name = f"soul-{name}"
    personality_req = (form.get("personality_req") or "").strip()
    kb_scope = (form.get("kb_scope") or "*").split(",")
    kb_scope = [x.strip() for x in kb_scope if x.strip()]
    domain_labels = (form.get("domain_labels") or "").split(",")
    domain_labels = [x.strip() for x in domain_labels if x.strip()]
    supported_task_types = (form.get("supported_task_types") or "").split(",")
    supported_task_types = [x.strip() for x in supported_task_types if x.strip()]
    harness = (form.get("harness") or "").strip()

    if not files:
        raise _err(400, "no_files", "至少上传 1 个文件")

    # 保存到 tmp/soul-distill-<uuid>/
    tmp_root = Path(backend_output_tmp()) / f"soul-distill-{uuid.uuid4().hex[:8]}"
    tmp_root.mkdir(parents=True, exist_ok=True)
    for f in files:
        safe = Path(f.filename or "file").name
        (tmp_root / safe).write_bytes(await f.read())

    from app.services import soul_distill, soul_distill_files, soul_training_db

    async def _task(tid: str):
        gate_cb = await soul_task_runner.gated_progress_cb(tid)
        run_id = soul_training_db.start_run(
            name, "soul_distill", task_id=tid, mode="distill-files")

        async def _cb(p):
            await gate_cb(p)
            soul_training_db.log_event(run_id, p.get("phase", "info"), p)

        try:
            await _cb({"phase": "parse_files", "msg": "解析上传文件…"})
            parsed = await soul_distill_files.parse_uploaded_files(tmp_root, progress_cb=_cb)
            material = parsed["text"]
            if not material.strip():
                raise ValueError(
                    f"全部文件解析失败({len(parsed['skipped'])} 个被跳过), 无可用文本")
            # 文件解析摘要并入需求描述
            file_summary = "；".join(
                f"{f['name']}({f['method']},{f['chars']}字)" for f in parsed["files"])
            req_text = f"{personality_req}\n[已解析文件] {file_summary}".strip()
            rep = await soul_distill.distill_and_create(
                name=name, kb_scope=kb_scope or ["*"],
                domain_labels=domain_labels, supported_task_types=supported_task_types,
                harness=harness, personality_req=req_text,
                source_material=material, progress_cb=_cb)
            await _finish_run_with_metrics(run_id, rep)
            return rep
        except Exception as e:
            soul_training_db.finish_run(run_id, "error", {"error": str(e)})
            raise

    task_id = soul_task_runner.submit_soul_task(
        _task, "soul_distill_files",
        {"soul_name": name, "files": len(files)})
    return {"success": True, "task_id": task_id, "status": "running",
            "mode": "distill-files", "files": len(files),
            "tmp_dir": str(tmp_root)}
