"""SOUL 路由服务 — 查询 → 最优人格匹配。

根据用户查询内容、任务目标与类型，从已注册的 SOUL 人格库中自动选择
最匹配的人格执行回答。核心流程：
1. TTL 缓存检查（(query_hash, task_type) 组合键）
2. 候选收集（排除模板 SOUL，>8 时按 domain_labels embedding 余弦初筛）
3. LLM 打分（soul_router_score_v1.txt system prompt + 结构化输出）
4. LLM 失败 → embedding 降级（余弦相似度排序）
5. 分数 × route_weight 调整 → 阈值判定自动路由 / route_uncertain
6. 路由日志 + 统计累计
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from app.utils.paths import PROJECT_ROOT

from app.services import soul_config
from app.services import soul_profile
from app.services.agent_harness_manager import agent_harness
from app.services.embedding_service import embedding_service

# ── 模块级状态 ──────────────────────────────────────────────────────────

# 路由缓存: {(query_hash, task_type): (expiry_ts, RouteResult)}
_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()

# 路由统计
_stats: dict[str, Any] = {
    "total_routes": 0,
    "cache_hits": 0,
    "fallbacks": 0,
    "per_soul_selection": {},  # {kb_id: int}
}
_stats_lock = asyncio.Lock()

# 全局路由成本累计（不计入 SOUL 学习预算）
_route_cost_usd: float = 0.0
_cost_lock = asyncio.Lock()

# 路由日志路径(backend/app/data,与测试集同目录)
_LOG_DIR = PROJECT_ROOT / "app" / "data"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_log_path = _LOG_DIR / "router-log.jsonl"
_log_lock = asyncio.Lock()

# ── 提示词目录 ──────────────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_ROUTER_SYSTEM_PROMPT = _PROMPTS_DIR / "soul_router_score_v1.txt"


# ── 余弦相似度工具 ──────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    dot / (|a| * |b|)，带 epsilon 保护避免除零。
    输入应为已归一化的向量（embedding_service 输出已归一化），
    此时余弦相似度 = 内积。
    """
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    denom = norm_a * norm_b
    if denom < 1e-12:
        return 0.0
    return dot / denom


# ── 内部辅助 ────────────────────────────────────────────────────────────

def _query_hash(query: str) -> str:
    """计算查询文本的短哈希（sha256 前 12 位）。"""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]


def _kb_config_for(soul_kb_id: str) -> dict:
    """从 soul KB 的 meditation 配置取 harness/model。"""
    try:
        from app.services.kb_meditation_config import get_meditation_config
        cfg = get_meditation_config(soul_kb_id).get("config", {})
        return {"harness": cfg.get("harness", "omp"), "model": cfg.get("model", "")}
    except Exception:
        return {"harness": "omp", "model": ""}


# ── 公开 API ────────────────────────────────────────────────────────────

async def route(
    query: str,
    task_goal: str = "",
    task_type: str = "",
    top_k: int = 1,
) -> dict[str, Any]:
    """查询路由：从已注册 SOUL 中选择最优匹配人格。

    Args:
        query: 用户查询文本。
        task_goal: 任务目标描述（如"教学""研究"）。
        task_type: 任务类型标签（匹配 supported_task_types）。
        top_k: 保留参数（当前始终返回全部 ranked，≤8）。

    Returns:
        {
            "ranked": [{"kb_id": str, "score": float, "reason": str}] (≤8),
            "route_uncertain": bool,
            "top1": str | None,
            "route_confidence": float | None,
            "cache_hit": bool,
            "embedding_fallback": bool,
            "candidates_considered": int,
        }
    """
    qh = _query_hash(query)
    cache_key = (qh, task_type)
    now = time.time()

    # ── TTL 缓存检查 ──
    async with _cache_lock:
        if cache_key in _cache:
            expiry, cached_result = _cache[cache_key]
            if now < expiry:
                async with _stats_lock:
                    _stats["total_routes"] += 1
                    _stats["cache_hits"] += 1
                cached_result["cache_hit"] = True
                return cached_result
            else:
                del _cache[cache_key]

    # ── 候选收集 ──
    all_candidates = soul_config.list_soul_kbs(include_template=False)

    if not all_candidates:
        result: dict[str, Any] = {
            "ranked": [],
            "route_uncertain": True,
            "top1": None,
            "route_confidence": None,
            "cache_hit": False,
            "embedding_fallback": False,
            "candidates_considered": 0,
        }
        async with _cache_lock:
            _cache[cache_key] = (
                now + soul_config.ROUTER_TTL_SECONDS,
                {**result},
            )
        return result

    candidates_considered = len(all_candidates)

    # ── 候选 >8: domain_labels embedding 余弦初筛 ──
    prefiltered_candidates = all_candidates
    if len(all_candidates) > soul_config.ROUTER_MAX_CANDIDATES:
        try:
            query_vec = embedding_service.embed_one(query)
        except Exception as e:
            logger.warning("Embedding query failed for pre-filter: %s", e)
            query_vec = []

        if query_vec:
            scored_candidates: list[tuple[dict, float]] = []
            for kb in all_candidates:
                try:
                    cfg = soul_config.read_soul_config(kb["kb_id"])
                except Exception:
                    continue
                labels = cfg.domain_labels
                if not labels:
                    # 无领域标签 → 保留（中性分数）
                    scored_candidates.append((kb, 0.5))
                    continue
                try:
                    label_vecs = embedding_service.embed(labels)
                except Exception as e:
                    logger.warning(
                        "Embedding domain_labels failed for %s: %s",
                        kb["kb_id"], e,
                    )
                    scored_candidates.append((kb, 0.5))
                    continue
                if not label_vecs:
                    scored_candidates.append((kb, 0.5))
                    continue
                # 均值向量
                dim = len(label_vecs[0])
                mean_vec = [0.0] * dim
                for lv in label_vecs:
                    for i in range(dim):
                        mean_vec[i] += lv[i]
                for i in range(dim):
                    mean_vec[i] /= len(label_vecs)
                cos = _cosine_similarity(query_vec, mean_vec)
                scored_candidates.append((kb, cos))

            # 按余弦相似度降序，取前 ROUTER_MAX_CANDIDATES 个
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            prefiltered_candidates = [
                kb for kb, _ in scored_candidates[:soul_config.ROUTER_MAX_CANDIDATES]
            ]
        else:
            # embedding 不可用 → 截断取前 N 个
            prefiltered_candidates = all_candidates[:soul_config.ROUTER_MAX_CANDIDATES]

    # ── 读取每个候选的 profile summary ──
    candidate_infos: list[dict[str, Any]] = []
    for kb in prefiltered_candidates:
        kid = kb["kb_id"]
        try:
            cfg = soul_config.read_soul_config(kid)
        except Exception:
            cfg = soul_config.SoulConfig(
                kb_scope=[], is_template=False, route_weight=1.0,
            )

        summary = ""
        profile_missing = False
        try:
            summary = soul_profile.read_profile_summary(kid)
        except Exception:
            profile_missing = True
            # fallback: soul-definition 前 500 字
            try:
                from app.services.storage_reader_service import storage_reader
                kb_path = kb.get("path", "")
                docs = storage_reader.list_documents(kb_path)
                soul_def_path = ""
                for d in docs:
                    if d.get("name", "").startswith("soul-definition"):
                        soul_def_path = d.get("path", "")
                        break
                if soul_def_path:
                    content = storage_reader.read_document_content(
                        soul_def_path, max_chars=500,
                    )
                    summary = content[:500]
            except Exception:
                summary = ""

        candidate_infos.append({
            "kb_id": kid,
            "domain_labels": cfg.domain_labels,
            "supported_task_types": cfg.supported_task_types,
            "route_weight": cfg.route_weight,
            "profile_summary": summary,
            "profile_missing": profile_missing,
        })

    # ── 构建路由打分 prompt ──
    candidates_json = []
    for ci in candidate_infos:
        candidates_json.append({
            "kb_id": ci["kb_id"],
            "domain_labels": ci["domain_labels"],
            "supported_task_types": ci["supported_task_types"],
            "route_weight": ci["route_weight"],
            "profile_summary": ci["profile_summary"][:500],
        })

    prompt = (
        f"## 用户查询\n<USER_CONTENT>\n{query[:2000]}\n</USER_CONTENT>\n\n"
        f"## 任务目标\n{task_goal or '（未指定）'}\n\n"
        f"## 任务类型\n{task_type or '（未指定）'}\n\n"
        f"## 候选 SOUL 列表\n"
        f"{json.dumps(candidates_json, ensure_ascii=False, indent=2)}"
    )

    # ── LLM 打分 ──
    result_schema = {
        "type": "object",
        "properties": {
            "ranked": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kb_id": {"type": "string"},
                        "score": {"type": "number"},
                        "reason": {"type": "string", "maxLength": 50},
                    },
                    "required": ["kb_id", "score", "reason"],
                },
                "maxItems": 8,
            },
        },
        "required": ["ranked"],
    }

    # 使用第一个候选的 kb_config（harness/model），或默认 omp
    first_kb_config = {}
    if candidate_infos:
        first_kb_config = _kb_config_for(candidate_infos[0]["kb_id"])

    embedding_fallback = False
    route_confidence: float | None = None
    ranked: list[dict[str, Any]] = []

    try:
        result = await agent_harness.complete(
            prompt=prompt,
            kb_config=first_kb_config,
            result_schema=result_schema,
            system_prompt_path=str(_ROUTER_SYSTEM_PROMPT),
            timeout_sec=60,
            expected_output_tokens=1024,
        )

        # 累计路由成本
        cost = float(result.get("cost_estimate", 0.0))
        async with _cost_lock:
            global _route_cost_usd
            _route_cost_usd += cost

        if result.get("success") and result.get("parsed"):
            parsed = result["parsed"]
            if isinstance(parsed, dict):
                raw_ranked = parsed.get("ranked", [])
            elif isinstance(parsed, list):
                raw_ranked = parsed
            else:
                raw_ranked = []

            # 验证并规范化 ranked 条目
            for entry in raw_ranked:
                if not isinstance(entry, dict):
                    continue
                kid = str(entry.get("kb_id", ""))
                score = float(entry.get("score", 0.0))
                reason = str(entry.get("reason", ""))[:50]

                # 查找对应候选的 route_weight
                weight = 1.0
                for ci in candidate_infos:
                    if ci["kb_id"] == kid:
                        weight = ci["route_weight"]
                        break

                adjusted = score * weight
                ranked.append({
                    "kb_id": kid,
                    "score": round(adjusted, 4),
                    "reason": reason,
                })
        else:
            # complete() 失败 → embedding 降级
            embedding_fallback = True
    except Exception as e:
        logger.warning(
            "Router complete() failed: %s; falling back to embedding", e,
        )
        embedding_fallback = True

    # ── Embedding 降级 ──
    if embedding_fallback:
        ranked = await _embedding_fallback_rank(query, prefiltered_candidates)

    # ── 排序（adjusted 降序）──
    if ranked:
        ranked.sort(key=lambda x: x["score"], reverse=True)
        ranked = ranked[:soul_config.ROUTER_MAX_CANDIDATES]

    # ── 判定路由置信度 ──
    top1_kb_id: str | None = None
    route_uncertain = True

    if ranked:
        top1_entry = ranked[0]
        top1_score = top1_entry["score"]
        top1_kb_id = top1_entry["kb_id"]
        threshold = soul_config.ROUTE_CONFIDENCE_THRESHOLD

        if not embedding_fallback:
            route_confidence = top1_score

        if top1_score >= threshold:
            route_uncertain = False
    else:
        route_confidence = None

    # ── 构建返回结果 ──
    route_result: dict[str, Any] = {
        "ranked": ranked,
        "route_uncertain": route_uncertain,
        "top1": top1_kb_id if not route_uncertain else None,
        "route_confidence": route_confidence,
        "cache_hit": False,
        "embedding_fallback": embedding_fallback,
        "candidates_considered": candidates_considered,
    }

    # ── 写入 TTL 缓存 ──
    async with _cache_lock:
        _cache[cache_key] = (
            now + soul_config.ROUTER_TTL_SECONDS,
            {**route_result},
        )

    # ── 路由日志 ──
    top1_reason = ""
    if top1_kb_id and ranked:
        for r in ranked:
            if r["kb_id"] == top1_kb_id:
                top1_reason = r.get("reason", "")
                break

    log_entry = {
        "query_hash": qh,
        "query": query[:200],
        "task_goal": task_goal,
        "task_type": task_type,
        "choice": top1_kb_id,
        "reason": top1_reason[:100],
        "confidence": route_confidence,
        "threshold_used": soul_config.ROUTE_CONFIDENCE_THRESHOLD,
        "cached": False,
        "embedding_fallback": embedding_fallback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    async with _log_lock:
        try:
            line = json.dumps(log_entry, ensure_ascii=False) + "\n"
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logger.warning("Failed to write router log: %s", e)

    # ── 统计更新 ──
    async with _stats_lock:
        _stats["total_routes"] += 1
        if embedding_fallback:
            _stats["fallbacks"] += 1
        if top1_kb_id:
            per_soul = _stats["per_soul_selection"]
            per_soul[top1_kb_id] = per_soul.get(top1_kb_id, 0) + 1

    return route_result


async def _embedding_fallback_rank(
    query: str,
    candidates: list[dict],
) -> list[dict[str, Any]]:
    """Embedding 降级：按查询与各 SOUL domain_labels 均值向量的余弦相似度排序。

    Args:
        query: 用户查询文本。
        candidates: list_soul_kbs() 返回的候选列表（已预筛选或全部）。

    Returns:
        按 adjusted 降序排列的 ranked 列表（score = cosine × route_weight）。
    """
    try:
        query_vec = embedding_service.embed_one(query)
    except Exception as e:
        logger.warning("Embedding fallback: query embedding failed: %s", e)
        return []

    if not query_vec:
        return []

    scored: list[tuple[dict[str, Any], float]] = []
    for kb in candidates:
        kid = kb["kb_id"]
        try:
            cfg = soul_config.read_soul_config(kid)
        except Exception:
            cfg = soul_config.SoulConfig(
                kb_scope=[], is_template=False, route_weight=1.0,
            )

        labels = cfg.domain_labels
        if not labels:
            # 无领域标签 → 中性分数
            scored.append((
                {"kb_id": kid, "score": 0.5, "reason": "无领域标签（embedding 降级）"},
                0.5,
            ))
            continue

        try:
            label_vecs = embedding_service.embed(labels)
        except Exception as e:
            logger.warning(
                "Embedding fallback: label embedding failed for %s: %s", kid, e,
            )
            scored.append((
                {"kb_id": kid, "score": 0.3, "reason": "标签嵌入失败"},
                0.3,
            ))
            continue

        if not label_vecs:
            scored.append((
                {"kb_id": kid, "score": 0.5, "reason": "无领域标签（embedding 降级）"},
                0.5,
            ))
            continue

        # 均值向量
        dim = len(label_vecs[0])
        mean_vec = [0.0] * dim
        for lv in label_vecs:
            for i in range(dim):
                mean_vec[i] += lv[i]
        for i in range(dim):
            mean_vec[i] /= len(label_vecs)

        cos = _cosine_similarity(query_vec, mean_vec)

        # 应用 route_weight
        adjusted = cos * cfg.route_weight
        reason = f"领域余弦相似度 {cos:.3f}"[:50]
        scored.append((
            {"kb_id": kid, "score": round(adjusted, 4), "reason": reason},
            adjusted,
        ))

    # 按 adjusted 降序
    scored.sort(key=lambda x: x[1], reverse=True)
    return [entry for entry, _ in scored[:soul_config.ROUTER_MAX_CANDIDATES]]


def invalidate_cache(soul_kb_id: str | None = None) -> None:
    """清空路由缓存（profile/config 变更时调用）。

    Args:
        soul_kb_id: 指定清空的 SOUL KB ID（按 ranked 中的 kb_id 匹配）；
            为 None 时全清。
    """
    if soul_kb_id is None:
        _cache.clear()
        logger.info("Router cache fully invalidated")
        return

    # 清除所有包含该 soul_kb_id 的缓存条目
    to_remove: list[tuple[str, str]] = []
    for cache_key, (_, cached_result) in list(_cache.items()):
        ranked = cached_result.get("ranked", [])
        if any(r.get("kb_id") == soul_kb_id for r in ranked):
            to_remove.append(cache_key)
    for key in to_remove:
        del _cache[key]
    if to_remove:
        logger.info(
            "Router cache invalidated for soul_kb_id=%s: %d entries removed",
            soul_kb_id, len(to_remove),
        )


async def get_router_status() -> dict[str, Any]:
    """获取路由状态统计。

    Returns:
        {
            "total_routes": int,
            "cache_hit_rate": float,
            "fallback_rate": float,
            "per_soul_selection_count": {kb_id: int},
            "route_cost_usd": float,
        }
    """
    async with _stats_lock:
        total = _stats["total_routes"]
        cache_hits = _stats["cache_hits"]
        fallbacks = _stats["fallbacks"]
        per_soul = dict(_stats["per_soul_selection"])

    cache_hit_rate = (cache_hits / total) if total > 0 else 0.0
    fallback_rate = (fallbacks / total) if total > 0 else 0.0

    async with _cost_lock:
        cost = _route_cost_usd

    return {
        "total_routes": total,
        "cache_hit_rate": round(cache_hit_rate, 4),
        "fallback_rate": round(fallback_rate, 4),
        "per_soul_selection_count": per_soul,
        "route_cost_usd": round(cost, 6),
    }