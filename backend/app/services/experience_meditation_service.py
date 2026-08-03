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


# ── Signal Harvesting (Chat DB → meditation_signals) ─────────────────

def harvest_signals_to_db(db_path: str, days: int = 7, kb_filter: str = "") -> int:
    """Extract real KB Q&A signals from chat DB by parsing MCP tool calls.

    ONLY captures signals where the user asked a question AND the assistant
    made actual MCP tool calls to kb_search_*/kb_doc_read against a specific KB.
    This ensures every signal is backed by real KB interaction — no fake signals.

    Returns count of new signals inserted.
    """
    import sqlite3 as _sqlite3
    from app.services.meditation_db import save_signal, get_pending_signals

    if not os.path.exists(db_path):
        logger.debug("Chat DB not found: %s", db_path)
        return 0

    try:
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
    except Exception as e:
        logger.warning("Failed to open chat DB: %s", e)
        return 0

    inserted = 0
    try:
        # Step 1: Find user messages (sdk_type='user')
        user_rows = conn.execute(
            """SELECT id, session_id, content, created_at FROM messages
               WHERE sdk_type = 'user'
                 AND created_at >= datetime('now', ?)
               ORDER BY created_at DESC LIMIT 100""",
            (f"-{days} days",),
        ).fetchall()

        for user_row in user_rows:
            try:
                user_data = json.loads(user_row["content"])
            except Exception:
                continue

            # Extract user question text
            user_msg = user_data.get("message", {})
            content_blocks = user_msg.get("content", [])
            if isinstance(content_blocks, str):
                question_text = content_blocks
            elif isinstance(content_blocks, list):
                question_text = " ".join(
                    b.get("text", "") for b in content_blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                question_text = str(content_blocks)

            if not question_text or len(question_text) < 10:
                continue
            if _is_noise(question_text):
                continue

            session_id = user_row["session_id"] or ""

            # Step 2: Find assistant response in same session with KB tool calls
            assistant_rows = conn.execute(
                """SELECT id, content FROM messages
                   WHERE session_id = ? AND sdk_type = 'assistant'
                     AND id > ?
                   ORDER BY id ASC LIMIT 5""",
                (session_id, user_row["id"]),
            ).fetchall()

            kb_ids_found = set()
            retrieved_docs = []
            assistant_answer = ""

            for asst_row in assistant_rows:
                try:
                    asst_data = json.loads(asst_row["content"])
                except Exception:
                    continue

                asst_msg = asst_data.get("message", {})
                asst_content = asst_msg.get("content", [])
                if isinstance(asst_content, str):
                    assistant_answer = asst_content[:1000]
                    continue
                if not isinstance(asst_content, list):
                    continue

                for block in asst_content:
                    if not isinstance(block, dict):
                        continue
                    # Extract text for answer
                    if block.get("type") == "text":
                        assistant_answer += block.get("text", "")[:500]
                    # Extract tool_use blocks
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        # Check if this is a KB-related tool call
                        if any(kw in tool_name for kw in ["kb_search", "kb_doc_read", "kb_list", "kb_get"]):
                            kb_id = tool_input.get("kb_id", "") or tool_input.get("kbId", "")
                            if kb_id and kb_filter and kb_id != kb_filter:
                                continue  # Skip if filtering for a different KB
                            if kb_id:
                                kb_ids_found.add(kb_id)
                            doc_path = tool_input.get("doc_path", "") or tool_input.get("path", "")
                            if doc_path:
                                retrieved_docs.append({"path": doc_path})
                    # Check for tool_result with kb references
                    if block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, str) and "kb_" in result_content:
                            pass  # Already captured via tool_use

            # Only create signal if we found actual KB tool calls
            if not kb_ids_found:
                continue

            # Use the first KB found, or the filter
            target_kb = kb_filter if kb_filter else list(kb_ids_found)[0]

            # Dedup: check if similar question already exists
            existing = get_pending_signals(target_kb, days=days)
            if any(
                _tokenize(question_text) & _tokenize(s.get("question_text", ""))
                for s in existing
            ):
                continue

            try:
                save_signal(
                    session_id=session_id,
                    kb_id=target_kb,
                    question_text=question_text[:500],
                    retrieved_docs=retrieved_docs[:10],
                    assistant_answer=assistant_answer[:2000],
                    resolved=False,
                )
                inserted += 1
            except Exception:
                pass

    except Exception as e:
        logger.warning("Signal harvesting error: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if inserted:
        logger.info("Harvested %d real KB interaction signals from chat DB (last %d days)", inserted, days)
        _check_incremental_trigger(kb_filter, inserted)
    return inserted


def _check_incremental_trigger(kb_id: str, new_count: int) -> None:
    """Check if incremental meditation should be triggered for a KB."""
    if not kb_id or kb_id == "unknown":
        return
    try:
        from app.services.kb_meditation_config import get_meditation_config
        from app.services.meditation_db import get_pending_signals
        cfg = get_meditation_config(kb_id)
        if not cfg.get("success"):
            return
        config = cfg["config"]
        if not config.get("enabled") or not config.get("incremental_enabled", True):
            return
        min_count = config.get("min_cluster_count", 2)
        pending = get_pending_signals(kb_id, days=config.get("interval_hours", 24) // 24 or 7)
        if len(pending) >= min_count:
            logger.info("Incremental trigger: %d signals >= %d threshold for KB %s",
                        len(pending), min_count, kb_id)
            # Fire-and-forget: don't block the harvester
            asyncio.ensure_future(_fire_incremental_meditation(kb_id, config, pending))
    except Exception:
        logger.debug("Incremental trigger check skipped", exc_info=True)


async def _fire_incremental_meditation(kb_id: str, config: dict, signals: list) -> None:
    """Fire incremental meditation for a KB (non-blocking)."""
    try:
        from app.services.agent_harness_manager import agent_harness
        from app.services.kb_meditation_config import get_meditation_config
        cfg = get_meditation_config(kb_id)
        kb_path = cfg.get("kb_path", kb_id)
        result = await agent_harness.synthesize_experiences(
            kb_path=kb_path, kb_id=kb_id, signals=signals,
            kb_config=config, trigger="incremental",
        )
        if result.get("success"):
            from app.services.meditation_db import mark_signals_derived
            signal_ids = [s.get("id") for s in signals if s.get("id")]
            if signal_ids:
                mark_signals_derived(signal_ids)
    except Exception as e:
        logger.warning("Incremental meditation failed for KB %s: %s", kb_id, e)

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
        self._lock = asyncio.Lock()
        self._kb_locks: dict[str, asyncio.Lock] = {}
        self._wake = asyncio.Event()

    def _get_kb_lock(self, kb_path: str) -> asyncio.Lock:
        """Get or create a per-KB lock to prevent concurrent meditation on same KB."""
        if kb_path not in self._kb_locks:
            self._kb_locks[kb_path] = asyncio.Lock()
        return self._kb_locks[kb_path]

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
            "running_now": self._lock.locked(),
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

    # ── Background Loop (KB-aware) ──────────────────────────────────────

    def _soul_mode_active(self) -> bool:
        """是否存在已启用(meditation_mode=soul 且 enabled=True)的人格库。

        SOUL 定时训练独立于 experience_auto 全局开关: 只要有人格库开启
        soul 冥想,调度循环就必须持续唤醒(间隔取各库最小 interval_hours)。
        """
        try:
            from app.services.kb_meditation_config import get_all_kb_meditation_configs
            for kb_cfg in get_all_kb_meditation_configs():
                c = kb_cfg.get("config", {})
                if c.get("meditation_mode") == "soul" and c.get("enabled"):
                    return True
        except Exception:
            pass
        return False

    def _soul_min_interval_hours(self) -> int | None:
        """已启用 soul 库的最小 interval_hours(决定循环唤醒间隔)。"""
        try:
            from app.services.kb_meditation_config import get_all_kb_meditation_configs
            mins: list[int] = []
            for kb_cfg in get_all_kb_meditation_configs():
                c = kb_cfg.get("config", {})
                if c.get("meditation_mode") == "soul" and c.get("enabled"):
                    try:
                        mins.append(int(c.get("interval_hours", 24)))
                    except (TypeError, ValueError):
                        continue
            return min(mins) if mins else None
        except Exception:
            return None

    async def _loop(self):
        """Main scheduler loop. KB-aware: iterates over KBs with meditation configs."""
        while True:
            try:
                cfg = config.experience_auto_config
                soul_active = self._soul_mode_active()
                if not cfg.get("enabled", False) and not soul_active:
                    self._wake.clear()
                    try:
                        await asyncio.wait_for(self._wake.wait(), timeout=300)
                    except asyncio.TimeoutError:
                        pass
                    continue

                # 唤醒间隔: 全局经验冥想与 soul 库各自 interval 取最小,
                # 保证 interval_hours 更短的人格库也能按时触发
                interval = int(cfg.get("interval_hours", 24))
                soul_interval = self._soul_min_interval_hours()
                if soul_interval and soul_interval < interval:
                    interval = soul_interval
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=interval * 3600)
                except asyncio.TimeoutError:
                    pass

                if not config.experience_auto_config.get("enabled", False) and not self._soul_mode_active():
                    continue

                await self._run_kb_aware_meditation()

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Meditation loop error — will retry next cycle")
                await asyncio.sleep(60)

    async def _run_kb_aware_meditation(self) -> dict:
        """KB-aware meditation: harvest signals → iterate KBs → spawn agent harness."""
        from app.services.kb_meditation_config import get_all_kb_meditation_configs
        from app.services.agent_harness_manager import agent_harness
        from app.services.meditation_db import get_pending_signals

        self._last_run = datetime.now(timezone.utc)
        report = {
            "timestamp": self._last_run.isoformat(),
            "kbs_scanned": 0,
            "kbs_meditated": 0,
            "experiences_created": 0,
            "drafts_created": 0,
            "errors": [],
            "results": [],
        }

        try:
            kb_configs = get_all_kb_meditation_configs()
            report["kbs_scanned"] = len(kb_configs)

            for kb_cfg in kb_configs:
                kb_id = kb_cfg["kb_id"]
                kb_path = kb_cfg["kb_path"]
                kb_name = kb_cfg.get("kb_name", kb_path)
                config = kb_cfg["config"]

                if not config.get("enabled", False):
                    continue

                # ── M0.4 SOUL mode branch: soul KBs skip the entire experience path ──
                mode = config.get("meditation_mode", "experience")
                if mode == "soul":
                    await self._run_soul_meditation(kb_cfg)
                    continue

                # Check if due
                last_run_at = config.get("last_run_at")
                if last_run_at:
                    try:
                        last_dt = datetime.fromisoformat(last_run_at)
                        interval_h = config.get("interval_hours", 24)
                        if (datetime.now(timezone.utc) - last_dt).total_seconds() < interval_h * 3600:
                            continue  # Not due yet
                    except Exception:
                        pass

                # Get pending signals
                lookback_days = config.get("interval_hours", 24) // 24 or 7
                signals = get_pending_signals(kb_id, days=lookback_days)
                if not signals:
                    continue

                # Check KB lock
                kb_lock = self._get_kb_lock(kb_path)
                if kb_lock.locked():
                    continue

                logger.info("Meditation: triggering for KB %s (%d signals)", kb_name, len(signals))

                try:
                    async with kb_lock:
                        result = await agent_harness.synthesize_experiences(
                            kb_path=kb_path,
                            kb_id=kb_id,
                            signals=signals,
                            kb_config=config,
                            trigger="scheduled",
                        )
                    report["results"].append({
                        "kb_id": kb_id,
                        "kb_name": kb_name,
                        "result": result,
                    })
                    if result.get("success"):
                        report["kbs_meditated"] += 1
                        report["experiences_created"] += len(result.get("experiences", []))
                        report["drafts_created"] += len(result.get("drafts", []))

                        # Mark signals as derived
                        from app.services.meditation_db import mark_signals_derived
                        signal_ids = [s.get("id") for s in signals if s.get("id")]
                        if signal_ids:
                            mark_signals_derived(signal_ids)

                        # Update KB YAML metadata
                        from app.services.kb_meditation_config import update_meditation_config
                        update_meditation_config(kb_id, {
                            "last_run_at": self._last_run.isoformat(),
                            "last_run_status": "success",
                            "total_runs": config.get("total_runs", 0) + 1,
                            "total_experiences_generated": config.get("total_experiences_generated", 0) + len(result.get("experiences", [])) + len(result.get("drafts", [])),
                        })
                    else:
                        report["errors"].append(f"{kb_name}: {result.get('error', 'unknown')}")
                        from app.services.kb_meditation_config import update_meditation_config
                        update_meditation_config(kb_id, {
                            "last_run_at": self._last_run.isoformat(),
                            "last_run_status": "failed",
                            "total_runs": config.get("total_runs", 0) + 1,
                        })

                except Exception as e:
                    logger.exception("Meditation failed for KB %s: %s", kb_name, e)
                    report["errors"].append(f"{kb_name}: {e}")

            self._last_result = report
            logger.info("KB-aware meditation complete: scanned=%d meditated=%d exp=%d drafts=%d errors=%d",
                        report["kbs_scanned"], report["kbs_meditated"],
                        report["experiences_created"], report["drafts_created"],
                        len(report["errors"]))
            return report

        except Exception as e:
            logger.exception("KB-aware meditation cycle failed")
            report["error"] = str(e)
            self._last_result = report
            return report

    async def _run_soul_meditation(self, kb_cfg: dict) -> dict:
        """Soul-mode meditation: incremental soul learning (2.6 完整实现).

        调度器路径与手动 soul_learn 共用 per-soul 锁(learn_incremental 内部获取),
        不用本循环的 kb_lock(避免与手动路径互斥语义不一致)。
        """
        from app.services.kb_meditation_config import update_meditation_config

        kb_id = kb_cfg["kb_id"]
        kb_path = kb_cfg.get("kb_path", kb_id)
        config = kb_cfg.get("config", {})

        # Due check (soul mode manages its own interval/cooldown)
        last_run_at = config.get("last_run_at")
        if last_run_at:
            try:
                last_dt = datetime.fromisoformat(last_run_at)
                interval_h = config.get("interval_hours", 24)
                if (datetime.now(timezone.utc) - last_dt).total_seconds() < interval_h * 3600:
                    return {"mode": "soul", "kb_id": kb_id, "status": "not_due"}
            except Exception:
                pass

        logger.info("Soul meditation trigger for %s (mode=soul)", kb_id)
        try:
            from app.services.soul_learn import learn_incremental
            rounds = int(config.get("rounds_per_run", 1) or 1)
            report = await learn_incremental(kb_id, rounds=rounds)
        except Exception as e:
            logger.exception("Soul meditation failed for %s", kb_id)
            try:
                update_meditation_config(kb_id, {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_run_status": "failed",
                    "total_runs": config.get("total_runs", 0) + 1,
                })
            except Exception:
                pass
            return {"mode": "soul", "kb_id": kb_id, "kb_path": kb_path,
                    "status": "failed", "error": str(e)[:300]}

        ok = bool(report.get("success", True)) and not report.get("error")
        try:
            update_meditation_config(kb_id, {
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "last_run_status": "success" if ok else "failed",
                "total_runs": config.get("total_runs", 0) + 1,
                "total_experiences_generated": config.get("total_experiences_generated", 0)
                + int(report.get("memories_created", 0) or 0),
            })
        except Exception as e:
            logger.warning("Failed to update soul meditation config for %s: %s", kb_id, e)

        return {"mode": "soul", "kb_id": kb_id, "kb_path": kb_path,
                "status": "completed" if ok else "failed",
                "questions": report.get("questions_generated", 0),
                "memories": report.get("memories_created", 0),
                "gaps": report.get("gaps_count", 0),
                "cost": report.get("cost_estimate", 0.0)}

    # ── Meditation Cycle ───────────────────────────────────────────────

    async def run_meditation_now(self, kb_id: str | None = None) -> dict:
        """Run one meditation cycle. Returns a report dict.

        Args:
            kb_id: If provided, only meditate on this specific KB.
                  If None, run for all KBs (subject to per-KB enabled config).

        Steps:
          1. Harvest question clusters from chat DB
          2. Load KB catalog (optionally filter to kb_id)
          3. For each cluster ≥ min_cluster_count:
             a. Match to KB
             b. Vector-search KB for answer docs
             c. Check existing experiences (skip if covered)
             d. Heuristic-extract from matched docs
             e. Create draft
          4. Return report
        """
        if self._lock.locked():
            return {"success": False, "error": "Meditation already running"}
        async with self._lock:
            return await self._run_meditation_cycle(kb_filter=kb_id)

    async def _run_meditation_cycle(self, kb_filter: str | None = None) -> dict:
        """Core meditation cycle logic (called under lock)."""
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
            # Apply optional KB filter
            if kb_filter:
                kbs = [
                    k for k in kbs
                    if k["id"] == kb_filter or k["path"] == kb_filter
                    or k["path"].replace("\\", "/") == kb_filter.replace("\\", "/")
                ]
                if not kbs:
                    report["summary"] = f"KB not found or not a knowledge base: {kb_filter}"
                    report["error"] = "kb_not_found"
                    self._last_result = report
                    return report
                logger.info("Meditation: filtered to single KB: %s", kbs[0]["name"])
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

                # 3b. Search KB for answer docs (run in executor to avoid blocking)
                try:
                    from app.services.vector_service import vector_service
                    results = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: vector_service.search(
                            query=cluster["representative"],
                            kb_id=kb_path, top_k=3, score_threshold=0.3,
                        )
                    )
                except Exception as e:
                    logger.warning("Meditation: vector search failed for '%s': %s",
                                   cluster["representative"][:50], e)
                    results = []

                if not results:
                    report["skipped_no_kb"].append(
                        f"{cluster['representative'][:60]} (no docs found)")
                    continue

                # Collect verified doc paths + snippets
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
                    cluster_tokens = _tokenize(cluster["representative"])
                    covered = False
                    for e in exps:
                        exp_text = f"{e.get('title','')} {e.get('scenario','')} {e.get('problem','')}".lower()
                        token_matches = sum(1 for t in cluster_tokens if t.lower() in exp_text)
                        if token_matches >= 2:
                            covered = True
                            break
                    if covered:
                        report["already_covered"] += 1
                        report["skipped_covered"].append(
                            cluster["representative"][:80])
                        continue
                except Exception:
                    pass

                # 3d. Build draft from verified doc content
                solution_parts = []
                for i, snip in enumerate(doc_snippets[:2], 1):
                    solution_parts.append(f"参考文档{i}：{snip}...")
                solution = "\n\n".join(solution_parts) if solution_parts else \
                    "从知识库文档中自动归纳，待审核时精炼。"

                _LESSON_KW = (
                    "建议", "应该", "需要", "注意", "必须", "关键", "确保",
                    "避免", "推荐", "最佳", "重要", "首先", "核心", "步骤",
                    "recommend", "should", "must", "key", "important",
                    "ensure", "avoid", "critical", "best", "essential",
                    "first", "always", "never", "use", "apply", "implement",
                    "configur", "enabl", "require", "prefer",
                )
                key_lessons = []
                for snip in doc_snippets:
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
                    all_sents = sorted(
                        [s.strip() for snip in doc_snippets
                         for s in re.split(r'[.。！？\n]', snip)
                         if 40 <= len(s.strip()) <= 200],
                        key=len, reverse=True)
                    key_lessons = all_sents[:2] if all_sents else \
                        ["待审核时从文档中提炼具体可执行教训。"]

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


# Singleton
meditation_scheduler = ExperienceMeditationScheduler()
