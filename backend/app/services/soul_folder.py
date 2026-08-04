"""SOUL 文件夹结构解析服务 — 将 SOUL KB 磁盘目录解析为分区数据结构供前端展示。

解析 soul-<name>/ 下的全部子目录与文件，归入 11 个语义分区：
  constitution / config / memories / cognition-drafts / cognition /
  training / questions / reports / audit / calibration / checkpoints

每个分区返回 description + items 列表；
md/json/jsonl/yaml 格式文件解析为结构化内容。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.services.soul_config import resolve_soul_kb_path, soul_kb_dir

logger = logging.getLogger(__name__)

# ── 分区定义：key → (显示名, 用途描述) ──────────────────────────────────────

_SECTION_DEFS: dict[str, tuple[str, str]] = {
    "constitution": (
        "宪法层",
        "人格定义核心文档：soul-definition / thinking-style / values / memory-conventions",
    ),
    "config": (
        "配置",
        "soul-config.yml — kb_scope / domain_labels / supported_task_types / route_weight",
    ),
    "memories": (
        "训练记忆",
        "memories/*.md — 已批准的正式记忆（含 frontmatter: question/scores/status/evidence）",
    ),
    "cognition-drafts": (
        "认知草稿",
        "cognition-drafts/*.md — RL 认知草稿（pending/approved/rejected）",
    ),
    "cognition": (
        "认知档案",
        "cognition/*.md — 认知档案（设计意图 & rollback 保护目录）",
    ),
    "training": (
        "训练数据导出",
        "training/export-*.jsonl — 训练数据导出文件",
    ),
    "questions": (
        "学习缺口",
        "questions/gaps.md + learned-hashes.json — 学习缺口与已学文档哈希",
    ),
    "reports": (
        "报告",
        "reports/ — profile-summary.md / drift-*.md / reward-history.jsonl",
    ),
    "audit": (
        "审计日志",
        "audit/approval-log.jsonl + cost-log.jsonl — 审批与成本审计记录",
    ),
    "calibration": (
        "校准集",
        "calibration/calibration.jsonl — 校准评测数据（≥20 条方可 calibrate）",
    ),
    "checkpoints": (
        "检查点",
        "checkpoints/ — 检查点快照（JSON）",
    ),
}

# ── 宪法文档文件名 ─────────────────────────────────────────────────────────

_CONSTITUTION_FILES = [
    "soul-definition.md",
    "thinking-style.md",
    "values.md",
    "memory-conventions.md",
]

# ── 内部辅助 ───────────────────────────────────────────────────────────────


def _is_jsonl(name: str) -> bool:
    return name.endswith(".jsonl")


def _is_json(name: str) -> bool:
    return name.endswith(".json") and not name.endswith(".jsonl")


def _is_yaml(name: str) -> bool:
    return name.endswith(".yml") or name.endswith(".yaml")


def _is_md(name: str) -> bool:
    return name.endswith(".md")


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """解析 Markdown 文件的 YAML frontmatter。"""
    if not content.startswith("---\n"):
        return {}, content
    parts = content.split("\n---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1]
    body = parts[2].strip()
    try:
        fm: dict[str, Any] = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, body
    return fm, body


def _read_content(path: Path) -> tuple[str | None, float]:
    """读取文件内容文本；返回 (content_str, mtime_epoch)。不存在返回 (None, 0)。"""
    if not path.exists() or not path.is_file():
        return None, 0.0
    mtime = path.stat().st_mtime
    try:
        return path.read_text(encoding="utf-8"), mtime
    except Exception:
        return None, mtime


def _make_item(
    name: str,
    file_type: str,
    size: int,
    mtime: float,
    content: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": name,
        "type": file_type,
        "size": size,
        "mtime": mtime,
    }
    if content is not None:
        item["content"] = content
    if meta:
        item["meta"] = meta
    return item


def _parse_jsonl_to_list(text: str) -> list[dict[str, Any]]:
    """解析 JSONL 文本为 dict 列表。"""
    records: list[dict[str, Any]] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"raw": line})
    return records


def _read_and_parse(
    path: Path, file_type: str
) -> tuple[str | None, float, dict[str, Any] | None]:
    """读取文件并解析，返回 (raw_text, mtime, parsed_or_none)。"""
    raw, mtime = _read_content(path)
    if raw is None:
        return None, mtime, None

    parsed = None
    if file_type == "jsonl":
        records = _parse_jsonl_to_list(raw)
        parsed = {"parsed": records, "raw": raw}
    elif file_type == "json":
        try:
            parsed = {"parsed": json.loads(raw), "raw": raw}
        except json.JSONDecodeError:
            parsed = {"parsed": None, "raw": raw, "parse_error": True}
    elif file_type == "yaml":
        try:
            parsed = {"parsed": yaml.safe_load(raw), "raw": raw}
        except yaml.YAMLError:
            parsed = {"parsed": None, "raw": raw, "parse_error": True}
    return raw, mtime, parsed


# ── 分区处理函数 ───────────────────────────────────────────────────────────


def _scan_constitution(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描根目录下 4 份宪法文档。"""
    items: list[dict[str, Any]] = []
    for fname in _CONSTITUTION_FILES:
        fp = kb_dir / fname
        raw, mtime = _read_content(fp)
        if raw is not None:
            items.append(
                _make_item(fname, "md", len(raw.encode("utf-8")), mtime, content=raw)
            )
        else:
            # 文件缺失也列出，便于前端展示缺失状态
            items.append(_make_item(fname, "md", 0, 0.0, content=None))
    return items


def _scan_config(kb_dir: Path) -> list[dict[str, Any]]:
    """解析 soul-config.yml。"""
    fp = kb_dir / "soul-config.yml"
    raw, mtime, parsed = _read_and_parse(fp, "yaml")
    if raw is None:
        return [_make_item("soul-config.yml", "yaml", 0, 0.0)]
    item = _make_item(
        "soul-config.yml",
        "yaml",
        len(raw.encode("utf-8")),
        mtime,
        content=raw,
    )
    if parsed:
        item["meta"] = parsed
    return [item]


def _scan_memories(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 memories/*.md，解析 frontmatter。"""
    items: list[dict[str, Any]] = []
    mem_dir = kb_dir / "memories"
    if not mem_dir.exists() or not mem_dir.is_dir():
        return items

    for fp in sorted(mem_dir.glob("*.md")):
        raw, mtime = _read_content(fp)
        if raw is None:
            continue
        fm, body = _parse_frontmatter(raw)
        item = _make_item(
            fp.name,
            "md",
            len(raw.encode("utf-8")),
            mtime,
            content=raw,
        )
        # 提取关键 frontmatter 字段到 meta
        meta: dict[str, Any] = {
            "question": fm.get("question", ""),
            "status": fm.get("status", "unknown"),
            "scores": fm.get("scores", {}),
            "pas_score": fm.get("pas_score", None),
            "evidence_paths": fm.get("evidence_paths", []),
        }
        item["meta"] = meta
        items.append(item)
    return items


def _scan_cognition_drafts(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 cognition-drafts/*.md。"""
    return _scan_simple_md_dir(kb_dir / "cognition-drafts")


def _scan_cognition(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 cognition/*.md。"""
    return _scan_simple_md_dir(kb_dir / "cognition")


def _scan_simple_md_dir(dir_path: Path) -> list[dict[str, Any]]:
    """通用 .md 目录扫描（不含 frontmatter 解析）。"""
    items: list[dict[str, Any]] = []
    if not dir_path.exists() or not dir_path.is_dir():
        return items
    for fp in sorted(dir_path.glob("*.md")):
        raw, mtime = _read_content(fp)
        if raw is None:
            continue
        items.append(
            _make_item(fp.name, "md", len(raw.encode("utf-8")), mtime, content=raw)
        )
    return items


def _scan_training(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 training/export-*.jsonl。"""
    items: list[dict[str, Any]] = []
    train_dir = kb_dir / "training"
    if not train_dir.exists() or not train_dir.is_dir():
        return items
    for fp in sorted(train_dir.glob("*.jsonl")):
        raw, mtime, parsed = _read_and_parse(fp, "jsonl")
        if raw is None:
            continue
        item = _make_item(
            fp.name,
            "jsonl",
            len(raw.encode("utf-8")),
            mtime,
            content=raw,
        )
        if parsed:
            item["meta"] = parsed
        items.append(item)
    return items


def _scan_questions(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 questions/gaps.md + questions/learned-hashes.json。"""
    items: list[dict[str, Any]] = []
    q_dir = kb_dir / "questions"

    # gaps.md
    gaps_path = q_dir / "gaps.md"
    raw, mtime = _read_content(gaps_path)
    if raw is not None:
        items.append(
            _make_item("gaps.md", "md", len(raw.encode("utf-8")), mtime, content=raw)
        )
    else:
        items.append(_make_item("gaps.md", "md", 0, 0.0))

    # learned-hashes.json
    lh_path = q_dir / "learned-hashes.json"
    raw, mtime, parsed = _read_and_parse(lh_path, "json")
    if raw is not None:
        item = _make_item(
            "learned-hashes.json",
            "json",
            len(raw.encode("utf-8")),
            mtime,
            content=raw,
        )
        if parsed:
            item["meta"] = parsed
        items.append(item)
    else:
        items.append(_make_item("learned-hashes.json", "json", 0, 0.0))

    return items


def _scan_reports(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 reports/ 目录 (md + jsonl)。"""
    items: list[dict[str, Any]] = []
    rp_dir = kb_dir / "reports"
    if not rp_dir.exists() or not rp_dir.is_dir():
        return items

    for fp in sorted(rp_dir.iterdir()):
        if not fp.is_file():
            continue
        raw, mtime = _read_content(fp)
        if raw is None:
            continue

        if fp.suffix == ".jsonl":
            ft = "jsonl"
            _, _, parsed = _read_and_parse(fp, "jsonl")
        elif fp.suffix == ".json":
            ft = "json"
            _, _, parsed = _read_and_parse(fp, "json")
        elif fp.suffix in (".md", ".txt"):
            ft = "md"
            parsed = None
        else:
            ft = "text"
            parsed = None

        item = _make_item(fp.name, ft, len(raw.encode("utf-8")), mtime, content=raw)
        if parsed:
            item["meta"] = parsed
        items.append(item)
    return items


def _scan_audit(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 audit/*.jsonl。"""
    items: list[dict[str, Any]] = []
    audit_dir = kb_dir / "audit"
    if not audit_dir.exists() or not audit_dir.is_dir():
        return items
    for fp in sorted(audit_dir.glob("*.jsonl")):
        raw, mtime, parsed = _read_and_parse(fp, "jsonl")
        if raw is None:
            continue
        item = _make_item(
            fp.name,
            "jsonl",
            len(raw.encode("utf-8")),
            mtime,
            content=raw,
        )
        if parsed:
            item["meta"] = parsed
        items.append(item)
    return items


def _scan_calibration(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 calibration/calibration.jsonl。"""
    items: list[dict[str, Any]] = []
    cal_dir = kb_dir / "calibration"
    if not cal_dir.exists() or not cal_dir.is_dir():
        return items
    for fp in sorted(cal_dir.glob("*.jsonl")):
        raw, mtime, parsed = _read_and_parse(fp, "jsonl")
        if raw is None:
            continue
        item = _make_item(
            fp.name,
            "jsonl",
            len(raw.encode("utf-8")),
            mtime,
            content=raw,
        )
        if parsed:
            item["meta"] = parsed
        items.append(item)
    return items


def _scan_checkpoints(kb_dir: Path) -> list[dict[str, Any]]:
    """扫描 checkpoints/ 目录 (JSON 快照)。"""
    items: list[dict[str, Any]] = []
    cp_dir = kb_dir / "checkpoints"
    if not cp_dir.exists() or not cp_dir.is_dir():
        return items
    for fp in sorted(cp_dir.iterdir()):
        if not fp.is_file():
            continue
        raw, mtime = _read_content(fp)
        if raw is None:
            continue
        if fp.suffix in (".json", ".jsonl"):
            _, _, parsed = _read_and_parse(fp, "json" if fp.suffix == ".json" else "jsonl")
            item = _make_item(
                fp.name,
                fp.suffix.lstrip("."),
                len(raw.encode("utf-8")),
                mtime,
                content=raw,
            )
            if parsed:
                item["meta"] = parsed
            items.append(item)
        else:
            items.append(
                _make_item(fp.name, "text", len(raw.encode("utf-8")), mtime)
            )
    return items


# ── 分区扫描映射 ────────────────────────────────────────────────────────────

_SECTION_SCANNERS: dict[str, Any] = {
    "constitution": _scan_constitution,
    "config": _scan_config,
    "memories": _scan_memories,
    "cognition-drafts": _scan_cognition_drafts,
    "cognition": _scan_cognition,
    "training": _scan_training,
    "questions": _scan_questions,
    "reports": _scan_reports,
    "audit": _scan_audit,
    "calibration": _scan_calibration,
    "checkpoints": _scan_checkpoints,
}


# ── 公开 API ────────────────────────────────────────────────────────────────


def read_soul_folder(soul_kb_id: str) -> dict[str, Any]:
    """解析 SOUL KB 磁盘目录为分区结构。

    Args:
        soul_kb_id: SOUL 知识库 ID（路径名或 UUID）。

    Returns:
        ``{"success": True, "structure": {"sections": [...]}}``
        每个 section: ``{key, name, description, items: [{name, type, size, mtime, content?, meta?}]}``
    """
    # 解析路径
    resolved = resolve_soul_kb_path(soul_kb_id)
    if not resolved:
        return {"success": False, "error": "soul_kb_not_found"}

    kb_dir = soul_kb_dir(soul_kb_id)
    if not kb_dir.exists():
        return {"success": False, "error": "soul_dir_not_found"}

    # 确保子目录存在（幂等）
    from app.services.soul_config import ensure_soul_dirs
    ensure_soul_dirs(soul_kb_id)

    sections: list[dict[str, Any]] = []

    for key, (display_name, description) in _SECTION_DEFS.items():
        scanner = _SECTION_SCANNERS.get(key)
        items: list[dict[str, Any]] = []
        if scanner:
            items = scanner(kb_dir)

        sections.append({
            "key": key,
            "name": display_name,
            "description": description,
            "entries": items,
        })

    return {
        "success": True,
        "structure": {
            "sections": sections,
            "soul_kb_id": soul_kb_id,
            "resolved_path": resolved,
        },
    }