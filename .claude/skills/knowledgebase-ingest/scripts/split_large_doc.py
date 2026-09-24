#!/usr/bin/env python3
"""A2.5 structure-aware Markdown split gate.

The script is deliberately source-preserving: it scans logical Markdown units,
optionally validates an Agent boundary plan, materializes parts from contiguous
source spans, and never rewrites the body. A malformed plan is rejected and the
structural fallback is used with an explicit warning in the JSON result.

Usage:
  python split_large_doc.py parsed.md
  python split_large_doc.py parsed.md --agent-plan plan.json
  python split_large_doc.py parsed.md --dry-run --max-chars 30000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[3]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:
    from app.services.semantic_splitter import (  # type: ignore
        DEFAULT_MAX_CHARS,
        DEFAULT_OVERLAP_CHARS,
        clamp_max_chars,
        content_description,
        plan_split,
    )
except Exception as exc:  # pragma: no cover - only used in broken installations
    print(json.dumps({"success": False, "error": f"splitter_import_failed: {exc}"}, ensure_ascii=False))
    raise

CONFIG_MAX_CHARS_KEY = "max_chars"


def _parse_large_doc_section(text: str) -> dict | None:
    lines = text.splitlines()
    in_ingestion = False
    in_large_doc = False
    cfg: dict = {}
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        key, _, val = stripped.strip().partition(":")
        val = val.strip()
        if indent == 0:
            in_ingestion = key == "ingestion"
            in_large_doc = False
            continue
        if in_ingestion and indent == 2:
            in_large_doc = key == "large_doc"
            continue
        if in_ingestion and in_large_doc:
            if val.lower() in ("true", "false"):
                cfg[key] = val.lower() == "true"
            else:
                try:
                    cfg[key] = int(val)
                except ValueError:
                    try:
                        cfg[key] = float(val)
                    except ValueError:
                        cfg[key] = val.strip('"\'')
    return cfg or None


def _read_config(config_path: Path | None, source_path: Path) -> tuple[dict, str]:
    candidates: list[tuple[Path, str]] = []
    if config_path:
        candidates.append((config_path, "--config"))
    env_cfg = os.environ.get("RAG_KB_CONFIG")
    if env_cfg:
        candidates.append((Path(env_cfg), "RAG_KB_CONFIG"))
    # Prefer the input file's repository ancestry, then CWD. This fixes the
    # old behavior where a temp parse directory could silently select a wrong
    # max_chars value based on the caller's CWD.
    for base in [source_path.parent, *source_path.parent.parents, Path.cwd(), *Path.cwd().parents]:
        candidates.append((base / "config.yml", "ancestor"))
    defaults = {
        "auto_split": True,
        "max_chars": DEFAULT_MAX_CHARS,
        "overlap_chars": DEFAULT_OVERLAP_CHARS,
        "strategy": "agent_semantic",
        "target_utilization": 0.85,
        "allow_oversized_atomic_unit": True,
        "allow_hard_fallback": False,
    }
    seen: set[Path] = set()
    for path, source in candidates:
        path = path.resolve()
        if path in seen or not path.exists():
            continue
        seen.add(path)
        try:
            cfg = _parse_large_doc_section(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if cfg is not None:
            merged = dict(defaults)
            merged.update(cfg)
            return merged, f"{path} ({source})"
    return defaults, "defaults"


def _load_json(path: str | None) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _selftest() -> int:
    text = (
        "# Title\n\n"
        "## A\n\nfirst paragraph with enough content.\n\n"
        "```python\n# this is not a heading\nprint('x')\n```\n\n"
        "| key | value |\n| --- | --- |\n| a | b |\n\n"
        "## B\n\nsecond paragraph.\n"
    )
    result = plan_split(text, "title.md", {"max_chars": 80})
    assert result["source_sha256"]
    assert result["units"]
    assert all("# this is not a heading" not in u["heading_path"] for u in result["units"])
    assert result["parts"]
    print(json.dumps({"selftest": "pass", "parts": len(result["parts"]), "units": len(result["units"])}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="按逻辑结构拆分解析后的 Markdown 文档")
    ap.add_argument("input", nargs="?", help="解析产物 markdown 路径")
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--agent-plan", default=None, help="已由 Agent 生成的 JSON 边界计划")
    ap.add_argument("--keep-source", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.selftest:
        return _selftest()
    if not args.input:
        ap.error("缺少 input 路径（或使用 --selftest）")
    src = Path(args.input)
    if not src.exists() or not src.is_file():
        print(json.dumps({"success": False, "error": f"文件不存在: {src}"}, ensure_ascii=False))
        return 1
    try:
        content = src.read_text(encoding="utf-8")
        cfg, cfg_source = _read_config(Path(args.config) if args.config else None, src)
        if args.max_chars is not None:
            cfg[CONFIG_MAX_CHARS_KEY] = args.max_chars
        if args.agent_plan:
            cfg["agent_plan"] = _load_json(args.agent_plan)
        if not bool(cfg.get("auto_split", True)):
            result = plan_split(content, src.stem, cfg)
            result.update({"success": True, "source_file": str(src),
                           "max_chars_source": cfg_source, "auto_split_config": False,
                           "dry_run": bool(args.dry_run), "source_deleted": False})
            print(json.dumps(result, ensure_ascii=False))
            return 0
        cfg["auto_split"] = True
        result = plan_split(content, src.stem, cfg)
        result.update({
            "success": True,
            "source_file": str(src),
            "max_chars_source": cfg_source,
            "auto_split_config": bool(cfg.get("auto_split", True)),
            "dry_run": bool(args.dry_run),
        })
        parts = result.get("parts") or []
        split = bool(result.get("split"))
        if not split:
            result["parts"] = [{
                "file": str(src), "title": src.stem,
                "chars": len(content),
                "description": content_description(content),
                **p,
            } for p in parts[:1]]
            result["source_deleted"] = False
            result["note"] = "未超过结构化拆分门槛，无需拆分"
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.dry_run:
            result["parts"] = [{"file": None, **p} for p in parts]
            result["source_deleted"] = False
            print(json.dumps(result, ensure_ascii=False))
            return 0
        out_dir = Path(args.out_dir) if args.out_dir else src.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        materialized: list[dict] = []
        stem = src.stem
        for p in parts:
            name = f"{stem} (part {p['part_index']} of {p['part_count']}).md"
            path = out_dir / name
            path.write_text(str(p["content"]), encoding="utf-8")
            materialized.append({"file": str(path), **p})
        result["parts"] = materialized
        if args.keep_source:
            result["source_deleted"] = False
        else:
            try:
                src.unlink()
                result["source_deleted"] = True
            except OSError as exc:
                result["source_deleted"] = False
                result["warning"] = f"删除原文失败（请手动处理）: {exc}"
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"success": False, "source_file": str(src), "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
