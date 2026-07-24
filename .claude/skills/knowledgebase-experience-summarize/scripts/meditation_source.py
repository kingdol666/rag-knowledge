#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meditation Source Harvester — 冥想记忆的"问题矿源".

Harvests KB-relevant user questions from the harness chat DB (claude-chat.db),
clusters them by semantic similarity, and ranks by frequency so the agent can
distill recurring topics into experiences (OpenClaw-style meditation memory).

This is a BEST-EFFORT, stateless, dependency-free harvester. It:
  * reads `messages` where sdk_type='user'
  * parses the JSON envelope to extract plain text
  * drops test/ping noise and KB-irrelevant chatter via a keyword filter
  * clusters near-duplicate questions (token Jaccard)
  * emits a ranked JSON list of clusters for the agent's meditation step

It NEVER writes anything. Missing DB / unreadable content → empty result, exit 0.

Usage:
    python meditation_source.py                         # defaults
    python meditation_source.py --db path/to.db --days 14 --top 30
    python meditation_source.py --json > clusters.json  # machine output

The agent should pair this output with the CURRENT session's KB Q&A context
(the agent has richer, guaranteed-KB-relevant context than the raw chat log).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# ── KB-relevance signal keywords (CN + EN) ────────────────────────────────
KB_KEYWORDS = [
    # Chinese
    "知识库", "经验", "文档", "搜索", "检索", "查询", "入库", "上传", "解析",
    "图谱", "整理", "校验", "标签", "向量", "怎么", "如何", "为什么", "报错",
    "失败", "故障", "排查", "部署", "配置", "索引", "去重", "迁移", "移动",
    "删除", "更新", "合并", "重命名", "搜", "查", "帮",
    # English
    "knowledge", "kb ", "kb-", "experience", "document", "search", "retriev",
    "ingest", "upload", "parse", "graph", "organize", "verify", "tag",
    "vector", "index", "neo4j", "chroma", "mineru", "rag", "mcp",
    "how to", "how do", "what is", "why", "error", "fail", "debug",
    "deploy", "config", "dedup", "migrate", "move", "delete", "rename",
]

# ── Noise / test-ping patterns to discard ─────────────────────────────────
NOISE_PATTERNS = [
    r"^\s*reply\s*[:：]", r"reply\s+with\s+exactly", r"reply\s+only",
    r"say\s+exactly", r"what\s+is\s+\d+\s*[\+\-\*\/]\s*\d+",
    r"\b(final_ok|claude_ok|reasoning_high_ok|pong|ok|okay)\b\s*$",
    r"remember\s+(the\s+)?code\b", r"what\s+code\s+did\s+i\s+tell",
    r"read\s+the\s+file\b.*\bmust\s+use\s+a\s+tool\b",
    # Numbered file-dump detection: "1 foo\n2 bar\n3 baz" (pasted file content).
    r"^\d+\s+\S.*\n\d+\s+\S",
]
NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]

# ── Question / intent signal (a genuine user question must contain one) ────
INTENT_MARKERS = [
    "?", "？",
    "怎么", "如何", "为什么", "为啥", "啥", "什么", "哪里", "哪儿", "哪",
    "能否", "可以", "帮我", "请帮", "我想", "我要", "需要", "怎么办",
    "吗", "呢", "嘛", "请",
    "how", "what", "why", "where", "when", "who", "which",
    "can you", "could you", "would you", "is there", "are there",
    "do you", "does", "please", "show me", "give me", "explain", "tell me",
]

# ── Tool / system output prefixes to discard (not real user questions) ────
SYSTEM_PREFIXES = (
    "tool permission", "launching skill", "async agent", "file does not exist",
    "unable to verify", "base directory for this skill", "no matching deferred",
    "knowledge_base:", "the boulder", "hook success", "system-reminder",
    "memory updated", "reading ", "memory://", "artifact://", "skill://",
    "now i", "step ", "phase ", "i'll", "i will", "let me",
)

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


def extract_text(raw: str) -> str:
    """Extract plain user text from a stored message payload.

    Stored content may be: a JSON envelope, a JSON list of blocks, or raw text.
    """
    if not raw:
        return ""
    s = raw.strip()
    if not s.startswith("{") and not s.startswith("["):
        return s
    try:
        obj = json.loads(s)
    except Exception:
        return s
    # Walk common shapes to find a text string.
    candidates = [obj]
    out: list[str] = []
    while candidates:
        node = candidates.pop()
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for k in ("text", "content", "message"):
                if k in node:
                    candidates.append(node[k])
        elif isinstance(node, list):
            candidates.extend(node)
    return " ".join(t.strip() for t in out if t.strip())


def is_noise(text: str) -> bool:
    low = text.lower()
    if len(low) < 6:
        return True
    for rx in NOISE_RE:
        if rx.search(low):
            return True
    # Reject tool/system output that leaked in under sdk_type='user'.
    for prefix in SYSTEM_PREFIXES:
        if low.startswith(prefix):
            return True
    # Reject JSON/data dumps (tool results, file contents).
    stripped = text.lstrip()
    if stripped[0:1] in ("{", "[") and stripped[0:2] not in ("{ ",):
        return True
    return False


def has_intent(text: str) -> bool:
    """A genuine user question contains at least one intent marker."""
    low = text.lower()
    for marker in INTENT_MARKERS:
        if marker in low:
            return True
    return False


def kb_relevance(text: str) -> int:
    """Score how KB-relevant a question is (count of distinct keyword hits)."""
    low = text.lower()
    score = 0
    for kw in KB_KEYWORDS:
        if kw in low:
            score += 1
    return score


def tokenize(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(text) if len(tok) > 1}


def cluster(questions: list[dict], threshold: float = 0.45) -> list[list[dict]]:
    """Greedy token-Jaccard clustering. Each cluster is a list of question dicts."""
    clusters: list[list[dict]] = []
    reps: list[set[str]] = []
    for q in sorted(questions, key=lambda d: d["relevance"], reverse=True):
        toks = q["tokens"]
        placed = False
        for i, rep in enumerate(reps):
            inter = len(toks & rep)
            union = len(toks | rep) or 1
            if union and inter / union >= threshold:
                clusters[i].append(q)
                # Update representative as union of tokens (loosens slowly).
                reps[i] |= toks
                placed = True
                break
        if not placed:
            clusters.append([q])
            reps.append(set(toks))
    return clusters


def harvest(db_path: str, days: int, min_len: int, max_len: int = 300) -> list[dict]:
    if not os.path.exists(db_path):
        return []
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
    rows: list[tuple] = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.cursor()
        cur.execute(
            "SELECT session_id, content, created_at FROM messages "
            "WHERE sdk_type='user' ORDER BY id ASC"
        )
        rows = cur.fetchall()
        con.close()
    except sqlite3.OperationalError:
        # Read-only URI may fail on Windows locks; retry normal connect.
        try:
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute(
                "SELECT session_id, content, created_at FROM messages "
                "WHERE sdk_type='user' ORDER BY id ASC"
            )
            rows = cur.fetchall()
            con.close()
        except Exception:
            return []
    except Exception:
        return []

    questions: list[dict] = []
    for sid, content, created in rows:
        text = extract_text(content or "")
        text = " ".join(text.split())
        if len(text) < min_len or len(text) > max_len or is_noise(text):
            continue
        # Reject inline numbered file-dumps: "1 foo 2 bar 3 baz".
        if re.match(r"^\d+\s+\S.*\s\d+\s+\S.*\s\d+\s+\S", text):
            continue
        if not has_intent(text):
            continue
        # Optional time window (created_at may be missing/unparseable).
        if created:
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff_dt:
                    continue
            except Exception:
                pass  # keep unparseable/old timestamps rather than dropping
        rel = kb_relevance(text)
        if rel < 1:
            continue
        questions.append({
            "text": text, "session": sid or "", "relevance": rel,
            "tokens": tokenize(text),
        })
    return questions


def main() -> int:
    ap = argparse.ArgumentParser(description="Harvest KB-relevant question clusters for meditation.")
    ap.add_argument("--db", default=os.path.join("storage", "claude-chat.db"),
                    help="path to chat DB (default: storage/claude-chat.db)")
    ap.add_argument("--days", type=int, default=7, help="lookback window in days (default: 7)")
    ap.add_argument("--min-length", type=int, default=6, help="min question char length (default: 6)")
    ap.add_argument("--max-length", type=int, default=300, help="max question char length (default: 300)")
    ap.add_argument("--top", type=int, default=20, help="max clusters to emit (default: 20)")
    ap.add_argument("--threshold", type=float, default=0.45, help="cluster Jaccard threshold (default: 0.45)")
    ap.add_argument("--json", action="store_true", help="emit compact JSON only (for agent parsing)")
    args = ap.parse_args()
    questions = harvest(args.db, args.days, args.min_length, args.max_length)
    clusters = cluster(questions, args.threshold)

    results = []
    for members in clusters:
        members_sorted = sorted(members, key=lambda d: d["relevance"], reverse=True)
        rep = max(members_sorted, key=lambda d: len(d["text"]))
        results.append({
            "representative": rep["text"],
            "count": len(members),
            "max_relevance": max(m["relevance"] for m in members),
            "samples": [m["text"] for m in members_sorted[:5]],
        })
    results.sort(key=lambda c: (c["count"], c["max_relevance"]), reverse=True)
    results = results[: args.top]

    payload = {
        "success": True,
        "source_db": os.path.abspath(args.db),
        "window_days": args.days,
        "total_questions": len(questions),
        "total_clusters": len(results),
        "note": ("Raw chat history is approximate. Agent MUST merge with the "
                 "current session's KB Q&A and verify each topic before authoring."),
        "clusters": results,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    print(f"== Meditation Source Harvest ==")
    print(f"db        : {payload['source_db']}")
    print(f"window    : {payload['window_days']} days")
    print(f"questions : {payload['total_questions']} KB-relevant")
    print(f"clusters  : {payload['total_clusters']}\n")
    for i, c in enumerate(results, 1):
        print(f"[{i}] x{c['count']}  (rel={c['max_relevance']})  {c['representative'][:90]}")
        for s in c["samples"][1:3]:
            print(f"      · {s[:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
