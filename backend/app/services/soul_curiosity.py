"""SOUL 元认知好奇心引擎 v2 — 补天后天训练强化核心。

算法框架参考: Desvaux/Abdelghani/Oudeyer/Sauzéon, "Curiosity and
Metacognition: Towards a Unified Framework for Learning and Education
in the Age of AI" (arXiv:2604.25648, 2026):
  - 好奇心 = 内在知识获取驱动力, 根本依赖"元认知监控与控制"
    (metacognitive monitoring and control) → 本模块为每个 SOUL 维护
    questions/mastery.json 掌握画像(元认知状态), 训练循环每轮读写
  - 干预需"针对个体画像定制"(tailored to individual profiles)
    → 问题类型分布/难度按该 SOUL 的主题掌握度动态调整(近发展区 ZPD)
  - AI 应是"认知伙伴"而非捷径 → 新奇度过滤 + 缺口驱动, 防止重复学习

设计映射:
  论文概念             → v2 实现
  ─────────────────────────────────────────────────────────
  元认知监控           → mastery.json: per-topic 记忆数/均分/gaps/最近学习
  个体画像定制         → compute_question_mix(): 动态四层问题比例
  认知伙伴(防捷径)     → 已知记忆摘要注入 prompt + jaccard 新奇度过滤
  持续好奇(探索-利用)  → 薄弱已学文档重学队列(weak topics re-exploration)
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.soul_config import soul_kb_dir

logger = logging.getLogger(__name__)

# 掌握度阈值(与评价 Agent REWARD_MIN=3.5 对齐)
MASTERY_WEAK = 3.0        # 均分 <3.0 → 薄弱主题(重学)
MASTERY_MID = 3.5         # 3.0-3.5 → 补基深化
MASTERY_STRONG = 4.0      # >=4.0 → 前沿挑战

MASTERY_FILE = "mastery.json"

# 四层问题: fact / concept / cross_doc / challenge
DEFAULT_MIX = {"fact": 30, "concept": 30, "cross_doc": 20, "challenge": 20}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_memory_frontmatter(path: Path) -> dict:
    """读取记忆文件的 frontmatter(最小实现, 避免循环依赖)。"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm: dict = {}
    cur = None
    for line in text[3:end].splitlines():
        kv = re.match(r"^(\w+):\s*(.*)$", line)
        if kv:
            cur = kv.group(1)
            raw = kv.group(2).strip()
            fm[cur] = raw if raw else {}
        elif cur:
            # 嵌套缩进键(如 scores: 下的 groundedness: 2)
            nkv = re.match(r"^  (\w+):\s*(.*)$", line)
            if nkv and isinstance(fm.get(cur), dict):
                fm[cur][nkv.group(1)] = nkv.group(2).strip()
    # 宽松解析 scores/evidence_paths(兼容单/双引号 Python/JSON 字面量)
    for key in ("scores", "evidence_paths", "tags"):
        val = fm.get(key)
        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                import ast
                fm[key] = ast.literal_eval(val)
            except Exception:
                try:
                    fm[key] = json.loads(val)
                except Exception:
                    pass
    return fm


# ═══════════════════════════════════════════════════════════════════════════
# §1  元认知画像读写(questions/mastery.json)
# ═══════════════════════════════════════════════════════════════════════════

def read_mastery_profile(soul_kb_id: str) -> dict:
    """读取该 SOUL 的元认知掌握画像(不存在 → 空画像)。

    Returns:
        {
          updated_at, topics: {<doc_path>: {learned, approved_memories,
            avg_score, gaps, last_learned_at}}, weak_topics: [...],
          known_questions: [<已批准记忆 question 摘要>]
        }
    """
    empty = {"updated_at": "", "topics": {}, "weak_topics": [], "known_questions": []}
    try:
        p = soul_kb_dir(soul_kb_id) / "questions" / MASTERY_FILE
        if not p.exists():
            return empty
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return empty
        data.setdefault("topics", {})
        data.setdefault("weak_topics", [])
        data.setdefault("known_questions", [])
        return data
    except Exception as e:
        logger.warning("read_mastery_profile failed for %s: %s", soul_kb_id, e)
        return empty


def _aggregate_topics(soul_kb_id: str) -> tuple[dict, list[str]]:
    """从已批准记忆 + gaps + learned-hashes 聚合主题画像(纯本地 IO, 零 LLM 成本)。

    topic 键 = 证据文档路径(记忆的 evidence_paths 第一条; 无证据 → 按
    question 归属的 doc 缺失时归入 '_ungrounded')。
    """
    _dir = soul_kb_dir(soul_kb_id)
    topics: dict[str, dict] = {}

    # 1) 已批准记忆(掌握度 = 记忆质量)
    mem_dir = _dir / "memories"
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md")):
            fm = _read_memory_frontmatter(f)
            if not fm or fm.get("status") != "approved":
                continue
            paths = fm.get("evidence_paths") or []
            topic = paths[0] if paths else "_ungrounded"
            t = topics.setdefault(topic, {
                "learned": True, "approved_memories": 0,
                "avg_score": 0.0, "gaps": 0, "last_learned_at": "",
            })
            t["approved_memories"] += 1
            scores = fm.get("scores") or {}
            if not isinstance(scores, dict):
                scores = {}
            vals: list[float] = []
            for v in scores.values():
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
            t["avg_score"] = round(
                (t["avg_score"] * (t["approved_memories"] - 1) + (sum(vals) / len(vals) if vals else 0))
                / t["approved_memories"], 2) if vals else t["avg_score"]

    # 2) gaps(缺口 → 薄弱信号)
    gaps_path = _dir / "questions" / "gaps.md"
    if gaps_path.exists():
        try:
            for line in gaps_path.read_text(encoding="utf-8").splitlines():
                parts = line.split("\t")
                if len(parts) >= 4 and parts[2]:
                    t = topics.setdefault(parts[2], {
                        "learned": True, "approved_memories": 0,
                        "avg_score": 0.0, "gaps": 0, "last_learned_at": "",
                    })
                    t["gaps"] += 1
        except Exception:
            pass

    # 3) 已学哈希(学习足迹)
    try:
        hp = _dir / "questions" / "learned-hashes.json"
        if hp.exists():
            learned = json.loads(hp.read_text(encoding="utf-8"))
            for doc_path in learned:
                topics.setdefault(doc_path, {
                    "learned": True, "approved_memories": 0,
                    "avg_score": 0.0, "gaps": 0, "last_learned_at": "",
                })
    except Exception:
        pass

    weak = [k for k, v in topics.items()
            if (v["approved_memories"] == 0 or v["avg_score"] < MASTERY_WEAK or v["gaps"] > 0)]
    return topics, weak


def update_mastery_profile(soul_kb_id: str) -> dict:
    """训练轮次结束后刷新元认知画像(下一轮/RL 的元认知输入)。

    成本: 纯本地 IO, 无 LLM 调用。
    """
    topics, weak = _aggregate_topics(soul_kb_id)
    known: list[str] = []
    mem_dir = soul_kb_dir(soul_kb_id) / "memories"
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            fm = _read_memory_frontmatter(f)
            if fm and fm.get("status") == "approved" and fm.get("question"):
                known.append(str(fm["question"])[:120])
            if len(known) >= 8:
                break

    profile = {
        "updated_at": _now_iso(),
        "topics": topics,
        "weak_topics": weak,
        "known_questions": known,
    }
    try:
        qdir = soul_kb_dir(soul_kb_id) / "questions"
        qdir.mkdir(parents=True, exist_ok=True)
        (qdir / MASTERY_FILE).write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("update_mastery_profile write failed for %s: %s", soul_kb_id, e)
    return profile


def topic_mastery(mastery: dict, doc_path: str) -> dict:
    """取某文档的主题掌握状态(元认知上下文, 供自适应问题生成)。"""
    t = (mastery.get("topics") or {}).get(doc_path) or {}
    return {
        "learned": bool(t.get("learned")),
        "approved_memories": int(t.get("approved_memories", 0)),
        "avg_score": float(t.get("avg_score", 0.0)),
        "gaps": int(t.get("gaps", 0)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# §2  自适应问题分布(近发展区 ZPD — 个体画像定制)
# ═══════════════════════════════════════════════════════════════════════════

def compute_question_mix(mastery: dict | None, doc_path: str = "") -> dict:
    """按该主题掌握度动态计算四层问题比例。

    论文映射: 好奇心干预需针对个体画像定制 —— 未学主题打基础(事实优先),
    薄弱主题补基深化(概念/跨文档), 掌握主题挑战边界(挑战型倾斜)。
    """
    if not mastery:
        return dict(DEFAULT_MIX)
    t = topic_mastery(mastery, doc_path)
    if not t["learned"] or t["approved_memories"] == 0:
        # 新主题: 建立基础(事实/概念为主)
        return {"fact": 35, "concept": 30, "cross_doc": 20, "challenge": 15}
    avg = t["avg_score"]
    if avg < MASTERY_WEAK or t["gaps"] > 0:
        # 薄弱/有缺口: 补基 + 跨文档关联(重学模式)
        return {"fact": 20, "concept": 30, "cross_doc": 30, "challenge": 20}
    if avg < MASTERY_STRONG:
        # 中等: 均衡深化, 挑战略增
        return {"fact": 15, "concept": 25, "cross_doc": 30, "challenge": 30}
    # 强掌握: 前沿挑战倾斜(好奇心的最高形态 —— 探索知识边界)
    return {"fact": 10, "concept": 20, "cross_doc": 20, "challenge": 50}


def mix_to_instruction(mix: dict) -> str:
    """把比例 dict 转成 prompt 指令文本。"""
    return (f"- fact（事实层）：是什么、定义、参数、数据、多少（约 {mix['fact']}%）\n"
            f"- concept（概念层）：原理、机制、区别、为什么（约 {mix['concept']}%）\n"
            f"- cross_doc（跨文档层）：对比、关系、与…相关、异同（约 {mix['cross_doc']}%）\n"
            f"- challenge（挑战层）：挑战、难点、局限、瓶颈（约 {mix['challenge']}%，请重点倾斜此类）")


# ═══════════════════════════════════════════════════════════════════════════
# §3  新奇度过滤(认知伙伴 — 防重复学习)
# ═══════════════════════════════════════════════════════════════════════════

def novelty_filter(q_text: str, known_questions: list[str], threshold: float = 0.55) -> bool:
    """与已批准记忆问题做 jaccard 重叠过滤: 过高重叠 → 视为重复(返回 False)。

    轻量实现(零 LLM 成本): token 化后计算字符级重叠; 语义层由 prompt
    注入已知记忆摘要兜底(LLM 生成时主动避开)。
    """
    if not known_questions:
        return True

    def _tokens(s: str) -> set[str]:
        s = re.sub(r"[^\w\u4e00-\u9fff]+", " ", s.lower())
        # 中文按 2-gram, 英文按词
        cjk = re.findall(r"[\u4e00-\u9fff]", s)
        if len(cjk) >= 4:
            return set(s[j:j + 2] for j in range(len(s) - 1))
        return set(s.split())

    q_tokens = _tokens(q_text)
    if not q_tokens:
        return True
    for known in known_questions:
        k_tokens = _tokens(known)
        if not k_tokens:
            continue
        inter = len(q_tokens & k_tokens)
        # 非对称重叠率: 交集 / 较短方词数(更贴近"q 是否已被已知覆盖")
        denom = min(len(q_tokens), len(k_tokens))
        if denom and inter / denom >= threshold:
            return False
    return True


def build_mastery_context(mastery: dict, doc_path: str) -> str:
    """构建注入 prompt 的元认知上下文(掌握度 + 缺口 + 已知记忆)。"""
    t = topic_mastery(mastery, doc_path)
    lines = [f"该主题(文档 {doc_path})当前掌握画像:"]
    if not t["learned"]:
        lines.append("  - 尚未学习(首次接触, 以建立基础为主)")
    else:
        lines.append(f"  - 已学习, 已批准记忆 {t['approved_memories']} 条, "
                     f"平均得分 {t['avg_score']:.1f}/5")
        if t["gaps"] > 0:
            lines.append(f"  - 存在 {t['gaps']} 个未解决学习缺口(gaps), 需针对性补强")
    known = (mastery.get("known_questions") or [])[:6]
    if known:
        lines.append("已掌握的知识(新问题须避开重复, 聚焦信息增益):")
        for k in known:
            lines.append(f"  - {k}")
    lines.append("要求: 生成的问题难度应略高于当前掌握水平(最近发展区), "
                 "优先探索未知与薄弱之处, 不得与已知知识重复。")
    return "\n".join(lines)
