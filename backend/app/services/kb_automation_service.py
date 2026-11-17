"""KB Automation Service — 知识库自动化机制（自动经验总结）。

每个知识库可独立开启「自动经验总结」：
- 每篇文档入库（进入该 KB）计数器 +doc_count（状态持久化在
  storage/tree-file-system/.kb-automation.json，与 .kb-states.json 同层）
- 计数器每达到 interval（默认 5）的倍数，触发一次经验总结更新：
  首次创建一条滚动总结经验（provisional，带警示可用），后续触发复用
  同一条经验做真 update（experience_service.update_experience 会重写
  .md 并重索引向量）
- 总结内容纯规则生成（文档清单/主题分布/经验池快照/维护建议），无 LLM
  依赖，确定性可审计
"""
from __future__ import annotations

import json
import logging
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.models.experience_models import ExperienceCreate, ExperienceUpdate
from app.utils.atomic_io import atomic_write_text
from app.utils.paths import get_storage_root

logger = logging.getLogger(__name__)

_STATE_FILENAME = ".kb-automation.json"
DEFAULT_INTERVAL = 5
MAX_HISTORY = 20
MAX_DOCS_SINCE = 50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(p: str) -> str:
    return p.replace("\\", "/")


class KbAutomationService:
    """单例。每 KB 的自动经验总结开关、入库计数器与滚动总结。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = threading.Lock()
        return cls._instance

    # ── 状态持久化 ────────────────────────────────────────────

    @property
    def _state_path(self) -> Path:
        return get_storage_root() / _STATE_FILENAME

    def _load(self) -> dict:
        p = self._state_path
        if not p.exists():
            return {"version": 1, "interval": DEFAULT_INTERVAL, "kbs": {}}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data.setdefault("interval", DEFAULT_INTERVAL)
            data.setdefault("kbs", {})
            return data
        except Exception as e:
            logger.warning("Failed to read %s: %s", p, e)
            return {"version": 1, "interval": DEFAULT_INTERVAL, "kbs": {}}

    def _save(self, data: dict) -> None:
        try:
            atomic_write_text(
                self._state_path,
                json.dumps(data, ensure_ascii=False, indent=2),
            )
        except Exception as e:
            logger.error("Failed to write %s: %s", self._state_path, e)

    @staticmethod
    def _entry(data: dict, kb_id: str) -> dict:
        return data["kbs"].setdefault(kb_id, {
            "auto_experience": False,
            "doc_counter": 0,
            "trigger_count": 0,
            "summary_exp_id": "",
            "docs_since_summary": [],
            "history": [],
            "enabled_at": "",
            "updated_at": "",
        })

    # ── tree-fs 读取（与 experience_service 同一存储格式） ──────

    def _read_tree_fs(self) -> dict:
        tree_path = get_storage_root() / ".tree-fs.json"
        if not tree_path.exists():
            return {"folders": [], "files": []}
        try:
            return json.loads(tree_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read .tree-fs.json: %s", e)
            return {"folders": [], "files": []}

    def _resolve_kb(self, kb_id: str) -> Optional[dict]:
        """kb_id (UUID) → {path, name, description}；找不到返回 None。"""
        tree = self._read_tree_fs()
        for folder in tree.get("folders", []):
            if folder.get("id") == kb_id or folder.get("path") == kb_id:
                return folder
        return None

    def _kb_docs(self, kb_path: str) -> list[dict]:
        """KB 下全部文档（排除 experience/ 子目录），含 name/path/description。"""
        kb_norm = _normalize_path(kb_path) + "/"
        docs = []
        for f in self._read_tree_fs().get("files", []):
            fp = _normalize_path(f.get("path", ""))
            if not fp.startswith(kb_norm) or not fp.endswith(".md"):
                continue
            if "/experience/" in fp:
                continue
            docs.append({
                "path": fp,
                "name": f.get("name", fp.rsplit("/", 1)[-1]),
                "description": f.get("description", "") or "",
                "created_at": f.get("createdAt", ""),
            })
        docs.sort(key=lambda d: d["created_at"])
        return docs

    # ── 对外查询/开关 ─────────────────────────────────────────

    def get_status(self, kb_id: str) -> dict:
        with self._lock:
            data = self._load()
            entry = data["kbs"].get(kb_id)
        if not entry:
            return {
                "success": True, "kb_id": kb_id,
                "enabled": False, "doc_counter": 0,
                "interval": data.get("interval", DEFAULT_INTERVAL),
                "next_trigger_at": DEFAULT_INTERVAL,
                "trigger_count": 0, "summary_exp_id": "",
                "docs_since_summary": [], "history": [],
                "total_docs": self._count_docs(kb_id),
            }
        interval = data.get("interval", DEFAULT_INTERVAL)
        counter = entry.get("doc_counter", 0)
        next_at = (counter // interval) * interval + interval
        return {
            "success": True, "kb_id": kb_id,
            "enabled": bool(entry.get("auto_experience")),
            "doc_counter": counter,
            "interval": interval,
            "next_trigger_at": next_at,
            "trigger_count": entry.get("trigger_count", 0),
            "summary_exp_id": entry.get("summary_exp_id", ""),
            "docs_since_summary": entry.get("docs_since_summary", []),
            "history": entry.get("history", [])[-10:],
            "last_trigger_at": entry.get("last_trigger_at", ""),
            "enabled_at": entry.get("enabled_at", ""),
            "total_docs": self._count_docs(kb_id),
        }

    def _count_docs(self, kb_id: str) -> int:
        kb = self._resolve_kb(kb_id)
        return len(self._kb_docs(kb["path"])) if kb else 0

    def list_all(self) -> dict:
        with self._lock:
            data = self._load()
        return {
            "success": True,
            "interval": data.get("interval", DEFAULT_INTERVAL),
            "kbs": {
                kb_id: {
                    "enabled": bool(e.get("auto_experience")),
                    "doc_counter": e.get("doc_counter", 0),
                    "trigger_count": e.get("trigger_count", 0),
                    "summary_exp_id": e.get("summary_exp_id", ""),
                }
                for kb_id, e in data["kbs"].items()
            },
        }

    def set_enabled(self, kb_id: str, enabled: bool) -> dict:
        kb = self._resolve_kb(kb_id)
        if not kb:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        with self._lock:
            data = self._load()
            entry = self._entry(data, kb_id)
            entry["auto_experience"] = bool(enabled)
            entry["updated_at"] = _now()
            if enabled and not entry.get("enabled_at"):
                entry["enabled_at"] = _now()
            self._save(data)
        logger.info("KB automation %s: %s (%s)", "enabled" if enabled else "disabled", kb_id, kb.get("name"))
        return {"success": True, "kb_id": kb_id, "enabled": bool(enabled),
                "kb_name": kb.get("name", "")}

    # ── 入库计数钩子（web documents/create → 后端） ────────────

    async def record_ingest(self, kb_id: str, doc_path: str = "",
                            title: str = "", doc_count: int = 1) -> dict:
        """文档入库后调用：开启状态下计数 +doc_count；计数达到 interval
        的倍数触发经验总结更新。未开启时零副作用（fail-open）。"""
        with self._lock:
            data = self._load()
            entry = data["kbs"].get(kb_id)
            if not entry or not entry.get("auto_experience"):
                return {"success": True, "kb_id": kb_id, "enabled": False,
                        "counted": 0, "triggered": False}
            doc_count = max(1, int(doc_count or 1))
            entry["doc_counter"] = entry.get("doc_counter", 0) + doc_count
            counter = entry["doc_counter"]
            interval = data.get("interval", DEFAULT_INTERVAL)
            if doc_path or title:
                entry.setdefault("docs_since_summary", []).append({
                    "path": _normalize_path(doc_path), "title": title, "at": _now(),
                    "count": doc_count,
                })
                entry["docs_since_summary"] = entry["docs_since_summary"][-MAX_DOCS_SINCE:]
            triggered = counter > 0 and counter % interval == 0
            self._save(data)

        result = {
            "success": True, "kb_id": kb_id, "enabled": True,
            "counted": doc_count, "doc_counter": counter,
            "interval": interval, "triggered": triggered,
            "next_trigger_at": (counter // interval) * interval + interval,
        }
        if triggered:
            summary = await self._run_summary(kb_id, manual=False)
            result["trigger"] = summary
        return result

    async def trigger_summary(self, kb_id: str) -> dict:
        """手动触发一次经验总结（管理/测试用），无论开关状态。"""
        kb = self._resolve_kb(kb_id)
        if not kb:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        return await self._run_summary(kb_id, manual=True)

    # ── 滚动经验总结（首次创建，后续真 update） ─────────────────

    async def _run_summary(self, kb_id: str, manual: bool) -> dict:
        from app.services.experience_service import experience_service

        kb = self._resolve_kb(kb_id)
        if not kb:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        kb_path = kb.get("path", "")
        kb_name = kb.get("name", "") or kb_path

        # 快照本轮新增并清空（锁内），总结生成在锁外
        with self._lock:
            data = self._load()
            entry = self._entry(data, kb_id)
            docs_since = list(entry.get("docs_since_summary", []))
            entry["docs_since_summary"] = []
            prev_exp_id = entry.get("summary_exp_id", "")
            round_no = entry.get("trigger_count", 0) + 1
            self._save(data)

        docs = self._kb_docs(kb_path)
        exp_res = await experience_service.list_experiences(kb_id)
        exps = exp_res.get("experiences", []) if exp_res.get("success") else []
        body = self._build_summary_body(kb_name, docs, exps, docs_since, round_no, manual)

        # 复用已有总结经验（被删则回退新建）
        exp = self._find_exp(exps, prev_exp_id)
        if exp:
            merged_metrics = dict(exp.get("metrics") or {})
            merged_metrics.update({
                "auto_summary": True,
                "last_summary_round": round_no,
                "last_summary_at": _now(),
                "last_summary_docs_total": len(docs),
            })
            merged_tags = list(dict.fromkeys(
                [*(exp.get("tags") or []), "auto_summary", "provisional"]))
            upd = await experience_service.update_experience(kb_id, exp["id"], ExperienceUpdate(
                solution=body,
                key_lessons=self._build_lessons(docs, exps, round_no),
                metrics=merged_metrics,
                tags=merged_tags,
            ))
            if not upd.get("success"):
                return {"success": False, "error": upd.get("error", "update failed")}
            action, exp_id = "updated", exp["id"]
        else:
            created = await experience_service.create_experience(kb_id, ExperienceCreate(
                title=f"自动经验总结 · {kb_name}",
                scenario=f"auto-summary-{kb_id[:8]}",
                category="tip",
                problem=(
                    f"本经验由入库自动总结机制维护（每 {DEFAULT_INTERVAL} 篇文档触发一次更新），"
                    f"滚动覆盖知识库《{kb_name}》的全部文档知识与经验池快照。"
                ),
                solution=body,
                key_lessons=self._build_lessons(docs, exps, round_no),
                tags=["auto_summary", "provisional", "自动化"],
                severity="normal",
                related_docs=[d["path"] for d in docs[-5:]],
                auto_extracted=True,
                harness="auto_summary",
                confidence=0.7,
                metrics={
                    "auto_summary": True,
                    "last_summary_round": round_no,
                    "last_summary_at": _now(),
                    "last_summary_docs_total": len(docs),
                },
            ))
            if not created.get("success"):
                return {"success": False, "error": created.get("error", "create failed")}
            action, exp_id = "created", created["experience"]["id"]

        with self._lock:
            data = self._load()
            entry = self._entry(data, kb_id)
            entry["summary_exp_id"] = exp_id
            entry["trigger_count"] = round_no
            entry["last_trigger_at"] = _now()
            entry.setdefault("history", []).append({
                "round": round_no, "at": _now(), "action": action,
                "exp_id": exp_id, "docs_total": len(docs),
                "docs_new": len(docs_since), "manual": manual,
            })
            entry["history"] = entry["history"][-MAX_HISTORY:]
            entry["updated_at"] = _now()
            self._save(data)

        logger.info("KB auto-summary %s: round %d %s exp=%s docs=%d",
                    kb_id[:8], round_no, action, exp_id, len(docs))
        return {"success": True, "action": action, "round": round_no,
                "summary_exp_id": exp_id, "docs_total": len(docs),
                "docs_new_since_last": len(docs_since)}

    @staticmethod
    def _find_exp(exps: list[dict], exp_id: str) -> Optional[dict]:
        if not exp_id:
            return None
        return next((e for e in exps if e.get("id") == exp_id), None)

    # ── 总结内容生成（纯规则，确定性） ─────────────────────────

    def _build_summary_body(self, kb_name: str, docs: list[dict],
                            exps: list[dict], docs_since: list[dict],
                            round_no: int, manual: bool) -> str:
        lines: list[str] = []
        lines.append(f"### 知识库概况（第 {round_no} 轮总结"
                     f"{' · 手动触发' if manual else ''}，{_now()[:19]}）")
        lines.append(f"- 知识库：**{kb_name}**")
        lines.append(f"- 文档总数：{len(docs)} 篇")
        provisional = [e for e in exps if "provisional" in (e.get("tags") or [])]
        lines.append(f"- 经验池：{len(exps)} 条（其中 provisional 待抽检 {len(provisional)} 条）")
        lines.append("")

        lines.append(f"### 本轮新增文档（自上次总结以来 {len(docs_since)} 篇）")
        # docs_since 与全库清单按路径精确对齐（不能用排序尾部对齐：
        # 关闭期间入库的文档不计数，会造成尾部窗口错位）
        inv = {_normalize_path(d["path"]): d for d in docs}
        if docs_since:
            for d in docs_since:
                rec = inv.get(_normalize_path(d.get("path", "")))
                name = (rec or {}).get("name") or d.get("title") or d.get("path", "")
                desc = (rec or {}).get("description") or ""
                desc = f" — {desc[:60]}" if desc else ""
                lines.append(f"1. `{name}`{desc}")
        else:
            lines.append("（无新增记录）")
        lines.append("")

        lines.append("### 知识主题分布（按标题/描述词频聚合）")
        topics = self._topic_distribution(docs)
        if topics:
            for topic, items in topics[:8]:
                names = "、".join(d["name"].replace(".md", "") for d in items[:4])
                more = f" 等{len(items)}篇" if len(items) > 4 else ""
                lines.append(f"- **{topic}**：{len(items)} 篇（{names}{more}）")
        else:
            lines.append("（暂无文档）")
        lines.append("")

        lines.append("### 经验池快照")
        if exps:
            for e in exps[:10]:
                mark = " `[provisional]`" if "provisional" in (e.get("tags") or []) else ""
                lines.append(f"- {e.get('title', '')}（{e.get('category', '')}）{mark}")
            if len(exps) > 10:
                lines.append(f"- …共 {len(exps)} 条")
        else:
            lines.append("- 经验池为空：可运行经验提取（/extract）或冥想任务提炼经验")
        lines.append("")

        lines.append("### 维护建议")
        lines.extend(self._build_advice(docs, exps, provisional))
        return "\n".join(lines)

    @staticmethod
    def _build_lessons(docs: list[dict], exps: list[dict], round_no: int) -> list[str]:
        lessons = [f"第 {round_no} 轮总结时知识库共 {len(docs)} 篇文档、{len(exps)} 条经验"]
        topics = KbAutomationService._topic_distribution(docs)
        for topic, items in topics[:3]:
            lessons.append(f"知识主题「{topic}」已有 {len(items)} 篇文档支撑")
        provisional = [e for e in exps if "provisional" in (e.get("tags") or [])]
        if provisional:
            lessons.append(f"经验池有 {len(provisional)} 条 provisional 经验待人工抽检转正")
        return lessons[:5]

    @staticmethod
    def _build_advice(docs: list[dict], exps: list[dict], provisional: list[dict]) -> list[str]:
        advice = []
        if provisional:
            advice.append(f"- 有 {len(provisional)} 条 provisional 经验，建议人工抽检后移除标记转正")
        if not exps:
            advice.append("- 经验池为空，建议对已有文档运行一次经验提取（POST /api/v1/experience/{kb}/extract）")
        if len(docs) >= 50:
            advice.append("- 文档数量较多（≥50 篇），建议定期整理归档保持检索质量")
        if not docs:
            advice.append("- 知识库暂无文档，总结将随入库自动充实")
        if not advice:
            advice.append("- 当前状态良好：文档与经验池均衡，无需干预")
        return advice

    # CJK bigram + latin token 词频 → 主题聚合（确定性，无外部依赖）
    @staticmethod
    def _topic_distribution(docs: list[dict]) -> list[tuple[str, list[dict]]]:
        def tokens(text: str) -> list[str]:
            text = (text or "").lower()
            out = re.findall(r"[a-z][a-z0-9\-]{2,}", text)
            cjk = re.findall(r"[\u4e00-\u9fff]", text)
            out += ["".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)]
            return out

        freq: Counter = Counter()
        doc_tokens: list[tuple[dict, list[str]]] = []
        for d in docs:
            toks = tokens(d.get("name", "").replace(".md", "")) + tokens(d.get("description", ""))
            toks = [t for t in set(toks) if len(t) >= 2]
            doc_tokens.append((d, toks))
            freq.update(toks)
        # 主题词：出现在 ≥2 篇文档中，过滤纯数字/虚词/通用动词
        stop = {"the", "and", "for", "with", "文档", "知识", "总结", "md", "part",
                "采用", "使用", "基于", "通过", "进行", "以及", "相关", "影响",
                "要求", "需要", "适合", "时间", "系统", "方法", "测试", "验证",
                "控制", "设计", "结果", "过程", "工况"}
        topics = [(t, c) for t, c in freq.most_common(30)
                  if c >= 2 and t not in stop and not t.isdigit()]
        if not topics:
            return []
        assigned: dict[str, list[dict]] = {t: [] for t, _ in topics}
        covered: set[int] = set()
        for t, _ in topics:
            for i, (d, toks) in enumerate(doc_tokens):
                if i in covered or t not in toks:
                    continue
                assigned[t].append(d)
                covered.add(i)
        return [(t, items) for t, items in assigned.items() if items]


kb_automation_service = KbAutomationService()
