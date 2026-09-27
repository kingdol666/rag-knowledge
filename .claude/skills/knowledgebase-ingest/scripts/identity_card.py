#!/usr/bin/env python3
"""Identity-Card Description (ICD) schema for knowledgebase-ingest A3c.

Motivation (measured 2026-09-26): the librarian funnel's precision ceiling is
description quality. A multi-work KB with vague descriptions forces L4 to read
everything; a work-anchored, event-specific description lets L2 filter other
works out and locate the exact part. This module renders and validates the
seven-dimension identity card:

  【门类】作品/主题名（原文/别名）· 第 k/N 部分 · 章节/小节范围
  事件: 1-3 concrete facts (the retrieval hooks)
  实体: 3-8 named entities
  可答: question types; 不含: explicit negatives (only when adjacency confusable)

Dimensions (validated independently):
  D1 genre       controlled vocabulary
  D2 identity    canonical name + original/alias, bilingual anchors mandatory
  D3 position    part k/N + non-degenerate range
  D4 events      concrete facts, no boilerplate, front-loaded
  D5 entities    >= 2 named entities
  D6 scope       answerable question types
  D7 negative    optional explicit exclusion
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

GENRES = {"小说", "论文", "手册", "规范", "经验", "纪要", "评论", "数据集", "其他"}
_PART_RE = re.compile(r"第\s*(\d+)\s*/\s*(\d+)\s*部分")
# The splitter emits `【Part i/N · …】` and the web helper `[part i/N …]` —
# all three part-marker dialects must pass D3, or every standard split fails
# validation for formatting alone.
_PART_EN_RE = re.compile(r"[\[【]?part\s+(\d+)\s*/\s*(\d+)", re.I)
_RANGE_RE = re.compile(r"(Chapter|Ch\.?|章|章节|§|Section)", re.I)
_RANGE_TOKEN_RE = re.compile(r"\b((?:[IVXLCDM]+|\d+))\s*[–—-]\s*((?:[IVXLCDM]+|\d+))\b")
_ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _range_token_value(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    upper = token.upper()
    total = 0
    for i, ch in enumerate(upper):
        value = _ROMAN_VAL.get(ch)
        if value is None:
            return None
        if i + 1 < len(upper) and _ROMAN_VAL.get(upper[i + 1], 0) > value:
            total -= value
        else:
            total += value
    return total


def _has_degenerate_range(text: str) -> bool:
    """True for equal or inverted spans (XV–XV, 9–3, XV–I)."""
    for left, right in _RANGE_TOKEN_RE.findall(text):
        a, b = _range_token_value(left), _range_token_value(right)
        if a is not None and b is not None and a >= b:
            return True
    return False


def render(meta: Mapping[str, Any]) -> str:
    """Render an ICD description from structured metadata. Front-loads the most
    selective terms (identity first) — matching is term-overlap based and
    renderings must survive description truncation."""
    genre = str(meta.get("genre") or "其他").strip()
    identity = str(meta.get("identity") or "").strip()          # "傲慢与偏见 Pride and Prejudice"
    position = str(meta.get("position") or "").strip()          # "第 8/26 部分 · Chapter 19"
    events = meta.get("events") or []
    entities = meta.get("entities") or []
    scope = str(meta.get("scope") or "").strip()
    negative = str(meta.get("negative") or "").strip()
    if isinstance(events, str):
        events = [events]
    if isinstance(entities, str):
        entities = [entities]
    head = f"【{genre}】{identity}"
    if position:
        head += f" · {position}"
    parts = [head]
    if events:
        parts.append("事件: " + "; ".join(str(e) for e in events[:3]))
    if entities:
        parts.append("实体: " + "、".join(str(e) for e in entities[:8]))
    tail = []
    if scope:
        tail.append(f"可答: {scope}")
    if negative:
        tail.append(f"不含: {negative}")
    if tail:
        parts.append("; ".join(tail))
    return "".join(p + ("。" if i < len(parts) - 1 else "") for i, p in enumerate(parts))


def validate(description: str, *, is_part: bool = True) -> dict[str, Any]:
    """Score a description against the ICD dimensions. Returns per-dimension
    verdicts, a 0-7 score, and actionable defects."""
    text = str(description or "").strip()
    checks: dict[str, bool] = {}
    defects: list[str] = []

    genre = re.search(r"【([^】]+)】", text)
    checks["D1_genre"] = bool(genre and genre.group(1).strip() in GENRES)
    if not checks["D1_genre"]:
        defects.append("D1: genre missing or outside controlled vocabulary")

    body = re.sub(r"^【[^】]+】", "", text)
    checks["D2_identity"] = bool(re.search(r"[\u4e00-\u9fff]{2,}.*[A-Za-z]{2,}|[A-Za-z]{2,}.*[\u4e00-\u9fff]{2,}", body[:60]))
    if not checks["D2_identity"]:
        defects.append("D2: no bilingual identity anchor in the first 60 chars")

    part_m = _PART_RE.search(text) or _PART_EN_RE.search(text)
    checks["D3_position"] = bool(part_m or (not is_part))
    if is_part and not part_m:
        defects.append("D3: split part lacks 第 k/N 部分 marker")
    if part_m and _has_degenerate_range(text):
        checks["D3_position"] = False
        defects.append("D3: degenerate range (single-point or inverted)")

    ev = re.search(r"事件[:：]\s*(.+?)(?:实体[:：]|可答[:：]|不含[:：]|$)", text)
    has_concrete = bool(ev) and len(ev.group(1).strip()) >= 8
    checks["D4_events"] = has_concrete
    if not has_concrete:
        defects.append("D4: no concrete event fingerprint (>=8 chars after 事件:)")

    ent = re.search(r"实体[:：]\s*([^;；。]+)", text)
    n_ent = len([e for e in re.split(r"[、,，/]", ent.group(1)) if e.strip()]) if ent else 0
    checks["D5_entities"] = n_ent >= 2
    if not checks["D5_entities"]:
        defects.append("D5: fewer than 2 named entities")

    checks["D6_scope"] = bool(re.search(r"可答[:：]", text))
    if not checks["D6_scope"]:
        defects.append("D6: no 可答 (answerable-scope) clause")

    checks["D7_negative"] = ("不含" in text) or True  # optional dimension: absence is not a defect
    score = sum(1 for k in ("D1_genre", "D2_identity", "D3_position",
                            "D4_events", "D5_entities", "D6_scope") if checks[k])
    over = len(text) > 220
    if over:
        defects.append(f"length {len(text)} > 220")
    return {"score": score, "max": 6, "checks": checks,
            "defects": defects, "length": len(text), "over_220": over,
            "grade": "icd-ok" if score == 6 and not over else
                     ("icd-partial" if score >= 4 else "icd-poor")}


def audit_catalog(catalog: Mapping[str, Any] | list) -> dict[str, Any]:
    """Audit a catalog dump ({"catalog":[{kb_id, docs:[...]}]}) for ICD compliance."""
    kbs = catalog if isinstance(catalog, list) else (
        catalog.get("catalog") if isinstance(catalog.get("catalog"), list) else catalog.get("kbs") or [])
    rows, total = [], 0
    for kb in kbs or []:
        kb_id = kb.get("kb_id") or kb.get("name")
        for d in kb.get("docs") or []:
            total += 1
            v = validate(str(d.get("description") or ""))
            rows.append({"kb_id": kb_id, "doc_path": d.get("doc_path"),
                         "grade": v["grade"], "score": v["score"], "defects": v["defects"]})
    grades = {"icd-ok": 0, "icd-partial": 0, "icd-poor": 0}
    for r in rows:
        grades[r["grade"]] += 1
    return {"doc_total": total, "grades": grades, "docs": rows}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Identity-Card Description (ICD) build/validate/audit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render an ICD from a JSON meta file")
    b.add_argument("meta")
    v = sub.add_parser("validate", help="validate one description string (arg or stdin)")
    v.add_argument("description", nargs="?")
    a = sub.add_parser("audit", help="audit a catalog dump for ICD compliance")
    a.add_argument("--input", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        print(render(meta))
        return 0
    if args.cmd == "validate":
        desc = args.description or sys.stdin.read().strip()
        verdict = validate(desc)
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        # Fail-closed for scripting: a description that has not passed the ICD
        # gate must not be saved (SKILL.md A3c acceptance is 6/6, icd-ok).
        return 0 if verdict["grade"] == "icd-ok" else 2
    catalog = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(json.dumps(audit_catalog(catalog), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
