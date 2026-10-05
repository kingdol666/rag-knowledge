#!/usr/bin/env python3
"""Repair broken '【?/?·' part prefixes in document descriptions.

The ingest A3c description template occasionally failed to fill the part index,
leaving a literal '【?/?·' prefix while the doc_path carries the real
'(part k of N)'. This script rewrites only that prefix from the path —
deterministic, no LLM — and pushes it with kb_doc_update_meta.

Read-only by default (--dry-run); pass --apply to write. Use --limit to roll out
in batches. A description that changed since the catalog dump is skipped
(stale_row guard) unless --force is given.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from audit_descriptions import audit_catalog, suggested_prefix_fix  # noqa: E402

REPO = SCRIPT_DIR.parents[3]


def _mcp_class():
    lib_dir = REPO / "benchmark-suite" / "scripts"
    if not lib_dir.is_dir():
        raise RuntimeError(f"MCP client library not found at {lib_dir}")
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))
    from lib import McpClient  # noqa: PLC0415
    return McpClient


def build_plan(catalog: Mapping[str, Any], min_chars: int = 40) -> list[dict[str, Any]]:
    """One plan row per auto-fixable broken_part_prefix doc."""
    verdict = audit_catalog(catalog, min_chars)
    plan = []
    for row in verdict["docs"]:
        if "suggested_description" not in row:
            continue
        plan.append({"kb_id": row["kb_id"], "doc_path": row["doc_path"],
                     "doc_id": row.get("doc_id"), "old_description": row["description"],
                     "new_description": row["suggested_description"]})
    return plan


def apply_plan(plan: list[dict[str, Any]], *, limit: int, force: bool) -> dict[str, Any]:
    mc = _mcp_class()()
    applied, skipped, errors = [], [], []
    try:
        live_desc: dict[tuple[str, str], str | None] = {}
        for row in plan:  # one kb_get_documents per affected KB, not per doc
            key = (str(row["kb_id"]), row["doc_path"])
            if key not in live_desc:
                try:
                    detail = (mc.call("kb_get_documents", {"lightweight": True,
                                                           "kb_id": row["kb_id"]},
                                      timeout=180).get("catalog") or [])
                    live_desc.update({(str(row["kb_id"]), str(e.get("doc_path"))): e.get("description")
                                      for e in detail})
                except Exception as exc:  # noqa: BLE001
                    errors.append({"doc_path": row["doc_path"],
                                   "error": f"catalog_lookup:{type(exc).__name__}:{str(exc)[:120]}"})
                    live_desc[key] = None
        for row in plan:
            if len(applied) >= limit:
                skipped.append({"doc_path": row["doc_path"], "reason": "limit_reached"})
                continue
            meta = live_desc.get((str(row["kb_id"]), row["doc_path"]))
            try:
                if not force and meta is not None and str(meta).strip() != str(row["old_description"]).strip():
                    skipped.append({"doc_path": row["doc_path"], "reason": "stale_row"})
                    continue
                mc.call("kb_doc_update_meta",
                        {"kb_id": row["kb_id"], "doc_path": row["doc_path"],
                         "description": row["new_description"]}, timeout=120)
                applied.append({"doc_path": row["doc_path"]})
                time.sleep(0.1)
            except Exception as exc:  # noqa: BLE001 — keep repairing the rest
                errors.append({"doc_path": row["doc_path"],
                               "error": f"{type(exc).__name__}:{str(exc)[:160]}"})
    finally:
        mc.close()
    return {"applied": applied, "skipped": skipped, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repair 【?/?· description prefixes from doc_path part numbers")
    parser.add_argument("--input", required=True, help="catalog JSON dump")
    parser.add_argument("--apply", action="store_true", help="write via kb_doc_update_meta (default: dry-run plan only)")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--force", action="store_true", help="apply even if the live description differs from the dump")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(Path(args.input).read_text(encoding="utf-8"))
        plan = build_plan(catalog)
        result: dict[str, Any] = {"plan_count": len(plan), "mode": "dry-run" if not args.apply else "apply"}
        if args.apply:
            result.update(apply_plan(plan, limit=args.limit, force=args.force))
        else:
            result["plan"] = plan
        rendered = json.dumps(result, ensure_ascii=False, indent=1)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered[:4000])
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}:{str(exc)[:240]}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
