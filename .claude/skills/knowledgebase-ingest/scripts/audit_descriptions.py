#!/usr/bin/env python3
"""Description audit for the ingest skill.

Scans a catalog dump (kb_list + kb_get_documents lightweight, saved as JSON) and
reports description defects that break level-by-level retrieval:

  empty / short (<40 chars)          — nothing for the description scan to match
  broken_part_prefix                 — '【?/?·' template placeholder was never filled
                                       (measured 2026-09-25: 156/322 docs) while the
                                       doc_path carries the real '(part k of N)'
  part_anchor_missing                — split doc whose description has no '——' section
                                       anchor tail and no part prefix at all
  boilerplate                        — identical description repeated on >=3 docs of a KB
  degenerate_range                   — inverted roman/arabic span claims (XV–I)

Pure offline tool: no MCP, no model. Exit 0 always; the JSON verdict is the result.
`--apply` is NOT here on purpose: fixes live in repair_part_prefixes.py (MCP write).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

DEFAULT_MIN_CHARS = 40
_PART_IN_PATH = re.compile(r"\(part (\d+) of (\d+)\)")
_PREFIX = re.compile(r"【([^】]*)·")
_DEGENERATE = re.compile(r"\b([IVXLCDM]+|\d+)\s*[–-]\s*\1\b", re.I)
_ANCHOR = "——"


def _issues_for(desc: str, doc_path: str, min_chars: int) -> list[str]:
    issues: list[str] = []
    text = str(desc or "").strip()
    if not text:
        return ["empty"]
    if len(text) < min_chars:
        issues.append("short")
    if "?/?" in text:
        issues.append("broken_part_prefix")
    if _DEGENERATE.search(text):
        issues.append("degenerate_range")
    if _PART_IN_PATH.search(str(doc_path or "")):
        has_prefix = bool(_PREFIX.search(text))
        has_anchor = _ANCHOR in text
        if not has_prefix and not has_anchor:
            issues.append("part_anchor_missing")
    return issues


def suggested_prefix_fix(desc: str, doc_path: str) -> str | None:
    """Fill '【?/?·' from the (part k of N) in the path; None when not fixable."""
    text = str(desc or "")
    m = _PART_IN_PATH.search(str(doc_path or ""))
    if not m or "?/?" not in text:
        return None
    return _PREFIX.sub(f"【{m.group(1)}/{m.group(2)}·", text, count=1)


def audit_catalog(catalog: Mapping[str, Any] | list, min_chars: int = DEFAULT_MIN_CHARS) -> dict[str, Any]:
    if isinstance(catalog, list):
        kbs = catalog
    else:
        kbs = catalog.get("catalog") if isinstance(catalog.get("catalog"), list) else catalog.get("kbs")
    if kbs is None and isinstance(catalog, list):
        kbs = catalog
    rows: list[dict[str, Any]] = []
    doc_total = 0
    for kb in kbs or []:
        kb_id = kb.get("kb_id") or kb.get("name")
        seen: Counter = Counter()
        for d in kb.get("docs") or []:
            desc = str(d.get("description") or "").strip()
            if desc:
                seen[desc] += 1
        for d in kb.get("docs") or []:
            doc_total += 1
            desc = str(d.get("description") or "").strip()
            path = str(d.get("doc_path") or "")
            issues = _issues_for(desc, path, min_chars)
            if desc and seen[desc] >= 3:
                issues.append("boilerplate")
            if not issues:
                continue
            row = {"kb_id": kb_id, "kb_name": kb.get("name"), "doc_path": path,
                   "doc_id": d.get("doc_id") or d.get("file_id"), "issues": issues,
                   "description": desc}
            if "broken_part_prefix" in issues:
                fixed = suggested_prefix_fix(desc, path)
                if fixed:
                    row["suggested_description"] = fixed
            rows.append(row)
    by_issue = Counter(issue for r in rows for issue in r["issues"])
    return {"doc_total": doc_total, "flagged": len(rows), "by_issue": dict(by_issue),
            "auto_fixable": sum(1 for r in rows if "suggested_description" in r),
            "docs": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit catalog descriptions for retrieval-breaking defects")
    parser.add_argument("--input", required=True, help="catalog JSON (kb_list + kb_get_documents dump, list or {catalog|kbs: [...]})")
    parser.add_argument("--output", help="write verdict JSON here instead of stdout")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS)
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(Path(args.input).read_text(encoding="utf-8"))
        verdict = audit_catalog(catalog, args.min_chars)
        rendered = json.dumps(verdict, ensure_ascii=False, indent=1)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)[:240]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
