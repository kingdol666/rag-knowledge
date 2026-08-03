"""SOUL 门面服务 — soul_ask / soul_status / soul_learn 编排。

人格注入问答 + 自主学习 + 度量。编排各 soul 模块:
- 路由(未指定 soul_kb_id 时)
- 人格加载 + persona bundle
- 知识检索(kb_scope 内 two_stage + 图谱邻居合并)
- complete() 合成 + PAS 评分 + language-style 校验
- 同步/异步: 本服务同步执行;异步由 kb-mcp 层 task_registry 包裹(与 meditation_run 同模式)
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from app.utils.paths import get_storage_root
from app.utils.safe_paths import resolve_within

from app.services import soul_config
from app.services import soul_profile
from app.services import soul_router
from app.services import soul_learn
from app.services import soul_memory
from app.services.agent_harness_manager import agent_harness
from app.services.storage_reader_service import storage_reader
from app.services.two_stage_search_service import two_stage_search_service
from app.services.graph_service import graph_service

_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ── 运行上下文(调用计数/预算由调用方持有,complete() 无状态) ──────────

class AskRunContext:
    """soul_ask 单次运行上下文: 记录调用次数与成本(路由成本单列全局池)。"""

    def __init__(self, soul_kb_id: str | None, label: str = "ask"):
        self.soul_kb_id = soul_kb_id
        self.label = label
        self.calls = 0
        self.cost_estimate = 0.0
        self.start = time.time()

    def note_call(self, result: dict) -> None:
        self.calls += 1
        self.cost_estimate += float(result.get("cost_estimate", 0.0))


async def _complete_checked(prompt: str, ctx: AskRunContext, kb_config: dict | None = None,
                            result_schema: dict | None = None, system_prompt_path: str | None = None,
                            timeout_sec: int = 120, expected_output_tokens: int = 512) -> dict:
    """complete() 封装: 计数 + harness 不可用错误标准化。"""
    result = await agent_harness.complete(
        prompt=prompt,
        kb_config=kb_config,
        result_schema=result_schema,
        system_prompt_path=system_prompt_path,
        timeout_sec=timeout_sec,
        expected_output_tokens=expected_output_tokens,
    )
    ctx.note_call(result)
    if not result.get("success"):
        err = result.get("error", "unknown")
        if "circuit" in str(err):
            return {"success": False, "error": "harness_unavailable", "detail": err}
        if err == "timeout":
            return {"success": False, "error": "timeout", "detail": "LLM 调用超时"}
        return {"success": False, "error": "harness_unavailable", "detail": str(err)[:300]}
    return result


def _kb_config_for(soul_kb_id: str) -> dict:
    """从 soul KB 的 meditation 配置取 harness/model(未显式设置时回退全局默认)。"""
    try:
        from app.services.kb_meditation_config import get_meditation_config
        cfg = get_meditation_config(soul_kb_id).get("config", {})
        harness = (cfg.get("harness") or "").strip() or "omp"
        return {"harness": harness, "model": cfg.get("model", "") or ""}
    except Exception:
        try:
            from app.config import config
            return {"harness": config.soul_default_harness, "model": config.soul_default_model}
        except Exception:
            return {"harness": "omp", "model": ""}


# ── 知识检索(kb_scope 内,图谱邻居合并) ────────────────────────────────

def _search_scope(soul_kb_id: str, kb_scope: list[str]) -> list[str] | None:
    """检索范围: kb_scope 空 → 仅人格库自身;含 "*" → None(全库);否则显式公开库。"""
    if "*" in kb_scope:
        return None
    scope = [k for k in kb_scope if k != "*"]
    if not scope:
        return [soul_kb_id]
    return scope


def _merge_graph_neighbors(chunks: list[dict], doc_paths: list[str], limit: int = 20) -> list[dict]:
    """two_stage chunks 与图谱邻居按 doc_path 合并去重(保留 chunk 级结构)。"""
    merged = list(chunks)
    seen_paths = {c.get("path") for c in chunks}
    for dp in doc_paths[:limit]:
        try:
            related = graph_service.get_related_documents(dp, limit=10) or []
        except Exception as e:
            logger.debug("graph neighbor failed for %s: %s", dp, e)
            related = []
        for r in related:
            rp = r.get("doc_path") or r.get("path") or ""
            if rp and rp not in seen_paths:
                # 图谱邻居无 chunk 文本,后续由 self_answer/合成时再检索;此处仅占位标记
                seen_paths.add(rp)
        # 图谱邻居信息已通过 two_stage 的 graph 展开覆盖,不重复注入
    return merged


async def _retrieve_knowledge(soul_kb_id: str, query: str, kb_scope: list[str]) -> dict:
    """检索范围=所选 SOUL 的 kb_scope(空 → 仅人格库自身)。

    返回 {"chunks": [{path, chunk_text, score}], "candidates": [...]}
    """
    scope = _search_scope(soul_kb_id, kb_scope)
    if scope is None:
        # 全库(通配符 *): 跨库均衡检索
        r = two_stage_search_service.search(
            query=query, stage2_top_k=8, enable_graph_expansion=True,
            balance_kbs=True)
    elif len(scope) == 1:
        r = two_stage_search_service.search(
            query=query, kb_id=scope[0], stage2_top_k=8, enable_graph_expansion=True)
    else:
        # 多库: 逐库检索后按 score 合并去重(库间无污染)
        merged_raw: list[dict] = []
        for kid in scope:
            try:
                rr = two_stage_search_service.search(
                    query=query, kb_id=kid, stage2_top_k=8,
                    enable_graph_expansion=True)
            except Exception as e:
                logger.debug("scope search failed for %s: %s", kid, e)
                continue
            if isinstance(rr, dict):
                merged_raw.extend(rr.get("stage2", {}).get("results", []))
        seen_pairs: set[tuple] = set()
        merged: list[dict] = []
        for res in sorted(merged_raw, key=lambda x: x.get("score", 0.0), reverse=True):
            key = (res.get("doc_path", ""), (res.get("content") or "")[:80])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            merged.append(res)
        r = {"stage2": {"results": merged}, "candidates": []}
    results = r.get("stage2", {}).get("results", []) if isinstance(r, dict) else []
    if not results:
        # 兼容旧契约(直接 results 键)
        results = r.get("results", []) if isinstance(r, dict) else []
    chunks: list[dict] = []
    for res in results:
        doc_path = res.get("doc_path") or ""
        sub = res.get("chunks") or []
        if sub:
            # 分组结构(按文档聚合)
            for c in sub:
                chunks.append({
                    "path": doc_path,
                    "chunk_text": c.get("chunk_text") or c.get("text") or c.get("content") or "",
                    "score": float(c.get("score", 0.0) or 0.0),
                })
        else:
            # 扁平结构(每条即一个 chunk)
            chunks.append({
                "path": doc_path,
                "chunk_text": res.get("content") or res.get("chunk_text") or res.get("text") or "",
                "score": float(res.get("score", 0.0) or 0.0),
            })
    # 按 score 降序去重(path+chunk_text 相同)
    seen = set()
    deduped = []
    for c in sorted(chunks, key=lambda x: x["score"], reverse=True):
        key = (c["path"], c["chunk_text"][:80])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return {"chunks": deduped[:16], "candidates": r.get("candidates", [])}


def _build_synthesize_prompt(query: str, chunks: list[dict], persona: dict,
                             memory_summaries: list[str], soul_kb_id: str,
                             context_override: str = "") -> str:
    lines = [
        "## 任务",
        f"用户问题: {query}",
        "",
        "## 人格设定",
        f"persona_definition: {persona.get('soul_def', '')[:1500]}",
        f"persona_values: {persona.get('values', '')[:800]}",
        f"thinking_style: {persona.get('thinking_style', '')[:800]}",
        f"language_style: {'; '.join(soul_profile.language_style_phrases(soul_kb_id))}",
        "",
        "## 知识片段(仅依据这些作答)",
    ]
    for i, c in enumerate(chunks[:16], 1):
        lines.append(f"[{i}] path={c['path']} score={c['score']:.3f}")
        lines.append(c["chunk_text"][:800])
        lines.append("")
    if memory_summaries:
        lines.append("## 人格记忆(参考,可引用)")
        for m in memory_summaries[:10]:
            lines.append(f"- {m[:200]}")
        lines.append("")
    if context_override:
        lines.append("## 临时背景知识(仅本次回答有效,不写入任何记忆)")
        lines.append(context_override[:1000])
        lines.append("")
    return "\n".join(lines)


def _relevance_reason_fallback(chunk: dict) -> str:
    return f"检索相似度 {chunk.get('score', 0.0):.2f}"


async def _pas_score(answer: str, persona: dict, ctx: AskRunContext, kb_config: dict,
                     soul_kb_id: str) -> tuple[float | None, dict | None]:
    """PAS 评分(独立提示词,与四维评分正交)。失败 → (None, None)。"""
    phrases = soul_profile.language_style_phrases(soul_kb_id)
    prompt = (
        f"## 待评估答案\n<USER_CONTENT>\n{answer[:4000]}\n</USER_CONTENT>\n\n"
        f"## 人格设定\n{persona.get('soul_def', '')[:1200]}\n\n"
        f"## 价值观\n{persona.get('values', '')[:600]}\n\n"
        f"## 语言风格短语\n{'、'.join(phrases)}"
    )
    r = await _complete_checked(
        prompt, ctx, kb_config=kb_config,
        system_prompt_path=str(_PROMPTS_DIR / "soul_pas_v1.txt"),
        result_schema={"pas_score": int, "style_adherence": int, "value_alignment": int, "alignment_notes": str},
        timeout_sec=60, expected_output_tokens=120,
    )
    if not r.get("success"):
        return None, None
    parsed = r.get("parsed") or {}
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}
    if not isinstance(parsed, dict):
        parsed = {}
    try:
        pas = float(parsed.get("pas_score", 0))
    except (TypeError, ValueError):
        pas = 0.0
    return min(5.0, max(0.0, pas)), parsed


# ── soul_ask 编排 ──────────────────────────────────────────────────────

async def soul_qdcvr_ask(query: str, soul_kb_id: str = "", task_goal: str = "",
                         task_type: str = "", top_k: int = 5) -> dict:
    """QDCVR + SOUL 组合问答: 先按 knowledgebase-search skill 流程检索知识,
    再注入人格做增强回答。

    检索侧(与 skill Step 2/2.5 对齐):
      - 两阶段检索(scope 感知: 显式人格按 kb_scope, 自动路由跨库)
      - 硬阈值过滤(score >= 0.35)
      - 文档级去重(同 doc 留最高分 chunk)
      - 短内容过滤(<50 chars 丢弃)
      - top_k 片段拼成 context_override 注入人格合成

    合成侧: 与 soul_ask 完全相同(人格注入 + 证据引用锚点校验 + PAS 评分),
    但回答必须基于注入的检索证据。
    """
    # 1. 检索范围: 显式人格 → 其 kb_scope; 自动路由 → 全库
    scope: list[str] | None = None
    if soul_kb_id:
        try:
            cfg = soul_config.read_soul_config(soul_kb_id)
            scope = _search_scope(soul_kb_id, cfg.kb_scope)
        except Exception:
            scope = None

    # 2. 两阶段检索(knowledgebase-search skill Step 2 同引擎)
    if scope is None:
        r = two_stage_search_service.search(
            query=query, stage2_top_k=8, enable_graph_expansion=True, balance_kbs=True)
    elif len(scope) == 1:
        r = two_stage_search_service.search(
            query=query, kb_id=scope[0], stage2_top_k=8, enable_graph_expansion=True)
    else:
        merged_raw: list[dict] = []
        for kid in scope:
            try:
                rr = two_stage_search_service.search(
                    query=query, kb_id=kid, stage2_top_k=8, enable_graph_expansion=True)
            except Exception:
                continue
            if isinstance(rr, dict):
                merged_raw.extend(rr.get("stage2", {}).get("results", []))
        r = {"stage2": {"results": merged_raw}}
    results = r.get("stage2", {}).get("results", []) if isinstance(r, dict) else []

    # 3. 展开为片段 + 文档级去重 + 硬阈值 + 短内容过滤(skill Step 2.5)
    chunks: list[dict] = []
    for res in results:
        doc_path = res.get("doc_path") or ""
        sub = res.get("chunks") or []
        if sub:
            for c in sub:
                chunks.append({
                    "path": doc_path,
                    "chunk_text": c.get("chunk_text") or c.get("text") or c.get("content") or "",
                    "score": float(c.get("score", 0.0) or 0.0),
                })
        else:
            chunks.append({
                "path": doc_path,
                "chunk_text": res.get("content") or res.get("chunk_text") or res.get("text") or "",
                "score": float(res.get("score", 0.0) or 0.0),
            })
    chunks = [c for c in chunks if c["chunk_text"] and len(c["chunk_text"].strip()) >= 50]
    chunks = [c for c in chunks if c["score"] >= 0.35]
    chunks.sort(key=lambda x: x["score"], reverse=True)
    seen_docs: set[str] = set()
    deduped: list[dict] = []
    for c in chunks:
        key = c["path"]
        if key in seen_docs:
            continue
        seen_docs.add(key)
        deduped.append(c)
    top = deduped[:top_k]

    if not top:
        # 无命中: 交给人格诚实降级(soul_ask 空证据会声明盲区)
        result = await soul_ask(query, soul_kb_id, task_goal, task_type, context_override="")
        result["evidence_count"] = 0
        return result

    # 4. 构建注入上下文(带来源标注)
    override = "\n\n---\n\n".join(
        f"[{i + 1}] 来源: {c['path']} (score={c['score']:.3f})\n{c['chunk_text'][:800]}"
        for i, c in enumerate(top)
    )

    # 5. 人格增强合成(与 soul_ask 同链路, 证据已注入)
    result = await soul_ask(query, soul_kb_id, task_goal, task_type, context_override=override)
    result["evidence_count"] = len(top)
    return result


async def soul_ask(query: str, soul_kb_id: str = "", task_goal: str = "",
                   task_type: str = "", context_override: str = "",
                   conversation_id: str = "") -> dict:
    """人格注入问答(sync 路径,65s 墙钟兜底)。

    返回 §11.1 ask 响应结构(含路由字段)。超时 → {"success": False, "error": "timeout"}。
    """
    if not query or len(query) > 4000:
        return {"success": False, "error": "invalid_query", "detail": "query 长度 1-4000"}
    ctx = AskRunContext(soul_kb_id or None)

    try:
        return await asyncio.wait_for(
            _soul_ask_inner(query, soul_kb_id, task_goal, task_type, context_override, ctx),
            timeout=soul_config.SYNTHESIS_TIMEOUT_SECONDS + 5,
        )
    except asyncio.TimeoutError:
        return {"success": False, "error": "timeout",
                "detail": "同步超时,请用 async_mode=true 重试"}
    except ValueError as e:
        return {"success": False, "error": "kb_not_found", "detail": str(e)[:300]}
    except Exception as e:
        logger.exception("soul_ask failed")
        return {"success": False, "error": "internal", "detail": str(e)[:300]}


async def _soul_ask_inner(query: str, soul_kb_id: str, task_goal: str, task_type: str,
                          context_override: str, ctx: AskRunContext) -> dict:
    # 1. 路由(未指定 soul_kb_id)
    selected = soul_kb_id
    route_fields: dict[str, Any] = {
        "selected_soul": None, "route_reason": None, "route_confidence": None,
        "route_candidates": None, "route_uncertain": False,
    }
    if not soul_kb_id:
        rr = await soul_router.route(query, task_goal=task_goal, task_type=task_type)
        ranked = rr.get("ranked", [])
        top1 = rr.get("top1")
        if rr.get("route_uncertain") or not top1:
            route_fields.update({
                "selected_soul": None, "route_uncertain": True,
                "route_reason": "无足够置信度的 SOUL 匹配",
                "route_candidates": [{"kb_id": x["kb_id"], "score": x.get("score")} for x in ranked[:3]],
                "route_confidence": rr.get("route_confidence"),
            })
            return {
                "success": True,
                "answer": "当前查询未能自动匹配到高置信度的人格。请指定 soul_kb_id,或从候选人格中选择。",
                "citations": [], "pas_score": None, "persona_bundle": [],
                "language_style_warning": False, "async_task_id": None,
                **route_fields,
            }
        selected = top1
        route_fields.update({
            "selected_soul": top1,
            "route_reason": next((x.get("reason", "") for x in ranked if x.get("kb_id") == top1), "")[:100],
            "route_confidence": rr.get("route_confidence"),
            "route_candidates": [{"kb_id": x["kb_id"], "score": x.get("score")} for x in ranked[:3]],
            "route_uncertain": False,
        })

    # 2. 校验 soul 库
    kb_path = soul_config.resolve_soul_kb_path(selected)
    if not kb_path:
        return {"success": False, "error": "kb_not_found", "detail": f"非 SOUL 库: {selected}"}
    if soul_config.is_template_kb(selected):
        return {"success": False, "error": "is_template", "detail": "模板库不可直接问答,请先 soul_init"}

    # 3. 人格加载 + bundle
    profile = await soul_profile.load_profile(selected)
    bundle = await soul_profile.build_persona_bundle(selected, query)
    kb_config = _kb_config_for(selected)

    # 4. 知识检索(kb_scope 内)
    kb_scope = profile.get("config", soul_config.SoulConfig()).kb_scope
    knowledge = await _retrieve_knowledge(selected, query, kb_scope)
    chunks = knowledge.get("chunks", [])

    # 5. 合成
    synth_prompt = _build_synthesize_prompt(
        query, chunks, profile, bundle.get("memory_summaries", []), selected,
        context_override)
    synth = await _complete_checked(
        synth_prompt, ctx, kb_config=kb_config,
        system_prompt_path=str(_PROMPTS_DIR / "soul_synthesize_v1.txt"),
        result_schema={"answer_text": str, "citations": [{"path": str, "chunk_text": str, "score": float, "relevance_reason": str}]},
        timeout_sec=soul_config.SYNTHESIS_TIMEOUT_SECONDS, expected_output_tokens=1024,
    )
    if not synth.get("success"):
        return {"success": False, "error": synth.get("error"), "detail": synth.get("detail", "")}
    parsed = synth.get("parsed") or {}
    if isinstance(parsed, list):
        # 模型偶发输出 JSON 数组(如 [{"answer_text": ...}]);取首元素
        parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}
    if not isinstance(parsed, dict):
        parsed = {}
    answer = parsed.get("answer_text") or synth.get("text", "")[:4000]
    # 防御: LLM 偶发把 answer_text 再序列化一次(字符串内是 JSON 对象)
    if isinstance(answer, str) and answer.lstrip().startswith(("{", "[")):
        try:
            inner = json.loads(answer)
            if isinstance(inner, dict) and inner.get("answer_text"):
                answer = inner["answer_text"]
            elif isinstance(inner, dict) and inner.get("text"):
                answer = inner["text"]
        except Exception:
            pass
    if not answer:
        return {"success": False, "error": "harness_unavailable", "detail": "合成无输出"}

    # 6. citations(LLM 输出不稳定时回退代码模板)
    citations = []
    valid_paths = {c["path"] for c in chunks}
    for cit in parsed.get("citations", []) or []:
        if not isinstance(cit, dict):
            # 兼容字符串形态引用(如 "path/to/doc.md")
            if isinstance(cit, str) and cit in valid_paths:
                citations.append({
                    "path": cit,
                    "chunk_text": "",
                    "score": 0.0,
                    "relevance_reason": _relevance_reason_fallback({"score": 0.0}),
                })
            continue
        p = cit.get("path", "")
        if p in valid_paths:
            citations.append({
                "path": p,
                "chunk_text": (cit.get("chunk_text") or "")[:500],
                "score": float(cit.get("score", 0.0) or 0.0),
                "relevance_reason": (cit.get("relevance_reason") or _relevance_reason_fallback({"score": cit.get("score", 0)}))[:200],
            })
    if not citations and chunks:
        for c in chunks[:3]:
            citations.append({
                "path": c["path"], "chunk_text": c["chunk_text"][:500],
                "score": c["score"], "relevance_reason": _relevance_reason_fallback(c),
            })

    # 7. PAS + language-style 校验
    pas_score, pas_parsed = await _pas_score(answer, profile, ctx, kb_config, selected)
    phrases = soul_profile.language_style_phrases(selected)
    style_hits = soul_profile.count_style_matches(answer, phrases)
    lang_warning = style_hits < 2
    if pas_score is not None and lang_warning:
        pas_score = max(0.0, pas_score - 0.5)

    return {
        "success": True,
        "answer": answer,
        "citations": citations,
        "pas_score": pas_score,
        "persona_bundle": bundle.get("doc_names", []),
        "language_style_warning": lang_warning,
        "async_task_id": None,
        **route_fields,
    }


# ── soul_status ────────────────────────────────────────────────────────

async def soul_status(soul_kb_id: str, summary_window: int = 30) -> dict:
    """学习指标(§3.2)。空态返回 0 值,不报错。"""
    kb_path = soul_config.resolve_soul_kb_path(soul_kb_id)
    if not kb_path:
        return {"success": False, "error": "kb_not_found", "detail": f"非 SOUL 库: {soul_kb_id}"}

    try:
        drafts = await soul_memory.list_drafts(soul_kb_id, "memory")
        drafts_count = drafts.get("count", 0) if isinstance(drafts, dict) else 0
    except Exception as e:
        logger.debug("drafts read failed: %s", e)
        drafts_count = 0

    soul_dir = soul_config.soul_kb_dir(soul_kb_id)
    memories_dir = soul_dir / "memories"
    total_memories = 0
    stale_count = 0
    judge_divergence_count = 0
    score_sum = 0.0
    recent_learned: list[dict] = []
    question_count = 0
    if memories_dir.exists():
        for f in sorted(memories_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                fm = _read_frontmatter(f)
            except Exception:
                continue
            if fm.get("status") == "approved":
                total_memories += 1
                if fm.get("stale"):
                    stale_count += 1
                if fm.get("judge_divergence"):
                    judge_divergence_count += 1
                sc = fm.get("scores") or {}
                if isinstance(sc, dict) and sc.get("groundedness") is not None:
                    score_sum += float(sc.get("groundedness", 0))
                    question_count += 1
                if len(recent_learned) < 10:
                    recent_learned.append({
                        "doc_path": fm.get("doc_source", ""),
                        "score": float((fm.get("scores") or {}).get("groundedness", 0) or 0),
                        "learned_at": fm.get("learned_at", ""),
                    })

    gaps = _read_gaps(soul_dir / "questions" / "gaps.md", 10)
    cost = _cost_summary(soul_dir)
    route_stats = await _route_stats_for(soul_kb_id)
    try:
        route_status = await soul_router.get_router_status()
    except Exception:
        route_status = {}
    training_stale = (soul_dir / "training").exists() and any(
        (soul_dir / "training").glob("*.jsonl"))

    return {
        "success": True,
        "soul_kb_id": soul_kb_id,
        "drafts_pending_review": drafts_count,
        "total_memories": total_memories,
        "total_gaps": len(gaps),
        "judge_divergence_count": judge_divergence_count,
        "eval_drift_alert": _eval_drift_alert(soul_dir),
        "stale_memory_count": stale_count,
        "training_stale": training_stale,
        "route_stats": route_stats,
        "route_cost_usd": round(route_status.get("route_cost_usd", 0.0), 4),
        "semaphore_queue_depth": 0,
        "estimated_cost_usd": cost,
        "recent_learned_docs": recent_learned,
        "recent_gaps": [g for g in gaps],
        "mastery": {
            "question_count": question_count,
            "avg_score": round(score_sum / question_count, 2) if question_count else 0.0,
        },
    }


def _read_frontmatter(path: Path) -> dict:
    import yaml
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            return yaml.safe_load(text[3:end]) or {}
    return {}


def _read_gaps(gaps_path: Path, n: int = 10) -> list[str]:
    if not gaps_path.exists():
        return []
    lines = gaps_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    return [ln for ln in lines[-n:] if ln.strip()]


def _cost_summary(soul_dir: Path) -> float:
    log = soul_dir / "audit" / "cost-log.jsonl"
    if not log.exists():
        return 0.0
    total = 0.0
    for ln in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            import json as _json
            total += float(_json.loads(ln).get("cost_estimate", 0))
        except Exception:
            continue
    return round(total, 4)


def _eval_drift_alert(soul_dir: Path) -> bool:
    reports = soul_dir / "reports"
    return reports.exists() and any(reports.glob("eval-drift-*.md"))


async def _route_stats_for(soul_kb_id: str) -> dict | None:
    try:
        st = await soul_router.get_router_status()
        count = (st.get("per_soul_selection_count") or {}).get(soul_kb_id, 0)
        total = st.get("total_routes", 0)
        return {
            "selected_count": count,
            "avg_confidence": 0.0,
            "uncertain_count": 0,
            "selection_ratio": round(count / total, 3) if total else 0.0,
        }
    except Exception:
        return None
