#!/usr/bin/env python3
"""Fix — 8 篇论文的 oversized part 被后端 auto_split 二次拆分, 整体重做.

根因: A2.5 拆分门禁以 max_chars=30000 拆分, 但部分 part 的表头/换行归一化使
kb_doc_create 收到的内容仍越过后端 30000 上限, 触发后端 auto_split 二次拆分,
产生 "xxx (part 1 of 6) (part 1 of 2).md" 嵌套命名(共 18 docs / 8 papers)。
修复: 受影响论文整体重做 — 重解析(同 content-hash 缓存, 快) → --max-chars 28500
重拆(表头余量) → kb_doc_delete 本篇旧文档 → kb_doc_create 重建(两层描述) →
标签 → 受影响 KB 批量索引 force + 图谱 force 重建并等待完成。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import BACKEND, McpClient, http_post  # noqa: E402
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "ing98", SUITE / "scripts" / "98_ingest_round2_phase1.py")
_ing98 = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_ing98)
poll_parse = _ing98.poll_parse
_spec99 = _ilu.spec_from_file_location(
    "ing99", SUITE / "scripts" / "99_ingest_round2_phase2.py")
_ing99 = _ilu.module_from_spec(_spec99)
_spec99.loader.exec_module(_ing99)
compose_part_desc = _ing99.compose_part_desc

PAPERS = SUITE / "data" / "papers"
SPLIT_SCRIPT = Path.home() / ".zcode" / "skills" / "knowledgebase-ingest" \
    / "scripts" / "split_large_doc.py"
SAFE_MAX_CHARS = 28500
AFFECTED = [
    "2304.12442", "2602.10156", "2508.18304", "2412.15058",
    "2402.07064", "1405.4980", "2607.03098", "1909.07748",
]


def main() -> int:
    manifest = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    clf = json.loads((PAPERS / "classification_r2.json").read_text(encoding="utf-8"))
    by_id = {p["arxiv_id"].split("v")[0]: p for p in manifest["papers"]}
    mc = McpClient()

    redone = []
    for aid in AFFECTED:
        p = by_id[aid]
        j = clf["assign"][aid]
        kb, tags, desc = j["kb"], j["tags"], j["desc"]
        pdf = PAPERS / p["pdf"]
        slug_frag = f"__{aid.replace('/', '-')}__"
        # 1) 删除本篇旧文档(含嵌套命名)
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        old = [d for d in docs if slug_frag in str(d.get("name", ""))]
        for d in old:
            path = d.get("path") or f"{kb}/{d.get('name')}"
            mc.call("kb_doc_delete", {"kb_id": kb, "doc_path": path}, timeout=120)
        print(f"[delete] {aid}: removed {len(old)} old docs from {kb}", flush=True)

        # 2) 重解析(缓存命中则快) + 3) 28500 重拆
        task = mc.call("parse_doc", {"file_path": str(pdf)}, timeout=300)
        tid = (task or {}).get("task_id") or ""
        if not tid:
            raise RuntimeError(f"parse_doc no task_id for {aid}")
        pr = poll_parse(mc, tid)
        result = (pr or {}).get("result") or {}
        md_path = str(result.get("markdown_path") or "")
        markdown = Path(md_path).read_text(encoding="utf-8",
                                            errors="replace") if md_path else ""
        r = subprocess.run(
            [sys.executable, str(SPLIT_SCRIPT), md_path,
             "--max-chars", str(SAFE_MAX_CHARS)],
            capture_output=True, text=True, encoding="utf-8", timeout=300,
            cwd=str(SUITE.parent))
        line = next((l for l in (r.stdout or "").splitlines()
                     if l.strip().startswith("{")), "")
        split = json.loads(line) if line else {}
        if not split.get("success"):
            raise RuntimeError(f"re-split failed for {aid}: {r.stdout[-200:]}")
        parts = [Path(x["file"]) for x in split.get("parts", [])]
        # 4) 重建 + 5) 标签
        created = []
        for idx, fp in enumerate(parts, 1):
            content = fp.read_text(encoding="utf-8")
            section = ""
            m = re.search(r"^章节: (.+)$", content, re.M)
            if m:
                section = m.group(1).strip()
            pdesc = compose_part_desc(desc, idx, len(parts), section,
                                      content) if len(parts) > 1 else desc
            name = fp.name
            cr = mc.call("kb_doc_create",
                         {"kb_id": kb, "name": name, "content": content,
                          "description": pdesc}, timeout=180)
            if not (isinstance(cr, dict) and cr.get("success", True)):
                raise RuntimeError(f"create failed {aid} part {idx}: "
                                   f"{str(cr)[:200]}")
            path = f"{kb}/{name}"
            mc.call("kb_doc_update_tags",
                    {"kb_id": kb, "doc_path": path, "tags": tags}, timeout=120)
            created.append({"name": name, "path": path, "chars": len(content),
                            "desc": pdesc})
        redone.append({"arxiv_id": aid, "kb": kb, "tags": tags, "desc": desc,
                       "pq_meta": j["pq_meta"], "pq_vec": j["pq_vec"],
                       "title": p["title"], "field": p["field"],
                       "parts": created, "redone": True})
        print(f"[redone] {aid}: {len(created)} new parts "
              f"(max {max(c['chars'] for c in created)} ch)", flush=True)

    # 6) 受影响 KB 批量索引 + 图谱 force 重建, 等待完成
    kbs = sorted({r["kb"] for r in redone})
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb_uuid = {k.get("name"): (k.get("kb_id") or k.get("name"))
               for k in cat.get("catalog") or []}
    for kb in kbs:
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        paths = [d.get("path") or f"{kb}/{d.get('name','')}" for d in docs]
        for s in range(0, len(paths), 20):
            http_post(f"{BACKEND}/api/v1/search/batch-index",
                      {"kb_id": kb_uuid.get(kb, kb),
                       "doc_paths": paths[s:s + 20], "force": True},
                      timeout=900)
        mc.call("kb_graph_build", {"kb_id": kb, "force": True}, timeout=300)
        print(f"[rebuild] {kb}: index+graph submitted", flush=True)
    deadline = time.time() + 900
    pending = set(kbs)
    while pending and time.time() < deadline:
        time.sleep(30)
        for kb in list(pending):
            probe = next(r for r in redone if r["kb"] == kb)
            g = mc.call("kb_graph_document",
                        {"doc_path": probe["parts"][0]["path"]}, timeout=120)
            st = mc.call("kb_graph_build", {"kb_id": kb, "force": False},
                         timeout=120)
            running = str((st or {}).get("status")) == "running"
            if not running and isinstance(g, dict) and \
                    g.get("graph", {}).get("graph_doc_id"):
                pending.discard(kb)
        print(f"[rebuild-wait] pending={sorted(pending)}", flush=True)

    (SUITE / "results" / "r2_redo.json").write_text(
        json.dumps({"redone": redone, "graph_pending": sorted(pending)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] redone={len(redone)} papers, graph_pending={sorted(pending)}",
          flush=True)
    mc.close()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(SUITE / "scripts"))
    sys.exit(main())
