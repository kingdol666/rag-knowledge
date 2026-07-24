"""Experience Meditation Service — 经验自动归纳冥想服务.

Periodic background scheduler that auto-induces experience drafts from
recurring user questions + KB answers. Like OpenClaw's meditation memory:

    harvest Q&A from chat history → match to KBs → verify against real
    KB docs → create drafts in the review pool.

The backend does MECHANICAL work only (no LLM):
  1. Harvest question clusters from storage/claude-chat.db
  2. Match each cluster to the most relevant KB (keyword overlap)
  3. Vector-search that KB to find the real answer docs
  4. Check existing experiences (skip if already covered)
  5. Heuristic-extract key points from the matched docs
  6. Write a draft to the KB's draft pool for agent/user review

Correctness guarantee: every draft's solution comes from real KB document
content (vector search hits), never fabricated. Quality gate happens at
draft approval time (LLM refinement by the agent).

Config (config.yml → experience_auto section, hot-reloadable):
  enabled, interval_hours, lookback_days, min_cluster_count,
  max_drafts_per_run, dry_run.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import config
from app.utils.paths import get_storage_root, PROJECT_ROOT

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_CHAT_DB_REL = os.path.join("storage", "claude-chat.db")

KB_KEYWORDS = [
    "知识库", "经验", "文档", "搜索", "检索", "查询", "入库", "上传", "解析",
    "图谱", "整理", "校验", "标签", "向量", "怎么", "如何", "为什么", "报错",
    "失败", "故障", "排查", "部署", "配置", "索引", "去重", "迁移", "移动",
    "knowledge", "experience", "document", "search", "retriev", "ingest",
    "upload", "parse", "graph", "organize", "verify", "vector", "index",
    "neo4j", "chroma", "mineru", "rag", "mcp", "how", "what", "why", "error",
]

NOISE_RE = [
    re.compile(p, re.IGNORECASE) for p in (
        r"^\s*reply\s*[:：]", r"reply\s+with\s+exactly", r"reply\s+only",
        r"say\s+exactly", r"what\s+is\s+\d+\s*[+\-*/]\s*\d+",
        r"\b(final_ok|claude_ok|reasoning_high_ok|pong|ok)\b\s*$",
        r"remember\s+(the\s+)?code\b",
        r"^\d+\s+\S.*\n\d+\s+\S",
    )
]

SYSTEM_PREFIXES = (
    "tool permission", "launching skill", "async agent", "file does not exist",
    "unable to verify", "base directory", "no matching deferred",
    "knowledge_base:", "the boulder", "hook success", "system-reminder",
)

INTENT_MARKERS = [
    "?", "？", "怎么", "如何", "为什么", "啥", "什么", "哪里", "能否", "可以",
    "帮我", "我想", "需要", "吗", "呢", "how", "what", "why", "where",
    "can you", "could you", "is there", "do you", "please", "explain",
]

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


# ── Question Harvester (mirrors meditation_source.py, stdlib-only) ────────

def _extract_text(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    if not s.startswith("{") and not s.startswith("["):
        return s
    try:
        obj = json.loads(s)
    except Exception:
        return s
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


def _is_noise(text: str) -> bool:
    low = text.lower()
    if len(low) < 6 or len(text) > 300:
        return True
    for rx in NOISE_RE:
        if rx.search(low):
            return True
    for prefix in SYSTEM_PREFIXES:
        if low.startswith(prefix):
            return True
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        return True
    return False


def _has_intent(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in INTENT_MARKERS)


def _kb_relevance(text: str) -> int:
    low = text.lower()
    return sum(1 for kw in KB_KEYWORDS if kw in low)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1}


def _cluster(questions: list[dict], threshold: float = 0.45) -> list[list[dict]]:
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
                reps[i] |= toks
                placed = True
                break
        if not placed:
            clusters.append([q])
            reps.append(set(toks))
    return clusters


def harvest_questions(db_path: str, days: int) -> list[dict]:
    """Read user questions from chat DB, filter, and cluster."""
    if not os.path.exists(db_path):
        logger.warning("Meditation: chat DB not found at %s", db_path)
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT content, created_at FROM messages WHERE sdk_type='user'"
        ).fetchall()
        con.close()
    except Exception:
        try:
            con = sqlite3.connect(db_path)
            rows = con.execute(
                "SELECT content, created_at FROM messages WHERE sdk_type='user'"
            ).fetchall()
            con.close()
        except Exception as e:
            logger.warning("Meditation: cannot read chat DB: %s", e)
            return []

    questions: list[dict] = []
    for content, created in rows:
        text = " ".join(_extract_text(content or "").split())
        if _is_noise(text) or not _has_intent(text):
            continue
        if created:
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except Exception:
                pass
        rel = _kb_relevance(text)
        if rel < 1:
            continue
        questions.append({"text": text, "relevance": rel, "tokens": _tokenize(text)})

    return [
        {"representative": max(m, key=lambda d: len(d["text"]))["text"],
         "count": len(m),
         "max_relevance": max(q["relevance"] for q in m),
         "samples": [q["text"] for q in sorted(m, key=lambda d: d["relevance"], reverse=True)[:5]]}
        for m in _cluster(questions)
    ]


# ── KB Matching ───────────────────────────────────────────────────────────

def _match_kb(cluster: dict, kbs: list[dict]) -> str | None:
    """Match a question cluster to the most relevant KB by keyword overlap.

    kbs: list of {id, name, path, description} dicts from .tree-fs.json.
    Returns the KB path or None.
    """
    text = cluster["representative"].lower()
    tokens = _tokenize(cluster["representative"])
    best_path = None
    best_score = 0
    for kb in kbs:
        kb_text = f"{kb.get('name', '')} {kb.get('description', '')}".lower()
        kb_tokens = _tokenize(kb_text)
        overlap = len(tokens & kb_tokens)
        name_hit = 1 if kb.get("name", "").lower() in text else 0
        score = overlap + name_hit
        if score > best_score:
            best_score = score
            best_path = kb.get("path", "")
    return best_path if best_score > 0 else None


# ── Meditation Scheduler ──────────────────────────────────────────────────

class ExperienceMeditationScheduler:
    """Background scheduler for periodic experience auto-induction.

    Lifecycle:
      - start(): launched from main.py lifespan; spawns an asyncio task.
      - The task loops: read config → sleep interval → run_meditation → repeat.
      - Config changes (interval, enabled) are picked up each iteration
        (hot-reload via config.reload() called by the config API).
      - stop(): cancels the task on shutdown.
      - run_meditation_now(): manual trigger (API), runs one cycle immediately.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._last_run: datetime | None = None
        self._last_result: dict | None = None
        self._running = False
        self._wake = asyncio.Event()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self):
        """Start the background loop (idempotent)."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("Experience meditation scheduler started")

    async def stop(self):
        """Cancel the background loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Experience meditation scheduler stopped")

    def notify_config_change(self):
        """Wake the scheduler immediately when config is hot-reloaded."""
        self._wake.set()

    # ── Status ─────────────────────────────────────────────────────────

    @property
    def status(self) -> dict:
        """Current scheduler status for the API."""
        from app.config import config as _cfg
        cfg = _cfg.experience_auto_config
        return {
            "enabled": cfg.get("enabled", False),
            "interval_hours": cfg.get("interval_hours", 24),
            "running_now": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_result": self._last_result,
            "next_run_eta": self._next_run_eta(),
        }

    def _next_run_eta(self) -> str | None:
        if not self._last_run:
            return None
        from app.config import config as _cfg
        interval = _cfg.experience_auto_config.get("interval_hours", 24)
        nxt = self._last_run + timedelta(hours=interval)
        delta = nxt - datetime.now(timezone.utc)
        if delta.total_seconds() < 0:
            return "due now"
        hrs = int(delta.total_seconds() // 3600)
        mins = int((delta.total_seconds() % 3600) // 60)
        return f"{hrs}h {mins}m"

    # ── Background Loop ────────────────────────────────────────────────

    async def _loop(self):
        """Main scheduler loop. Reads config each iteration for hot-reload."""
        while True:
            try:
                cfg = config.experience_auto_config
                if not cfg.get("enabled", False):
                    # Disabled — sleep 5 min then re-check (hot-enable support).
                    self._wake.clear()
                    try:
                        await asyncio.wait_for(self._wake.wait(), timeout=300)
                    except asyncio.TimeoutError:
                        pass
                    continue

                interval = int(cfg.get("interval_hours", 24))
                # Sleep for the interval, but wake early if config changes.
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=interval * 3600)
                except asyncio.TimeoutError:
                    pass

                # Re-check enabled after wake (might have been disabled).
                if not config.experience_auto_config.get("enabled", False):
                    continue

                await self.run_meditation_now()

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Meditation loop error — will retry next cycle")
                await asyncio.sleep(60)

    # ── Meditation Cycle ───────────────────────────────────────────────

    async def run_meditation_now(self) -> dict:
        """Run one meditation cycle. Returns a report dict.

        Steps:
          1. Harvest question clusters from chat DB
          2. Load KB catalog
          3. For each cluster ≥ min_cluster_count:
             a. Match to KB
             b. Vector-search KB for answer docs
             c. Check existing experiences (skip if covered)
             d. Heuristic-extract from matched docs
             e. Create draft
          4. Return report
        """
        if self._running:
            return {"success": False, "error": "Meditation already running"}
        self._running = True
        self._last_run = datetime.now(timezone.utc)

        cfg = config.experience_auto_config
        lookback = int(cfg.get("lookback_days", 7))
        min_count = int(cfg.get("min_cluster_count", 2))
        max_drafts = int(cfg.get("max_drafts_per_run", 5))
        dry_run = cfg.get("dry_run", False)

        report: dict[str, Any] = {
            "timestamp": self._last_run.isoformat(),
            "lookback_days": lookback,
            "dry_run": dry_run,
            "clusters_scanned": 0,
            "clusters_considered": 0,
            "kb_matched": 0,
            "already_covered": 0,
            "drafts_created": 0,
            "drafts": [],
            "skipped_no_kb": [],
            "skipped_covered": [],
        }

        try:
            # 1. Harvest
            db_path = str(PROJECT_ROOT.parent / _CHAT_DB_REL)
            clusters = harvest_questions(db_path, lookback)
            report["clusters_scanned"] = len(clusters)
            logger.info("Meditation: harvested %d clusters from %d-day window",
                        len(clusters), lookback)

            if not clusters:
                report["summary"] = "No question clusters found in chat history."
                self._last_result = report
                return report

            # 2. Load KB catalog
            from app.services.experience_service import experience_service
            tree = experience_service._read_tree_fs()
            kbs = [
                {"id": f.get("id", ""), "name": f.get("name", ""),
                 "path": f.get("path", ""), "description": f.get("description", "")}
                for f in tree.get("folders", [])
                if f.get("isKnowledgeBase")
            ]
            if not kbs:
                report["summary"] = "No knowledge bases found."
                self._last_result = report
                return report

            # 3. Process clusters
            drafts_made = 0
            for cluster in clusters:
                if drafts_made >= max_drafts:
                    break
                if cluster["count"] < min_count:
                    continue
                report["clusters_considered"] += 1

                # 3a. Match KB
                kb_path = _match_kb(cluster, kbs)
                if not kb_path:
                    report["skipped_no_kb"].append(cluster["representative"][:80])
                    continue
                report["kb_matched"] += 1

                # 3b. Search KB for answer docs (real content verification)
                try:
                    from app.services.vector_service import vector_service
                    results = vector_service.search(
                        query=cluster["representative"],
                        kb_id=kb_path, top_k=3, score_threshold=0.3,
                    )
                except Exception as e:
                    logger.warning("Meditation: vector search failed for '%s': %s",
                                   cluster["representative"][:50], e)
                    results = []

                if not results:
                    report["skipped_no_kb"].append(
                        f"{cluster['representative'][:60]} (no docs found)")
                    continue

                # Collect verified doc paths + snippets (REAL KB content)
                related_docs = []
                doc_snippets = []
                for r in results[:3]:
                    dp = r.get("doc_path", "").replace("\\", "/")
                    if dp and dp not in related_docs:
                        related_docs.append(dp)
                    snippet = r.get("content", "")[:200]
                    if snippet:
                        doc_snippets.append(snippet)

                if not related_docs:
                    continue

                # 3c. Check existing experiences (skip if already covered)
                try:
                    existing = await experience_service.search_experiences(
                        kb_path, cluster["representative"], top_k=3)
                    exps = existing.get("experiences", [])
                    if exps and any(e.get("_score", 0) > 0.6 for e in exps):
                        report["already_covered"] += 1
                        report["skipped_covered"].append(
                            cluster["representative"][:80])
                        continue
                except Exception:
                    pass  # Non-fatal — proceed to draft creation

                # 3d. Build draft from verified doc content
                solution_parts = []
                for i, snip in enumerate(doc_snippets[:2], 1):
                    solution_parts.append(f"参考文档{i}：{snip}...")
                solution = "\n\n".join(solution_parts) if solution_parts else \
                    "从知识库文档中自动归纳，待审核时精炼。"

                # Extract key lessons from doc snippets (bilingual heuristic)
                _LESSON_KW = (
                    # Chinese signal words for actionable sentences
                    "建议", "应该", "需要", "注意", "必须", "关键", "确保",
                    "避免", "推荐", "最佳", "重要", "首先", "核心", "步骤",
                    # English signal words for actionable sentences
                    "recommend", "should", "must", "key", "important",
                    "ensure", "avoid", "critical", "best", "essential",
                    "first", "always", "never", "use", "apply", "implement",
                    "configur", "enabl", "require", "prefer",
                )
                key_lessons = []
                for snip in doc_snippets:
                    # Split on sentence boundaries (CN + EN + markdown)
                    sentences = re.split(r'[.。！？\n;；]|(?:\d+[.)]\s)', snip)
                    for s in sentences:
                        s = s.strip().lstrip('-*• ')
                        if 25 <= len(s) <= 200 and any(kw in s.lower() for kw in _LESSON_KW):
                            if s not in key_lessons:
                                key_lessons.append(s)
                        if len(key_lessons) >= 3:
                            break
                    if len(key_lessons) >= 3:
                        break
                if not key_lessons:
                    # Fallback: extract longest informative sentences as proto-lessons
                    all_sents = sorted(
                        [s.strip() for snip in doc_snippets
                         for s in re.split(r'[.。！？\n]', snip)
                         if 40 <= len(s.strip()) <= 200],
                        key=len, reverse=True)
                    key_lessons = all_sents[:2] if all_sents else \
                        ["待审核时从文档中提炼具体可执行教训。"]

                # Derive scenario from representative question
                tokens = _tokenize(cluster["representative"])
                scenario = "auto-" + "-".join(list(tokens)[:3]) if tokens else "auto-meditation"
                scenario = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff-]', '', scenario)[:60]

                title = cluster["representative"][:60]
                if len(cluster["representative"]) > 60:
                    title += "..."

                draft_data = {
                    "title": f"[冥想] {title}",
                    "scenario": scenario,
                    "category": "best_practice",
                    "problem": cluster["representative"],
                    "solution": solution,
                    "result": "success",
                    "key_lessons": key_lessons,
                    "tags": ["冥想归纳", "auto-meditation"] +
                            [t for t in list(tokens)[:3]],
                    "severity": "normal",
                    "related_docs": related_docs,
                    "extraction_method": "meditation",
                    "source_cluster_count": cluster["count"],
                    "source_samples": cluster["samples"][:3],
                }

                if dry_run:
                    report["drafts"].append({
                        "kb": kb_path,
                        "draft_id": None,
                        "title": draft_data["title"],
                        "related_docs": related_docs,
                        "dry_run": True,
                    })
                    drafts_made += 1
                    report["drafts_created"] = drafts_made
                    continue

                # 3e. Create draft in review pool
                try:
                    r = await experience_service.save_draft(kb_path, draft_data)
                    if r.get("success"):
                        report["drafts_created"] += 1
                        drafts_made += 1
                        report["drafts"].append({
                            "kb": kb_path,
                            "draft_id": r.get("draft_id"),
                            "title": draft_data["title"],
                            "related_docs": related_docs,
                        })
                        logger.info("Meditation: created draft %s @ %s",
                                    r.get("draft_id"), kb_path)
                except Exception as e:
                    logger.warning("Meditation: draft creation failed: %s", e)

            report["summary"] = (
                f"Scanned {report['clusters_scanned']} clusters, "
                f"considered {report['clusters_considered']}, "
                f"matched {report['kb_matched']} to KBs, "
                f"{report['already_covered']} already covered, "
                f"{'dry-run ' if dry_run else ''}created {report['drafts_created']} drafts."
            )
            logger.info("Meditation cycle complete: %s", report["summary"])
            self._last_result = report
            return report

        except Exception as e:
            logger.exception("Meditation cycle failed")
            report["error"] = str(e)
            self._last_result = report
            return report
        finally:
            self._running = False


# Singleton
meditation_scheduler = ExperienceMeditationScheduler()
