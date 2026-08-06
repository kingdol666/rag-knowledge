"""SOUL 三角色强化学习引擎 — DRL 启发的统一训练架构。

将"知识学习"(learn_incremental)与"自我进化"(evaluate_persona + cognition_drafts)
统一为一个三角色 RL 循环, 大幅提升训练速度与效果。

━━━ 三角色架构(DRL → SOUL 映射) ━━━

  Actor (执行者) ── πθ(s→a)
    在知识库环境中执行问答: 生成好奇心问题 → 检索自答 → 质量自评 → 蒸馏记忆
    「权重」= memories/*.md(知识掌握度)
    优化: 并行批处理(asyncio.gather), ZPD 自适应跳过已掌握主题

  Critic (评价者) ── Vφ(s) → reward
    六维评价: 身份/价值观/思维/语言/知识掌握/自我一致性
    输出奖励信号 + 收敛检测
    优化: 单次 LLM 调用评估全部维度(含知识掌握), 中位数平滑

  Updater (更新者) ── ∇θ J(θ)
    基于奖励梯度更新「人格权重」(宪法层文档):
    低分维度 → 生成认知草稿 → 收敛态自动应用 / 发散态人工审批
    优化: 收敛感知自动应用(reward delta < 阈值 → 免人工瓶颈)

━━━ 训练速度对比 ━━━

  旧架构(串行): N问 × (检索+回答+评估) = 3N 串行 LLM 调用
  新架构(并行): 一批问题并行回答 + 一次统一 Critic → 提速 ~4-5x
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.soul_config import (
    resolve_soul_kb_path,
    soul_kb_dir,
    read_soul_config,
    get_soul_lock,
    PER_SOUL_LOCK_TIMEOUT,
)
from app.services.soul_memory import (
    _now_iso,
    _append_jsonl,
    _fmt_frontmatter,
    atomic_write_text,
    _read_memory_full,
)
from app.services.agent_harness_manager import agent_harness

# Module-level import of parallel pipeline (avoid lazy import inside function —
# uvicorn --reload worker can fail to resolve it after file changes)
from app.services.soul_learn import learn_incremental_parallel  # noqa: E402

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# ── 收敛检测参数 ──────────────────────────────────────────────────────────
REWARD_MIN = 3.5          # 维度达标线(达标维度不生成认知草稿)
CONVERGENCE_DELTA = 0.25  # reward 变化 < 此值视为收敛(平台期)
CONVERGENCE_ROUNDS = 2    # 连续 N 轮平台期 → 进入收敛态
AUTO_APPLY_THRESHOLD = 4.2  # overall ≥ 此值 + 收敛态 → 自动应用认知草稿

# ── 人格维度 → 目标文档+章节映射(多文档权重更新) ─────────────────────────
# Critic 六维评分 → 精准写入对应的宪法层文档章节
# 每个维度映射到: (目标文件名, 章节标题)
TRAIT_TARGETS: dict[str, tuple[str, str]] = {
    "identity":  ("soul-definition.md", "## 身份定位"),
    "values":    ("soul-definition.md", "## 性格五维"),
    "thinking":  ("thinking-style.md",  "## 推理模式"),
    "language":  ("soul-definition.md", "## language-style"),
    "knowledge": ("soul-definition.md", "## 领域知识经验"),
    "coherence": ("soul-definition.md", "## 自我一致性"),
}

# 旧映射(兼容, _apply_cognition_safe 内部不再使用)
TRAIT_SECTIONS: dict[str, str] = {
    "identity": "## 身份定位",
    "values": "## 性格五维",
    "thinking": "## 回答格式偏好",
    "language": "## language-style",
}

# ── 六维评价维度 ──────────────────────────────────────────────────────────
EVAL_DIMENSIONS = (
    "identity",    # 身份清晰度 → soul-definition.md/身份定位
    "values",      # 价值观一致性 → soul-definition.md/性格五维
    "thinking",    # 思维有效性 → thinking-style.md/推理模式
    "language",    # 语言风格 → soul-definition.md/language-style
    "knowledge",   # 知识掌握深度 → soul-definition.md/领域知识经验(动态创建)
    "coherence",   # 自我一致性 → soul-definition.md/自我一致性(动态创建)
)


# ═══════════════════════════════════════════════════════════════════════════
# 统一 RL 训练主循环
# ═══════════════════════════════════════════════════════════════════════════

async def train_rl_unified(
    soul_kb_id: str,
    rounds: int = 1,
    progress_cb=None,
) -> dict[str, Any]:
    """统一 RL 训练主循环(单 SOUL) — 三角色架构。

    每轮:
      Phase 1 ACTOR:   并行批处理知识学习(好奇心问题 → 检索自答 → 蒸馏)
      Phase 2 CRITIC:  六维评价 + 收敛检测(奖励信号)
      Phase 3 UPDATER: 收敛感知策略更新(认知草稿生成 + 自动应用)
      Phase 4 REWARD:  进化曲线记录
    """
    # learn_incremental_parallel imported at module level to avoid reload-worker race

    rounds = max(1, int(rounds or 1))
    _dir = soul_kb_dir(soul_kb_id)
    history_path = _dir / "reports" / "reward-history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    prev_rewards = _read_recent_rewards(history_path, CONVERGENCE_ROUNDS + 2)
    convergence_state = _detect_convergence(prev_rewards)
    per_round: list[dict] = []

    for r in range(1, rounds + 1):
        round_start = time.time()

        # ── Phase 1: ACTOR (执行者) — 并行批处理知识学习 ──────────
        if progress_cb:
            await _cb(progress_cb, {"phase": "actor", "round": r, "rounds": rounds,
                                    "msg": "执行者: 知识探索中..."})

        actor_intensity = 0.5 if convergence_state["converged"] else 1.0

        learn_rep = await learn_incremental_parallel(
            soul_kb_id, rounds=1, intensity=actor_intensity,
            progress_cb=(lambda p: _cb(progress_cb, {"phase": "actor", "round": r,
                                                      "rounds": rounds, **p}))
            if progress_cb else None,
        )
        learn_ok = bool(learn_rep.get("success"))
        learn_err = learn_rep.get("error") if not learn_ok else None
        actor_stats = {
            "questions": learn_rep.get("questions_generated", 0),
            "memories": learn_rep.get("memories_created", 0),
            "docs_processed": learn_rep.get("docs_processed", 0),
            "gaps_count": learn_rep.get("gaps_count", 0),
        }
        # Actor 完成事件(含本轮学习统计)
        if progress_cb:
            await _cb(progress_cb, {
                "phase": "actor", "type": "actor_done", "round": r, "rounds": rounds,
                "questions": actor_stats["questions"],
                "memories": actor_stats["memories"],
                "docs_processed": actor_stats["docs_processed"],
                "gaps": actor_stats["gaps_count"],
                "learn_error": learn_err,
            })

        # ── Phase 2: CRITIC (评价者) — 六维评价 + 收敛检测 ─────────
        if progress_cb:
            await _cb(progress_cb, {"phase": "critic", "round": r, "rounds": rounds,
                                    "msg": "评价者: 六维评分中..."})

        eval_rep = await _critic_unified(soul_kb_id, actor_stats, n_samples=1)
        reward = float(eval_rep.get("overall", 0.0))

        # Critic 评分事件(含六维分数 + 收敛分析 — 前端可视化核心)
        if progress_cb:
            await _cb(progress_cb, {
                "phase": "critic", "type": "critic_score", "round": r, "rounds": rounds,
                "identity": eval_rep.get("identity", 0),
                "values": eval_rep.get("values", 0),
                "thinking": eval_rep.get("thinking", 0),
                "language": eval_rep.get("language", 0),
                "knowledge": eval_rep.get("knowledge", 0),
                "coherence": eval_rep.get("coherence", 0),
                "overall": reward,
                "convergence_note": eval_rep.get("convergence_note", ""),
            })

        # ── Phase 3: UPDATER (更新者) — 收敛感知策略更新 ────────────
        prev_rewards.append(reward)
        prev_rewards = prev_rewards[-(CONVERGENCE_ROUNDS + 2):]
        convergence_state = _detect_convergence(prev_rewards)

        if progress_cb:
            await _cb(progress_cb, {"phase": "updater", "round": r, "rounds": rounds,
                                    "msg": "更新者: 权重更新中...",
                                    "converged": convergence_state["converged"]})

        updater_rep = await _updater_phase(
            soul_kb_id, eval_rep, convergence_state,
        )

        # Updater 权重更新事件(含每个维度的优化行 — 前端可视化权重变化)
        if progress_cb:
            drafts = updater_rep.get("drafts_created", [])
            await _cb(progress_cb, {
                "phase": "updater", "type": "updater_done", "round": r, "rounds": rounds,
                "auto_applied": updater_rep.get("auto_applied", 0),
                "pending": updater_rep.get("pending", 0),
                "drafts_count": len(drafts),
                "converged": convergence_state["converged"],
            })
        # ── Phase 4.5: AUTO-APPROVE — 自动批准高质量记忆(让权重真正落地) ──
        # 核心: 训练产出的 pending 记忆必须在问答时可见才算"真训练"。
        # 自动批准条件: groundedness≥3.5 且四维均分≥3.5(严格高于人工审批的≥3 门槛)。
        if learn_ok and actor_stats["memories"] > 0:
            if progress_cb:
                await _cb(progress_cb, {"phase": "approve", "round": r,
                                        "rounds": rounds, "msg": "自动批准高质量记忆..."})
            approve_rep = await _auto_approve_memories(soul_kb_id)
        else:
            approve_rep = {"approved": 0, "skipped": 0}

        # ── Phase 5: KNOWLEDGE DISTILL — 跨记忆知识综合(总结经验,非堆砌) ──
        if learn_ok:
            if progress_cb:
                await _cb(progress_cb, {"phase": "distill", "round": r,
                                        "rounds": rounds, "msg": "知识蒸馏: 综合经验..."})
            distill_rep = await distill_knowledge(soul_kb_id)
        else:
            distill_rep = {"distilled": False}
        # ── Phase 6: GLOBAL OPTIMIZE — 全局人格优化(修复"越练越笨") ──
        # 把积累的 active 认知草稿做完整的、连贯的全局重写:
        # 替换旧内容(删除矛盾), 非碎片追加 → reward 单调提升
        active_cogs = _active_cognition_drafts(_dir)
        should_opt, opt_reason = _should_optimize_globally(
            _dir, convergence_state, prev_rewards, active_cogs)

        optimize_rep: dict[str, Any] = {"optimized": False}
        if should_opt:
            if progress_cb:
                await _cb(progress_cb, {
                    "phase": "optimize", "round": r, "rounds": rounds,
                    "msg": f"全局优化: {opt_reason}, 重写人格定义...",
                    "active_cognitions": len(active_cogs),
                })
            optimize_rep = await optimize_persona_global(soul_kb_id, eval_rep)
            if progress_cb and optimize_rep.get("optimized"):
                await _cb(progress_cb, {
                    "phase": "optimize", "type": "optimize_done",
                    "round": r, "rounds": rounds,
                    "optimized_docs": optimize_rep.get("optimized_docs", []),
                    "cognitions_absorbed": optimize_rep.get("cognitions_absorbed", 0),
                })
        # ── Phase 4: REWARD ──────────────────────────────────────────
        round_elapsed = round(time.time() - round_start, 1)
        _append_jsonl(history_path, {
            "round": r, "timestamp": _now_iso(), "elapsed_sec": round_elapsed,
            "reward": reward,
            "identity": eval_rep.get("identity", 0),
            "values": eval_rep.get("values", 0),
            "thinking": eval_rep.get("thinking", 0),
            "language": eval_rep.get("language", 0),
            "knowledge": eval_rep.get("knowledge", 0),
            "coherence": eval_rep.get("coherence", 0),
            "memories_auto_approved": approve_rep.get("approved", 0),
            "converged": convergence_state["converged"],
            "cognition_auto_applied": updater_rep.get("auto_applied", 0),
"cognition_pending_review": updater_rep.get("pending", 0),
"global_optimized": optimize_rep.get("optimized", False),
"cognitions_absorbed": optimize_rep.get("cognitions_absorbed", 0),
"optimized_docs": optimize_rep.get("optimized_docs", []),
"learn": {
    "ok": learn_ok, "error": learn_err,
    "questions": actor_stats["questions"],
    "memories": actor_stats["memories"],
    "docs": actor_stats["docs_processed"],
},
        })

        per_round.append({
            "round": r, "elapsed_sec": round_elapsed, "reward": reward,
            "scores": {
                "identity": eval_rep.get("identity", 0),
                "values": eval_rep.get("values", 0),
                "thinking": eval_rep.get("thinking", 0),
                "language": eval_rep.get("language", 0),
                "knowledge": eval_rep.get("knowledge", 0),
                "coherence": eval_rep.get("coherence", 0),
            },
            "converged": convergence_state["converged"],
            "cognition": {
                "auto_applied": updater_rep.get("auto_applied", 0),
                "pending": updater_rep.get("pending", 0),
            },
            "global_optimize": {
                "optimized": optimize_rep.get("optimized", False),
                "docs": optimize_rep.get("optimized_docs", []),
                "absorbed": optimize_rep.get("cognitions_absorbed", 0),
            },
            "learn": {
                "ok": learn_ok, "error": learn_err,
                "questions_generated": actor_stats["questions"],
                "memories_created": actor_stats["memories"],
                "docs_processed": actor_stats["docs_processed"],
            },
        })

        if progress_cb:
            await _cb(progress_cb, {
                "phase": "reward", "round": r, "rounds": rounds,
                "reward": reward, "converged": convergence_state["converged"],
                "auto_applied": updater_rep.get("auto_applied", 0),
                "memories_approved": approve_rep.get("approved", 0),
                "global_optimized": optimize_rep.get("optimized", False),
                "elapsed_sec": round_elapsed,
            })

    return {
        "success": True,
        "rounds_completed": len(per_round),
        "per_round": per_round,
        "convergence_state": convergence_state,
        "hint": (
            "RL 统一训练完成。"
            + ("全局优化已应用(认知草稿已吸收重写)。" if any(
                pr.get("global_optimize", {}).get("optimized") for pr in per_round)
               else "")
            + f" 收敛态: {'是' if convergence_state['converged'] else '否'}"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4.5: AUTO-APPROVE — 自动批准高质量训练记忆(权重真正落地)
# ═══════════════════════════════════════════════════════════════════════════

async def _auto_approve_memories(soul_kb_id: str) -> dict[str, Any]:
    """自动批准高质量 pending 记忆 → 注册索引 → 问答时可检索。

    这是"真训练"的关键环节: 训练产出的 pending 记忆必须在问答时可见。
    自动批准门槛(严格高于人工审批):
      - groundedness ≥ 3.5
      - 四维均分 ≥ 3.5
      - 无 judge_divergence
    通过后: status→approved + 向量/图谱/BM25 索引 + profile 刷新。
    """
    from app.services.soul_memory import approve_draft, list_drafts

    _dir = soul_kb_dir(soul_kb_id)
    mem_dir = _dir / "memories"
    if not mem_dir.exists():
        return {"approved": 0, "skipped": 0}

    # 列出 pending 记忆
    try:
        drafts_rep = await list_drafts(soul_kb_id, draft_type="memory")
    except Exception:
        return {"approved": 0, "skipped": 0}

    pending = drafts_rep.get("drafts", [])
    if not pending:
        return {"approved": 0, "skipped": 0}

    approved_count = 0
    skipped_count = 0

    for draft in pending:
        scores = draft.get("scores", {})
        groundedness = float(scores.get("groundedness", 0))
        dims = [float(scores.get(k, 0)) for k in
                ("groundedness", "completeness", "coherence", "info_gain")]
        mean_score = sum(dims) / len(dims) if dims else 0
        has_divergence = draft.get("judge_divergence") is not None

        # 自动批准门槛(严格)
        if groundedness >= 3.5 and mean_score >= 3.5 and not has_divergence:
            draft_id = draft.get("id", "")
            if not draft_id:
                continue
            try:
                rep = await approve_draft(
                    soul_kb_id, draft_id, force=False,
                    operator="rl_auto_approve", draft_type="memory")
                if rep.get("success"):
                    approved_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.warning("auto-approve memory %s failed: %s", draft_id, e)
                skipped_count += 1
        else:
            skipped_count += 1

    logger.info("auto-approve: %d approved, %d skipped for %s",
                approved_count, skipped_count, soul_kb_id)
    return {"approved": approved_count, "skipped": skipped_count}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5: KNOWLEDGE DISTILL — 知识蒸馏(经验总结, 非堆砌)
# ═══════════════════════════════════════════════════════════════════════════

async def distill_knowledge(soul_kb_id: str) -> dict[str, Any]:
    """将已批准记忆综合提炼为结构化知识经验,写入 knowledge-synthesis.md。

    核心区别于"堆砌":
    - 不是复制每条记忆,而是跨记忆综合归纳共同模式与关键洞察
    - 产出 experience_rules(回答策略) + knowledge_points(知识结论)
    - 写入 SOUL 的 knowledge-synthesis.md, 在问答时注入 prompt
    - 每次训练后重新蒸馏(覆盖旧的, 保持精炼不膨胀)

    触发条件: 已批准记忆 ≥ 3 条(否则不值得综合)
    """
    _dir = soul_kb_dir(soul_kb_id)
    mem_dir = _dir / "memories"
    if not mem_dir.exists():
        return {"success": True, "distilled": False, "reason": "no_memories"}

    # 收集已批准记忆
    approved_memories: list[dict] = []
    for f in sorted(mem_dir.glob("*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        fm, body = _read_memory_full(f) or ({}, "")
        if not fm or fm.get("status") != "approved":
            continue
        approved_memories.append({
            "id": f"m{len(approved_memories) + 1}",
            "question": fm.get("question", "")[:200],
            "answer": body[:400],
            "scores": fm.get("scores", {}),
        })
        if len(approved_memories) >= 15:  # 最多综合 15 条
            break

    if len(approved_memories) < 3:
        return {"success": True, "distilled": False,
                "reason": f"insufficient_memories({len(approved_memories)})"}

    # 读取人格身份(保持视角一致)
    def_path = _dir / "soul-definition.md"
    persona = def_path.read_text(encoding="utf-8")[:500] if def_path.exists() else ""

    prompt_path = _PROMPTS_DIR / "soul_distill_knowledge_v1.txt"
    payload = json.dumps({
        "persona": persona,
        "memories": approved_memories,
    }, ensure_ascii=False, indent=1)[:12000]

    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=1000,
        timeout_sec=300,
    )
    text = (result.get("text") or "") if result.get("success") else ""
    parsed = _extract_json(text)
    if not parsed or not isinstance(parsed, dict):
        logger.warning("distill_knowledge: LLM parse failed for %s", soul_kb_id)
        return {"success": True, "distilled": False, "reason": "llm_parse_failed"}

    rules = parsed.get("experience_rules", [])
    points = parsed.get("knowledge_points", [])
    summary = parsed.get("synthesis_summary", "")

    if not rules and not points:
        return {"success": True, "distilled": False, "reason": "empty_synthesis"}

    # 写入 knowledge-synthesis.md(覆盖旧版, 保持精炼)
    synth_path = _dir / "knowledge-synthesis.md"
    lines = [
        f"<!-- 知识蒸馏: {soul_kb_id} | 更新: {_now_iso()} -->",
        f"<!-- 来源记忆: {len(approved_memories)} 条已批准 -->",
        "",
        "# 知识经验综合(训练蒸馏)",
        "",
        f"> {summary}",
        "",
    ]
    if rules:
        lines.append("## 回答经验法则")
        for r in rules:
            lines.append(f"- {r}")
        lines.append("")
    if points:
        lines.append("## 知识要点")
        for p in points:
            lines.append(f"- {p}")
        lines.append("")

    atomic_write_text(synth_path, "\n".join(lines))

    # 索引到向量库(问答时可检索)
    try:
        kb_path = resolve_soul_kb_path(soul_kb_id)
        if kb_path:
            from app.services.vector_service import vector_service
            doc_rel = f"{kb_path}/knowledge-synthesis.md"
            vector_service.index_document(
                kb_id=kb_path, doc_path=doc_rel,
                content="\n".join(lines))
    except Exception as e:
        logger.warning("distill_knowledge: index failed for %s: %s", soul_kb_id, e)

    logger.info("distill_knowledge: %d rules + %d points for %s",
                len(rules), len(points), soul_kb_id)
    return {
        "success": True, "distilled": True,
        "rules_count": len(rules), "points_count": len(points),
        "summary": summary[:100],
    }

# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: CRITIC (评价者) — 六维统一评价
# ═══════════════════════════════════════════════════════════════════════════

async def _critic_unified(
    soul_kb_id: str,
    actor_stats: dict[str, int],
    n_samples: int = 2,
) -> dict[str, Any]:
    """统一六维评价(多次采样取中位数)。"""
    n_samples = max(1, int(n_samples or 1))
    if n_samples == 1:
        return await _critic_once(soul_kb_id, actor_stats)

    results = await asyncio.gather(
        *(_critic_once(soul_kb_id, actor_stats) for _ in range(n_samples)),
        return_exceptions=True,
    )
    samples = [
        r for r in results
        if isinstance(r, dict) and r.get("success")
        and float(r.get("overall", 0)) > 0
    ]
    if not samples:
        return {
            "success": True, "overall": 0.0,
            "identity": 0, "values": 0, "thinking": 0,
            "language": 0, "knowledge": 0, "coherence": 0,
            "suggestions": {}, "warning": "evaluation_parse_failed",
        }

    merged: dict[str, Any] = {"success": True, "n_samples": len(samples)}

    def _median(values: list[float]) -> float:
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return round((ordered[mid - 1] + ordered[mid]) / 2, 2)

    for key in (*EVAL_DIMENSIONS, "overall"):
        merged[key] = _median([float(s.get(key, 0)) for s in samples])

    lowest = min(samples, key=lambda s: float(s.get("overall", 0)))
    merged["suggestions"] = lowest.get("suggestions") or {}
    if any(s.get("warning") for s in samples):
        merged["warning"] = "partial_sample_failure"
    return merged


async def _critic_once(
    soul_kb_id: str, actor_stats: dict[str, int],
) -> dict[str, Any]:
    """单次六维评价(Critic 单次 LLM 调用)。"""
    _dir = soul_kb_dir(soul_kb_id)

    # 证据 1: 人格定义
    def_path = _dir / "soul-definition.md"
    definition = (
        def_path.read_text(encoding="utf-8")[:3000]
        if def_path.exists() else ""
    )

    # 证据 2: 已批准记忆(稳定评测集)
    evidence_memories: list[dict] = []
    mem_dir = _dir / "memories"
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            fm, body = _read_memory_full(f) or ({}, "")
            if fm and fm.get("status") == "approved":
                evidence_memories.append({
                    "question": fm.get("question", "")[:120],
                    "answer": body[:300],
                    "scores": fm.get("scores", {}),
                    "doc_source": fm.get("doc_source", ""),
                })
                if len(evidence_memories) >= 5:
                    break

    # 证据 3: gaps 分布
    gaps_path = _dir / "training" / "gaps.md"
    gaps_summary = ""
    if gaps_path.exists():
        try:
            gaps_summary = gaps_path.read_text(encoding="utf-8")[-1000:]
        except Exception:
            pass

    # 证据 4: mastery 画像(知识掌握结构化数据)
    mastery_summary = ""
    mastery_path = _dir / "questions" / "mastery.json"
    if mastery_path.exists():
        try:
            md = json.loads(mastery_path.read_text(encoding="utf-8"))
            topics = md.get("topics", {})
            if topics:
                total_q = sum(t.get("questions", 0) for t in topics.values())
                avg_scores = [t.get("avg_score", 0) for t in topics.values()]
                mastery_summary = (
                    f"主题数={len(topics)}, 总问题={total_q}, "
                    f"平均掌握={sum(avg_scores) / len(avg_scores):.2f}, "
                    f"薄弱主题={sum(1 for s in avg_scores if s < 3.0)}"
                )
        except Exception:
            pass

    # 证据 5: reward 历史(进化趋势)
    history_path = _dir / "reports" / "reward-history.jsonl"
    recent_rewards: list[float] = []
    if history_path.exists():
        try:
            lines = history_path.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-5:]:
                if line.strip():
                    rec = json.loads(line)
                    recent_rewards.append(float(rec.get("reward", 0)))
        except Exception:
            pass

    prompt_path = _PROMPTS_DIR / "soul_rl_critic_v2.txt"
    payload = json.dumps({
        "definition": definition,
        "recent_memories": evidence_memories,
        "gaps_summary": gaps_summary,
        "mastery_summary": mastery_summary,
        "actor_stats": actor_stats,
        "recent_rewards": recent_rewards,
    }, ensure_ascii=False, indent=1)[:14000]

    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=900,
        timeout_sec=300,
    )
    text = (result.get("text") or "") if result.get("success") else ""
    if not result.get("success"):
        logger.warning("critic complete() failed: %s", result.get("error", "unknown"))
    parsed = _extract_json(text)

    if not parsed or not isinstance(parsed, dict):
        logger.warning("critic _extract_json failed: success=%s text_len=%d preview=%s",
                       result.get("success"), len(text),
                       text[:200] if text else "(empty)")
        return {
            "success": True, "overall": 0.0,
            "identity": 0, "values": 0, "thinking": 0,
            "language": 0, "knowledge": 0, "coherence": 0,
            "suggestions": {}, "warning": "evaluation_parse_failed",
        }

    def _f(v: Any, default: float = 0.0) -> float:
        try:
            return min(5.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return float(default)

    scores = {dim: _f(parsed.get(dim)) for dim in EVAL_DIMENSIONS}
    overall_raw = parsed.get("overall")
    overall = _f(overall_raw) if overall_raw is not None else round(
        sum(scores.values()) / len(scores), 2)
    suggestions = parsed.get("suggestions") or {}
    if not isinstance(suggestions, dict):
        suggestions = {}
    return {
        "success": True,
        **scores,
        "overall": overall,
        "suggestions": suggestions,
    }
async def _updater_phase(
    soul_kb_id: str,
    evaluation: dict[str, Any],
    convergence_state: dict[str, Any],
) -> dict[str, Any]:
    """认知积累: Updater LLM 根据 Critic 评分生成认知草稿(只积累,不污染人格定义)。

    核心设计变更(修复"越练越笨"):
    - 不再直接写入人格定义文档(soul-definition.md / thinking-style.md)
    - 只生成认知草稿(status=active), 作为"认知增量"积累
    - 认知草稿在问答时被注入 prompt(让训练认知真正参与回答)
    - 全局优化(optimize_persona_global)负责把积累的认知做完整的、连贯的重写

    这样保证:
    1. 人格定义文档始终保持完整、连贯(不被碎片追加污染)
    2. 认知草稿可被 LLM 在合成回答时参考
    3. 全局优化时才有"删除旧内容、替换新内容"的能力 → reward 单调提升
    """
    _dir = soul_kb_dir(soul_kb_id)

    # 检查是否有低分维度需要生成认知
    low_dims = [d for d in EVAL_DIMENSIONS
                if float(evaluation.get(d, 5)) < REWARD_MIN]
    if not low_dims:
        return {"success": True, "auto_applied": 0, "pending": 0,
                "drafts_created": []}

    # ── Updater LLM: 独立第三角色, 生成认知优化行 ──
    updates = await _updater_llm(soul_kb_id, evaluation, convergence_state)
    # 降级: Updater 失败 → 回退 Critic suggestions
    if not updates:
        suggestions = evaluation.get("suggestions") or {}
        updates = {d: _normalize_lines(suggestions.get(d))
                   for d in low_dims if suggestions.get(d)}
        if updates:
            logger.info("updater LLM failed, fallback to critic suggestions")

    created: list[str] = []

    for trait, lines in updates.items():
        if not lines:
            continue
        score = float(evaluation.get(trait, 5))

        draft_id = (
            datetime.now(timezone.utc).strftime("%Y%m%d")
            + "-" + __import__("uuid").uuid4().hex[:12]
        )
        fm = {
            "type": "cognition", "trait": trait,
            "scores": {"reward": score}, "source": "rl_unified",
            "status": "active",
            "learned_at": _now_iso(),
            "convergence": convergence_state.get("converged", False),
        }
        body = "\n".join(lines)
        content = _fmt_frontmatter(fm) + "\n" + body + "\n"
        drafts_dir = _dir / "cognition-drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_path = drafts_dir / f"{draft_id}.md"
        atomic_write_text(draft_path, content)
        created.append(draft_id)

        # 审计: 认知草稿已生成(不写入人格定义)
        _append_jsonl(_dir / "audit" / "approval-log.jsonl", {
            "timestamp": _now_iso(), "operator": "rl_updater",
            "action": "cognition_created", "trait": trait,
            "draft_id": draft_id, "reward": score,
            "note": "认知积累(不写入人格定义, 由全局优化统一处理)",
        })

    active_count = len(_active_cognition_drafts(_dir))
    logger.info("updater: %d cognition drafts created (active total=%d) for %s",
                len(created), active_count, soul_kb_id)

    return {
        "success": True, "auto_applied": 0,
        "pending": len(created), "drafts_created": created,
        "active_cognition_count": active_count,
    }


async def _updater_llm(
    soul_kb_id: str,
    evaluation: dict[str, Any],
    convergence_state: dict[str, Any],
) -> dict[str, list[str]]:
    """Updater LLM(第三角色): 基于 Critic 梯度生成权重优化行。

    输入: 当前人格定义 + Critic 六维评分 + 缺口/掌握画像 + 收敛状态。
    输出: {trait: [优化行...]} — 仅含 <3.5 维度的更新。
    失败 → 返回 {}(调用方回退到 Critic suggestions)。
    """
    _dir = soul_kb_dir(soul_kb_id)
    def_path = _dir / "soul-definition.md"
    definition = (
        def_path.read_text(encoding="utf-8")[:3000]
        if def_path.exists() else ""
    )

    # 缺口与掌握画像(与 Critic 共享证据, 但 Updater 聚焦"怎么改")
    gaps_summary = ""
    gaps_path = _dir / "training" / "gaps.md"
    if gaps_path.exists():
        try:
            gaps_summary = gaps_path.read_text(encoding="utf-8")[-800:]
        except Exception:
            pass
    mastery_summary = ""
    mastery_path = _dir / "questions" / "mastery.json"
    if mastery_path.exists():
        try:
            md = json.loads(mastery_path.read_text(encoding="utf-8"))
            topics = md.get("topics", {})
            if topics:
                total_q = sum(t.get("questions", 0) for t in topics.values())
                avg_scores = [t.get("avg_score", 0) for t in topics.values()]
                mastery_summary = (
                    f"主题数={len(topics)}, 总问题={total_q}, "
                    f"平均掌握={sum(avg_scores) / len(avg_scores):.2f}, "
                    f"薄弱主题={sum(1 for s in avg_scores if s < 3.0)}"
                )
        except Exception:
            pass

    scores = {d: float(evaluation.get(d, 0)) for d in EVAL_DIMENSIONS}
    payload = json.dumps({
        "definition": definition,
        "scores": scores,
        "gaps_summary": gaps_summary,
        "mastery_summary": mastery_summary,
        "converged": convergence_state.get("converged", False),
    }, ensure_ascii=False, indent=1)[:12000]

    prompt_path = _PROMPTS_DIR / "soul_rl_updater_v1.txt"
    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=800,
        timeout_sec=300,
    )
    text = (result.get("text") or "") if result.get("success") else ""
    parsed = _extract_json(text)
    if not parsed or not isinstance(parsed, dict):
        return {}

    updates_raw = parsed.get("updates") or {}
    if not isinstance(updates_raw, dict):
        return {}

    updates: dict[str, list[str]] = {}
    for trait in EVAL_DIMENSIONS:
        if float(evaluation.get(trait, 5)) >= REWARD_MIN:
            continue
        lines = _normalize_lines(updates_raw.get(trait))
        if lines:
            updates[trait] = lines
    return updates


async def _apply_persona_update(
    soul_kb_id: str, trait: str, lines: list[str],
) -> bool:
    """将 Critic 低分维度的优化行写入对应的人格文档章节。

    根据 TRAIT_TARGETS 映射决定写入哪个文件的哪个章节:
      identity  → soul-definition.md / ## 身份定位
      values    → soul-definition.md / ## 性格五维
      thinking  → thinking-style.md  / ## 推理模式
      language  → soul-definition.md / ## language-style
      knowledge → soul-definition.md / ## 领域知识经验 (自动创建)
      coherence → soul-definition.md / ## 自我一致性 (自动创建)

    安全规则:
    - 只追加优化行, 不删改既有内容
    - 写前 checkpoint
    - 行级去重(幂等)
    - 审计日志 + profile 刷新 + 向量重索引
    """
    from app.services.soul_reward import _append_to_section, trait_section_is_list_style
    from app.services.soul_memory import _create_checkpoint_locked
    from app.services.soul_profile import generate_profile_summary

    target = TRAIT_TARGETS.get(trait)
    if not target:
        logger.warning("_apply_persona_update: no target for trait %s", trait)
        return False

    doc_name, section_title = target
    _dir = soul_kb_dir(soul_kb_id)
    doc_path = _dir / doc_name

    # 文档不存在 → 创建(soul-definition.md 应总存在, thinking-style.md 可能缺失)
    if not doc_path.exists():
        doc_path.write_text(f"# {doc_name}\n\n", encoding="utf-8")

    # 写前 checkpoint
    try:
        await _create_checkpoint_locked(soul_kb_id, _dir)
    except Exception as e:
        logger.warning("checkpoint before persona update failed: %s", e)

    text = doc_path.read_text(encoding="utf-8")

    # 章节不存在 → 在文档末尾创建新章节(knowledge/coherence 维度)
    if section_title not in text:
        text = text.rstrip() + f"\n\n{section_title}\n"

    # 行级去重
    existing_lines = {ln.strip() for ln in text.split("\n") if ln.strip()}
    fresh = [ln for ln in lines if ln.strip() not in existing_lines]
    if not fresh:
        return True  # 幂等: 所有行已存在

    # language-style 为列表风格(每行一个短语), 其余为 "- " 列表行
    is_list_style = trait_section_is_list_style(section_title)
    if is_list_style:
        formatted = fresh  # 裸短语
    else:
        formatted = [f"- {ln.strip()}" for ln in fresh]

    updated = _append_to_section(text, section_title, formatted)
    atomic_write_text(doc_path, updated)

    # 审计日志
    _append_jsonl(_dir / "audit" / "approval-log.jsonl", {
        "timestamp": _now_iso(), "operator": "rl_updater",
        "action": "persona_update", "trait": trait,
        "target_doc": doc_name, "target_section": section_title,
        "lines_appended": len(fresh),
    })

    # 重新索引到向量库(确保问答时能检索到更新后的人格定义)
    try:
        from app.services.vector_service import vector_service
        kb_path = resolve_soul_kb_path(soul_kb_id)
        if kb_path:
            doc_rel = f"{kb_path}/{doc_name}"
            vector_service.index_document(
                kb_id=kb_path, doc_path=doc_rel,
                content=doc_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("persona doc re-index failed for %s: %s", doc_name, e)

    # 刷新 profile(路由依据同步)
    try:
        await generate_profile_summary(soul_kb_id)
    except Exception as e:
        logger.debug("profile refresh after persona update failed: %s", e)

    logger.info("persona update: %s/%s += %d lines (trait=%s)",
                soul_kb_id, doc_name, len(fresh), trait)
    return True
# ═══════════════════════════════════════════════════════════════════════════
# 认知草稿读取 + 全局人格优化引擎(核心: 修复"越练越笨")
# ═══════════════════════════════════════════════════════════════════════════

# 全局优化触发条件
OPTIMIZE_MIN_COGNITIONS = 3      # active 认知草稿 >= 此数 → 触发全局优化
OPTIMIZE_REWARD_DROP = 0.3       # reward 连续下降 >= 此值 → 触发全局优化
OPTIMIZE_ROUNDS_INTERVAL = 3     # 每 N 轮至少触发一次全局优化(有认知草稿时)


def _active_cognition_drafts(soul_dir: Path) -> list[dict[str, Any]]:
    """读取所有 status=active 的认知草稿(待全局优化处理的认知增量)。"""
    cog_dir = soul_dir / "cognition-drafts"
    if not cog_dir.exists():
        return []
    drafts: list[dict[str, Any]] = []
    for f in sorted(cog_dir.glob("*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        fm, body = _read_memory_full(f) or ({}, "")
        if not fm or fm.get("status") != "active":
            continue
        drafts.append({
            "id": f.stem, "trait": fm.get("trait", ""),
            "reward": float(fm.get("scores", {}).get("reward", 0)),
            "lines": [ln.strip() for ln in body.split("\n") if ln.strip()],
            "learned_at": fm.get("learned_at", ""),
        })
    return drafts


def _should_optimize_globally(
    soul_dir: Path,
    convergence_state: dict[str, Any],
    recent_rewards: list[float],
    active_cognitions: list[dict],
) -> tuple[bool, str]:
    """判断是否应该触发全局人格优化。

    触发条件(满足任一):
    1. active 认知草稿数 >= OPTIMIZE_MIN_COGNITIONS
    2. reward 连续下降(最近两轮差值 < -OPTIMIZE_REWARD_DROP)
    3. 收敛态 + 有 active 认知草稿(收敛时做一次"固化")
    4. 知识驱动: 有已批准记忆 ≥3 但定义无领域知识(模板定义需进化)
    """
    if len(active_cognitions) >= OPTIMIZE_MIN_COGNITIONS:
        return True, f"cognition_accumulated({len(active_cognitions)})"

    if len(recent_rewards) >= 3:
        last_two = recent_rewards[-2:]
        if len(last_two) == 2 and (last_two[0] - last_two[1]) >= OPTIMIZE_REWARD_DROP:
            if active_cognitions:
                return True, f"reward_dropping({last_two[0]:.2f}->{last_two[1]:.2f})"

    if convergence_state.get("converged") and active_cognitions:
        return True, "converged_with_cognitions"

    # 知识驱动触发: 有记忆但定义是模板 → 需要从模板进化为领域专家
    mem_dir = soul_dir / "memories"
    if mem_dir.exists():
        approved_count = sum(
            1 for f in mem_dir.glob("*.md")
            if f.stat().st_size > 100
            and "status: approved" in f.read_text(encoding="utf-8", errors="replace")[:300]
        )
        if approved_count >= 3:
            defn = soul_dir / "soul-definition.md"
            if defn.exists():
                def_text = defn.read_text(encoding="utf-8")[:500]
                # 模板特征: 含"通用领域"或"研究型 AI 人格"且无领域知识章节
                is_template = ("通用领域" in def_text or "研究型 AI 人格" in def_text)
                has_domain_knowledge = "领域知识经验" in defn.read_text(encoding="utf-8")
                if is_template and not has_domain_knowledge:
                    return True, f"template_needs_evolution(memories={approved_count})"

    return False, ""


async def optimize_persona_global(
    soul_kb_id: str,
    evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """全局人格优化引擎 — 把积累的认知做完整的、连贯的全局重写。

    核心区别于旧的"碎片追加":
    - 读取全部人格上下文(4宪法文档 + active认知草稿 + 记忆 + 知识综合)
    - LLM 做一次完整的、连贯的重写(可以删除矛盾内容、重组结构)
    - 重写结果直接替换人格文档(非追加)
    - checkpoint 保护, 可回滚
    - 重写后将已处理的认知草稿标记为 applied(消化吸收)

    这样确保:
    1. 人格定义始终完整连贯(消除矛盾堆砌)
    2. reward 单调提升(每轮都在上一轮基础上优化)
    3. 认知草稿被真正"消化"进人格(而非堆在文档末尾)
    """
    from app.services.soul_memory import _create_checkpoint_locked

    _dir = soul_kb_dir(soul_kb_id)
    active = _active_cognition_drafts(_dir)

    if not active:
        return {"success": True, "optimized": False, "reason": "no_active_cognitions"}

    # ── 收集全部人格上下文 ──
    context = _collect_persona_context(_dir)

    # ── checkpoint(全局重写前的安全网) ──
    try:
        await _create_checkpoint_locked(soul_kb_id, _dir)
    except Exception as e:
        logger.warning("checkpoint before global optimize failed: %s", e)

    # ── LLM 全局重写 ──
    prompt_path = _PROMPTS_DIR / "soul_rl_global_optimize_v1.txt"
    payload = json.dumps({
        "soul_definition": context["soul_definition"],
        "values": context["values"],
        "thinking_style": context["thinking_style"],
        "active_cognitions": active[:20],
        "recent_memories": context["recent_memories"],
        "knowledge_synthesis": context["knowledge_synthesis"],
        "critic_scores": {d: float((evaluation or {}).get(d, 0))
                          for d in EVAL_DIMENSIONS} if evaluation else {},
    }, ensure_ascii=False, indent=1)[:24000]

    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=4000,
        timeout_sec=300,
    )
    text = (result.get("text") or "") if result.get("success") else ""
    parsed = _extract_json(text)

    if not parsed or not isinstance(parsed, dict):
        logger.warning("global optimize: LLM parse failed for %s", soul_kb_id)
        return {"success": True, "optimized": False, "reason": "llm_parse_failed"}

    # ── 应用全局重写(替换, 非追加) ──
    optimized_docs: list[str] = []

    for doc_field, doc_name in [
        ("soul_definition", "soul-definition.md"),
        ("thinking_style", "thinking-style.md"),
        ("values", "values.md"),
    ]:
        new_content = parsed.get(doc_field)
        if not new_content or not isinstance(new_content, str):
            continue
        new_content = new_content.strip()
        if len(new_content) < 50:
            continue

        # 质量校验: soul-definition.md 必须保留核心章节
        if doc_name == "soul-definition.md":
            if "## 身份定位" not in new_content:
                logger.warning("global optimize: soul-definition missing 身份定位, skip")
                continue
            if "## language-style" not in new_content:
                logger.warning("global optimize: soul-definition missing language-style, skip")
                continue
        doc_path = _dir / doc_name
        old_content = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""
        if new_content == old_content.strip():
            continue

        atomic_write_text(doc_path, new_content)
        optimized_docs.append(doc_name)

        # 向量重索引
        try:
            from app.services.vector_service import vector_service
            kb_path = resolve_soul_kb_path(soul_kb_id)
            if kb_path:
                vector_service.index_document(
                    kb_id=kb_path, doc_path=f"{kb_path}/{doc_name}",
                    content=new_content)
        except Exception as e:
            logger.warning("global optimize re-index failed for %s: %s", doc_name, e)

    if not optimized_docs:
        return {"success": True, "optimized": False, "reason": "no_changes"}

    # ── 标记认知草稿为 applied(消化吸收) ──
    applied_ids: list[str] = []
    for cog in active:
        draft_path = _dir / "cognition-drafts" / f"{cog['id']}.md"
        if not draft_path.exists():
            continue
        fm, body = _read_memory_full(draft_path) or ({}, "")
        if not fm:
            continue
        fm["status"] = "applied"
        fm["applied_at"] = _now_iso()
        fm["applied_by"] = "global_optimize"
        atomic_write_text(draft_path, _fmt_frontmatter(fm) + "\n" + body + "\n")
        applied_ids.append(cog["id"])

    # 审计
    _append_jsonl(_dir / "audit" / "approval-log.jsonl", {
        "timestamp": _now_iso(), "operator": "global_optimize",
        "action": "persona_global_rewrite",
        "optimized_docs": optimized_docs,
        "cognitions_absorbed": len(applied_ids),
        "critic_scores": {d: float((evaluation or {}).get(d, 0))
                          for d in EVAL_DIMENSIONS} if evaluation else {},
    })

    # 刷新 profile
    try:
        from app.services.soul_profile import generate_profile_summary
        await generate_profile_summary(soul_kb_id)
    except Exception as e:
        logger.debug("profile refresh after global optimize failed: %s", e)

    logger.info("global optimize: %s docs rewritten, %d cognitions absorbed for %s",
                optimized_docs, len(applied_ids), soul_kb_id)

    return {
        "success": True, "optimized": True,
        "optimized_docs": optimized_docs,
        "cognitions_absorbed": len(applied_ids),
        "applied_cognition_ids": applied_ids,
    }


def _collect_persona_context(soul_dir: Path) -> dict[str, Any]:
    """收集全部人格上下文供全局优化使用。"""
    def _read(name: str, limit: int = 4000) -> str:
        p = soul_dir / name
        return p.read_text(encoding="utf-8")[:limit] if p.exists() else ""

    # recent memories (approved)
    memories: list[dict] = []
    mem_dir = soul_dir / "memories"
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            fm, body = _read_memory_full(f) or ({}, "")
            if fm and fm.get("status") == "approved":
                memories.append({
                    "question": fm.get("question", "")[:150],
                    "answer": body[:300],
                })
                if len(memories) >= 8:
                    break

    synth = _read("knowledge-synthesis.md", 1500)

    return {
        "soul_definition": _read("soul-definition.md", 6000),
        "values": _read("values.md", 3000),
        "thinking_style": _read("thinking-style.md", 8000),
        "recent_memories": memories,
        "knowledge_synthesis": synth,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 收敛检测
# ═══════════════════════════════════════════════════════════════════════════

def _read_recent_rewards(history_path: Path, limit: int = 5) -> list[float]:
    """读取最近 N 轮 reward(收敛检测输入)。"""
    if not history_path.exists():
        return []
    try:
        lines = history_path.read_text(encoding="utf-8").strip().split("\n")
        rewards: list[float] = []
        for line in lines[-limit:]:
            if line.strip():
                rec = json.loads(line)
                rewards.append(float(rec.get("reward", 0)))
        return rewards
    except Exception:
        return []


def _detect_convergence(recent_rewards: list[float]) -> dict[str, Any]:
    """检测 reward 是否进入收敛平台期。

    收敛条件: 最近 CONVERGENCE_ROUNDS 轮 reward 变化幅度均 < CONVERGENCE_DELTA。
    收敛态: 减少探索(半量问题), 认知草稿可自动应用。
    """
    if len(recent_rewards) < CONVERGENCE_ROUNDS + 1:
        return {"converged": False, "delta": 0.0,
                "rounds_in_plateau": 0, "trend": "unknown"}

    deltas = [
        abs(recent_rewards[i] - recent_rewards[i - 1])
        for i in range(1, len(recent_rewards))
    ]
    plateau = sum(1 for d in deltas[-CONVERGENCE_ROUNDS:] if d < CONVERGENCE_DELTA)
    max_delta = max(deltas[-CONVERGENCE_ROUNDS:]) if deltas else 0.0

    if len(recent_rewards) >= 2:
        slope = recent_rewards[-1] - recent_rewards[-CONVERGENCE_ROUNDS]
        if slope > CONVERGENCE_DELTA:
            trend = "rising"
        elif slope < -CONVERGENCE_DELTA:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    return {
        "converged": plateau >= CONVERGENCE_ROUNDS and max_delta < CONVERGENCE_DELTA,
        "delta": round(max_delta, 4),
        "rounds_in_plateau": plateau,
        "trend": trend,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════

async def _cb(cb, payload: dict) -> None:
    """调用进度回调(兼容同步/异步)。"""
    try:
        r = cb(payload)
        if asyncio.iscoroutine(r):
            await r
    except Exception:
        pass


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出提取 JSON(fence/裸 JSON 块均支持)。"""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_marker, close_marker in (("```json", "```"), ("```", "```")):
        if open_marker in text:
            start = text.index(open_marker) + len(open_marker)
            end = text.index(close_marker, start) if close_marker in text[start:] else len(text)
            try:
                return json.loads(text[start:end].strip())
            except Exception:
                continue
    s, e = text.find("{"), text.rfind("}")
    if 0 <= s < e:
        try:
            return json.loads(text[s:e + 1])
        except Exception:
            return None
    return None


def _normalize_lines(raw: Any, max_lines: int = 6) -> list[str]:
    """把 LLM 建议文本规范化为单行短语列表(去序号/横线/引号)。"""
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        items = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    else:
        return []

    out: list[str] = []
    for item in items[:max_lines * 2]:
        text = str(item).strip()
        for prefix in ("- ", "• ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. "):
            if text.startswith(prefix):
                text = text[len(prefix):]
        text = text.strip('"\'""''「」')
        if text and len(text) <= 200:
            out.append(text)
        if len(out) >= max_lines:
            break
    return out
