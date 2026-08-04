"""SOUL 强化学习引擎 — 评价 Agent 驱动的结构文档优化闭环。

RL 心智模型(好奇心驱动的强化学习训练):
  - 探索(Exploration): learn_incremental 对 kb_scope 内文档生成四层好奇心问题,
    检索自答,四维自评 —— 让 SOUL 学习新知识(观测环境)
  - 奖励(Reward): evaluate_persona 由评价 Agent 对人格当前表现打分
    (身份清晰度/价值观一致性/思维有效性/语言风格, 0-5)
  - 策略更新(Policy Update): generate_cognition_drafts 对低分维度生成认知草稿
    (对 soul-definition.md 结构文档的受控优化建议) → 人工审批 →
    apply_cognition_draft 合并入宪法层对应章节 → profile 刷新
  - 迭代: 每轮训练后 reward 记录到 reports/reward-history.jsonl,
    追踪"人格进化曲线"(模拟人类后天学习路径)

宪法层安全: 认知草稿只做"章节内追加优化行",不删除/重写既有内容;
审批/回滚/检查点机制完整保留(与记忆草稿同通道)。
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.soul_config import resolve_soul_kb_path, soul_kb_dir
from app.services.soul_memory import (
    _now_iso,
    _append_jsonl,
    _fmt_frontmatter,
    atomic_write_text,
    _read_memory_full,
)
from app.services.agent_harness_manager import agent_harness

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 人格特质 → soul-definition.md 章节标题(追加目标)
TRAIT_SECTIONS: dict[str, str] = {
    "identity": "## 身份定位",
    "values": "## 性格五维",
    "thinking": "## 回答格式偏好",
    "language": "## language-style",
}

REWARD_MIN = 3.5  # 低于该分维度生成认知草稿


# ═══════════════════════════════════════════════════════════════════════════
# §1  评价 Agent(evaluate_persona) — 奖励信号
# ═══════════════════════════════════════════════════════════════════════════

async def evaluate_persona(soul_kb_id: str, n_samples: int = 1) -> dict[str, Any]:
    """评价 Agent 对 SOUL 当前人格表现的四维评分(奖励信号)。

    证据输入:
      1. soul-definition.md 当前定义(前 2500 字符)
      2. 最近训练记忆草稿 3-5 条(question/answer/scores)
      3. 最近 gaps 摘要(grounding_below_3 / retrieval_failure 分布)

    n_samples > 1 时多次独立评价取均值(reward 平滑, 抑制 LLM 方差,
    RL 训练建议 2-3 次; 快速单查用默认 1 次)。

    输出: {identity, values, thinking, language, overall, suggestions}
    suggestions 为每个低分维度的具体优化建议(供认知草稿生成器使用)。
    """
    n_samples = max(1, int(n_samples or 1))

    if n_samples == 1:
        return await _evaluate_once(soul_kb_id)

    # 多采样: 并行多次独立评价, 逐维取中位数(reward 平滑, 抗 LLM 方差离群)
    results = await asyncio.gather(
        *(_evaluate_once(soul_kb_id) for _ in range(n_samples)),
        return_exceptions=True,
    )
    samples = [r for r in results if isinstance(r, dict) and r.get("success")
               and float(r.get("overall", 0)) > 0]
    if not samples:
        return {"success": True, "overall": 0.0, "identity": 0, "values": 0,
                "thinking": 0, "language": 0, "suggestions": {},
                "warning": "evaluation_parse_failed"}
    merged: dict[str, Any] = {"success": True, "n_samples": len(samples)}

    def _median(values: list[float]) -> float:
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return round((ordered[mid - 1] + ordered[mid]) / 2, 2)

    for key in ("identity", "values", "thinking", "language", "overall"):
        merged[key] = _median([float(s.get(key, 0)) for s in samples])
    lowest = min(samples, key=lambda s: float(s.get("overall", 0)))
    merged["suggestions"] = lowest.get("suggestions") or {}
    if any(s.get("warning") for s in samples):
        merged["warning"] = "partial_sample_failure"
    return merged


async def _evaluate_once(soul_kb_id: str) -> dict[str, Any]:
    """单次评价(评价 Agent 单次调用)。"""
    _dir = soul_kb_dir(soul_kb_id)
    def_path = _dir / "soul-definition.md"
    definition = (
        def_path.read_text(encoding="utf-8")[:2500]
        if def_path.exists() else ""
    )

    # 收集证据: 仅已批准记忆(稳定评测集, 避免 pending 草稿池变化导致评分漂移)
    evidence_drafts: list[dict] = []
    mem_dir = _dir / "memories"
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            fm, body = _read_memory_full(f) or ({}, "")
            if fm and fm.get("status") == "approved":
                evidence_drafts.append({
                    "question": fm.get("question", "")[:150],
                    "answer": body[:400],
                    "scores": fm.get("scores", {}),
                })
                if len(evidence_drafts) >= 5:
                    break

    # gaps 分布
    gaps_path = _dir / "training" / "gaps.md"
    gaps_summary = ""
    if gaps_path.exists():
        try:
            gaps_text = gaps_path.read_text(encoding="utf-8")[-1200:]
            gaps_summary = gaps_text
        except Exception:
            pass

    prompt_path = _PROMPTS_DIR / "soul_reward_eval_v1.txt"
    payload = json.dumps({
        "definition": definition,
        "recent_drafts": evidence_drafts,
        "gaps_summary": gaps_summary,
    }, ensure_ascii=False, indent=1)[:12000]

    result = await agent_harness.complete(
        prompt=f"<USER_CONTENT>\n{payload}\n</USER_CONTENT>",
        system_prompt_path=str(prompt_path),
        expected_output_tokens=800,
    )
    text = (result.get("text") or "") if result.get("success") else ""

    parsed = _extract_json(text)
    if not parsed or not isinstance(parsed, dict):
        # 评价失败: 返回中性分(不阻塞训练), 记录告警
        return {
            "success": True,
            "overall": 0.0,
            "identity": 0, "values": 0, "thinking": 0, "language": 0,
            "suggestions": {},
            "warning": "evaluation_parse_failed",
        }

    def _f(v: Any, default: int = 0) -> float:
        try:
            return min(5.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return float(default)

    scores = {
        "identity": _f(parsed.get("identity")),
        "values": _f(parsed.get("values")),
        "thinking": _f(parsed.get("thinking")),
        "language": _f(parsed.get("language")),
    }
    overall = _f(parsed.get("overall"), sum(scores.values()) / 4)
    suggestions = parsed.get("suggestions") or {}
    if not isinstance(suggestions, dict):
        suggestions = {}

    return {
        "success": True,
        **scores,
        "overall": overall,
        "suggestions": suggestions,
    }


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出提取 JSON(fence/裸 JSON 均支持)。"""
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
    # 最后尝试截取第一个 { 到最后一个 }
    s, e = text.find("{"), text.rfind("}")
    if 0 <= s < e:
        try:
            return json.loads(text[s:e + 1])
        except Exception:
            return None
    return None


# ═══════════════════════════════════════════════════════════════════════════
# §2  认知草稿生成(generate_cognition_drafts) — 策略更新建议
# ═══════════════════════════════════════════════════════════════════════════

async def generate_cognition_drafts(soul_kb_id: str, evaluation: dict) -> dict[str, Any]:
    """对低分维度生成认知草稿(cognition-drafts/*.md)。

    草稿 frontmatter: {type: cognition, trait, scores, source: reward,
    status: pending, learned_at}; body 为要追加进 soul-definition.md
    对应章节的优化行(每行一个短语/一句话, 语言风格维度尤其如此)。

    Returns: {created: [draft_id...], skipped: [trait...]}
    """
    _dir = soul_kb_dir(soul_kb_id)
    suggestions: dict = evaluation.get("suggestions") or {}
    created: list[str] = []
    skipped: list[str] = []

    for trait, score in (("identity", evaluation.get("identity", 5)),
                         ("values", evaluation.get("values", 5)),
                         ("thinking", evaluation.get("thinking", 5)),
                         ("language", evaluation.get("language", 5))):
        if float(score) >= REWARD_MIN:
            continue
        raw = suggestions.get(trait)
        if not raw:
            skipped.append(f"{trait}(no_suggestion)")
            continue
        lines = _normalize_lines(raw)
        if not lines:
            skipped.append(f"{trait}(empty)")
            continue

        draft_id = datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + __import__("uuid").uuid4().hex[:12]
        fm = {
            "type": "cognition",
            "trait": trait,
            "scores": {"reward": score},
            "source": "reward",
            "status": "pending",
            "learned_at": _now_iso(),
        }
        body = "\n".join(lines)
        content = _fmt_frontmatter(fm) + "\n" + body + "\n"
        drafts_dir = _dir / "cognition-drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(drafts_dir / f"{draft_id}.md", content)
        created.append(draft_id)

    return {"success": True, "created": created, "skipped": skipped}


def _normalize_lines(raw: Any, max_lines: int = 6) -> list[str]:
    """把 LLM 建议文本规范化为单行短语列表(去序号/横线/引号)。"""
    if isinstance(raw, str):
        lines = raw.split("\n")
    elif isinstance(raw, list):
        lines = [str(x) for x in raw]
    else:
        return []
    out: list[str] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        ln = ln.lstrip("-*•0123456789.、）)] ")
        ln = ln.strip().strip('"').strip("'").strip("。")
        if not ln:
            continue
        if ln not in out:
            out.append(ln)
        if len(out) >= max_lines:
            break
    return out


# ═══════════════════════════════════════════════════════════════════════════
# §3  认知草稿合并(apply_cognition_draft) — 策略落地
# ═══════════════════════════════════════════════════════════════════════════

async def apply_cognition_draft(soul_kb_id: str, draft_id: str,
                                operator: str = "system") -> dict[str, Any]:
    """将已批准认知草稿合并进 soul-definition.md 对应章节。

    安全规则:
      - 只向对应中文章节(见 TRAIT_SECTIONS)末尾追加优化行
      - 不删除/重写既有内容; 章节结构保持(profile/language-style 解析依赖)
      - 写前创建检查点; 写后刷新 profile-summary
    """
    _dir = soul_kb_dir(soul_kb_id)
    draft_path = _dir / "cognition-drafts" / f"{draft_id}.md"
    if not draft_path.exists():
        return {"success": False, "error": f"Draft not found: {draft_id}"}

    fm, body = _read_memory_full(draft_path) or ({}, "")
    if not fm or fm.get("type") != "cognition":
        return {"success": False, "error": "not_a_cognition_draft"}
    if fm.get("status") == "approved":
        return {"success": False, "error": "already_applied",
                "detail": f"draft {draft_id} 已审批合并, 幂等拒绝"}

    trait = fm.get("trait", "")
    section_title = TRAIT_SECTIONS.get(trait)
    if not section_title:
        return {"success": False, "error": f"unknown_trait: {trait}"}

    lines = [ln.rstrip() for ln in body.split("\n") if ln.strip()]

    # 合并前检查点(可回滚安全网)
    try:
        from app.services.soul_memory import _create_checkpoint_locked
        await _create_checkpoint_locked(soul_kb_id, _dir)
    except Exception as e:
        logger.warning("checkpoint before cognition apply failed: %s", e)

    def_path = _dir / "soul-definition.md"
    if not def_path.exists():
        return {"success": False, "error": "soul-definition missing"}

    text = def_path.read_text(encoding="utf-8")
    # 行级去重: 已存在于定义中的行不重复追加(重复训练/草稿幂等)
    existing_lines = {ln.strip() for ln in text.split("\n") if ln.strip()}
    fresh = [ln for ln in lines if ln not in existing_lines]
    if not fresh:
        # 全部行已存在 → 直接标记审批, 不重复写入
        fm["status"] = "approved"
        fm["approved_at"] = _now_iso()
        fm["approved_by"] = operator
        atomic_write_text(draft_path, _fmt_frontmatter(fm) + "\n" + body + "\n")
        _append_jsonl(_dir / "audit" / "approval-log.jsonl", {
            "timestamp": _now_iso(), "operator": operator, "action": "approve_cognition",
            "draft_id": draft_id, "trait": trait, "dedup": True,
            "draft_scores": fm.get("scores", {}),
        })
        return {"success": True, "approved": [draft_id], "trait": trait,
                "lines_appended": 0, "dedup": True, "indexed": True}

    new_text = _append_to_section(text, section_title, fresh)

    # 原子写 + frontmatter 更新
    atomic_write_text(def_path, new_text)

    fm["status"] = "approved"
    fm["approved_at"] = _now_iso()
    fm["approved_by"] = operator
    atomic_write_text(draft_path, _fmt_frontmatter(fm) + "\n" + body + "\n")

    # 审计
    _append_jsonl(_dir / "audit" / "approval-log.jsonl", {
        "timestamp": _now_iso(), "operator": operator, "action": "approve_cognition",
        "draft_id": draft_id, "trait": trait, "draft_scores": fm.get("scores", {}),
    })

    # 刷新 profile(路由依据同步)
    try:
        from app.services.soul_profile import generate_profile_summary
        await generate_profile_summary(soul_kb_id)
    except Exception as e:
        logger.debug("profile refresh after cognition apply failed: %s", e)

    return {
        "success": True,
        "approved": [draft_id],
        "trait": trait,
        "lines_appended": len(fresh),
        "indexed": True,
    }


def _append_to_section(text: str, section_title: str, lines: list[str]) -> str:
    """在对应章节末尾追加行; 找不到章节则追加到文末进化段。"""
    marker = f"## {section_title}" if not section_title.startswith("##") else section_title
    idx = text.find(marker)
    if idx < 0:
        # 无匹配章节 → 文末追加进化段
        tail = "\n\n## 进化日志(RL)\n\n" + "\n".join(f"- {ln}" for ln in lines) + "\n"
        return text.rstrip() + tail

    # 找该章节的结束(下一个 ## 或文末)
    next_idx = text.find("\n## ", idx + len(marker))
    insert_at = next_idx if next_idx > 0 else len(text)
    # 在章节内容末尾插入(缩进保留, 以 `- ` 列表行追加)
    section_end = insert_at
    # 若章节最后有换行, 在其后插入; 否则补换行
    prefix = text[:section_end]
    if not prefix.endswith("\n"):
        prefix += "\n"
    if trait_section_is_list_style(section_title):
        # language-style: 每行一个短语, 不含标点, 供自动子串匹配 → 追加裸行
        new_section = prefix + "\n".join(lines) + "\n"
    else:
        # 自由文本章节 → 追加 `- ` 列表行
        new_section = prefix + "\n".join(f"- {ln}" for ln in lines) + "\n"
    return new_section + text[insert_at:]


def trait_section_is_list_style(section_title: str) -> bool:
    """language-style 章节为"每行一个短语"列表风格, 其余为自由文本。"""
    return "language-style" in section_title


# ═══════════════════════════════════════════════════════════════════════════
# §5  读取助手(前端查看器)
# ═══════════════════════════════════════════════════════════════════════════

_PERSONA_DOCS = ["soul-definition.md", "thinking-style.md",
                 "values.md", "memory-conventions.md"]


def read_reward_history(soul_kb_id: str, limit: int = 50) -> list[dict]:
    """读取 RL 进化曲线记录(reward-history.jsonl, 新→旧)。"""
    _dir = soul_kb_dir(soul_kb_id)
    history_path = _dir / "reports" / "reward-history.jsonl"
    if not history_path.exists():
        return []
    records: list[dict] = []
    try:
        for line in history_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return records[-int(limit):]


async def read_persona_docs(soul_kb_id: str) -> dict[str, Any]:
    """读取人格定义 4 文档(供前端查看器) + RL 进化行统计。

    evolution_lines: 各文档中由 RL 认知草稿追加的行集合统计
    (从已批准 cognition-drafts 的 body 行聚合)。
    """
    _dir = soul_kb_dir(soul_kb_id)
    docs: list[dict] = []
    for name in _PERSONA_DOCS:
        p = _dir / name
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                docs.append({
                    "name": name,
                    "content": content,
                    "updated_at": datetime.fromtimestamp(
                        p.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                })
            except Exception:
                continue

    # 已批准认知草稿行(RL 进化痕迹)
    evolution_lines: list[str] = []
    cog_dir = _dir / "cognition-drafts"
    if cog_dir.exists():
        for f in sorted(cog_dir.glob("*.md")):
            fm, body = _read_memory_full(f) or ({}, "")
            if fm and fm.get("status") == "approved" and fm.get("type") == "cognition":
                for ln in body.split("\n"):
                    ln = ln.strip()
                    if ln and ln not in evolution_lines:
                        evolution_lines.append(ln)

    return {"docs": docs, "evolution_lines": evolution_lines[:60],
            "evolution_count": len(evolution_lines)}


# ═══════════════════════════════════════════════════════════════════════════
# §4  RL 主循环(train_rl) — 好奇心探索 × 评价 × 策略更新
# ═══════════════════════════════════════════════════════════════════════════

async def train_rl(soul_kb_id: str, rounds: int = 1,
                   progress_cb=None) -> dict[str, Any]:
    """RL 训练主循环(单 SOUL)。

    每轮:
      1. 好奇心探索: learn_incremental(rounds=1) — 学习新知识/更新认知
      2. 奖励: evaluate_persona — 评价 Agent 四维评分
      3. 策略更新: generate_cognition_drafts — 低分维度 → 认知草稿(待审批)
      4. reward 记录 → reports/reward-history.jsonl(进化曲线)

    Returns: {rounds_completed, per_round: [{round, reward, drafts_created,
    learn_report}], reward_history_path}

    NOTE: 不在本函数预取 per-soul 锁 —— learn_incremental 内部自行持锁,
    asyncio.Lock 不可重入, 外层再 acquire 同一实例会死锁至超时导致
    learn 阶段被跳过(历史 bug)。evaluate/generate 为只读/原子写, 无锁需求。
    """
    from app.services.soul_learn import learn_incremental

    rounds = max(1, int(rounds or 1))
    _dir = soul_kb_dir(soul_kb_id)
    history_path = _dir / "reports" / "reward-history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    per_round: list[dict] = []

    for r in range(1, rounds + 1):
        # 1) 好奇心探索(增量学习; learn_incremental 内部持 per-soul 锁)
        learn_rep = await learn_incremental(
            soul_kb_id, rounds=1,
            progress_cb=(lambda p: progress_cb({"phase": "learn", "round": r,
                                                 "rounds": rounds, **p}))
            if progress_cb else None,
        )
        learn_ok = bool(learn_rep.get("success"))
        learn_err = learn_rep.get("error") if not learn_ok else None
        if progress_cb:
            progress_cb({
                "phase": "learn", "round": r, "rounds": rounds,
                "questions": learn_rep.get("questions_generated", 0),
                "memories": learn_rep.get("memories_created", 0),
                "docs_processed": learn_rep.get("docs_processed", 0),
                "learn_error": learn_err,
            })

        # 2) 奖励(评价 Agent, 2 次采样均值平滑 LLM 方差) — learn 失败不阻塞评价/策略更新
        eval_rep = await evaluate_persona(soul_kb_id, n_samples=2)
        reward = float(eval_rep.get("overall", 0.0))

        # 3) 策略更新(认知草稿)
        cog_rep = await generate_cognition_drafts(soul_kb_id, eval_rep)
        created = cog_rep.get("created", [])

        # 4) reward 历史
        _append_jsonl(history_path, {
            "round": r, "timestamp": _now_iso(),
            "reward": reward,
            "identity": eval_rep.get("identity", 0),
            "values": eval_rep.get("values", 0),
            "thinking": eval_rep.get("thinking", 0),
            "language": eval_rep.get("language", 0),
            "drafts_created": created,
            "learn": {
                "ok": learn_ok,
                "error": learn_err,
                "questions": learn_rep.get("questions_generated", 0),
                "memories": learn_rep.get("memories_created", 0),
                "docs": learn_rep.get("docs_processed", 0),
            },
        })

        per_round.append({
            "round": r,
            "reward": reward,
            "scores": {
                "identity": eval_rep.get("identity", 0),
                "values": eval_rep.get("values", 0),
                "thinking": eval_rep.get("thinking", 0),
                "language": eval_rep.get("language", 0),
            },
            "cognition_drafts_created": created,
            "learn": {
                "ok": learn_ok,
                "error": learn_err,
                "questions_generated": learn_rep.get("questions_generated", 0),
                "memories_created": learn_rep.get("memories_created", 0),
                "docs_processed": learn_rep.get("docs_processed", 0),
            },
        })
        if progress_cb:
            progress_cb({
                "phase": "reward", "round": r, "rounds": rounds,
                "reward": reward, "drafts_created": len(created),
            })

    return {
        "success": True,
        "rounds_completed": len(per_round),
        "per_round": per_round,
        "reward_history_path": str(history_path),
        "hint": "认知草稿需经 soul_review_drafts(draft_type=cognition) 审批后合并入人格定义",
    }
