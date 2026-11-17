# -*- coding: utf-8 -*-
"""Stage 2（v2）—— 数据驱动全量入库：读 corpus_spec_final.json（11 域 100+ 篇）。

机制同 s2：>28KB 分卷 "(part i of n)"；PDF 走 MinerU 解析链；逐库 reindex；
产物 artifacts/s2_ingest_report_v2.json。幂等前置：同前缀旧库需先删（见 Stage 9 清场）。
运行: uv run --no-sync --directory kb-mcp python .../s2b_ingest_spec.py [--dry-run]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
SSE_URL = "http://127.0.0.1:8000/sse"
SPLIT_CHARS = 28_000


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


def load_spec():
    return json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))


def plan(spec):
    plans = []
    for m in spec:
        for d in m["docs"]:
            p = CORPUS / d["file"]
            if not p.exists():
                plans.append(dict(kb=m["slug"], file=d["file"], action="SKIP-MISSING")); continue
            if d["file"].lower().endswith(".pdf"):
                plans.append(dict(kb=m["slug"], file=d["file"], action="parse->save")); continue
            n = len(p.read_text(encoding="utf-8", errors="replace").encode("utf-8"))
            parts = max(1, -(-n // SPLIT_CHARS))
            plans.append(dict(kb=m["slug"], file=d["file"], bytes=n,
                              action="create" if parts == 1 else f"split x{parts}"))
    return plans


async def run(dry: bool):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    if dry:
        plans = plan(spec)
        (ART / "s2b_dryrun.json").write_text(json.dumps(plans, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
        by = {}
        for x in plans:
            by[x["action"]] = by.get(x["action"], 0) + 1
        print(json.dumps(by, ensure_ascii=False), "total", len(plans))
        return
    report = dict(kbs={}, started=time.strftime("%Y-%m-%d %H:%M:%S"))
    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            pdfs_all = []
            for m in spec:
                d = cj(await s.call_tool("kb_create", {"name": m["kb_name"], "description": m["kb_desc"]}))
                kb_id = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
                entry = dict(kb_id=kb_id, docs=[], parts=0)
                for d_ in m["docs"]:
                    p = CORPUS / d_["file"]
                    if not p.exists():
                        entry["docs"].append(dict(file=d_["file"], ok=False, error="missing")); continue
                    if d_["file"].lower().endswith(".pdf"):
                        pdfs_all.append((m["kb_name"], kb_id, p, d_["name"], d_["desc"]))
                        continue
                    content = p.read_text(encoding="utf-8", errors="replace")
                    if len(content.encode("utf-8")) <= SPLIT_CHARS:
                        dd = cj(await s.call_tool("kb_doc_create", {
                            "kb_id": kb_id, "name": d_["name"], "content": content,
                            "description": d_["desc"]}))
                        ok = bool(dd.get("success") or dd.get("files"))
                        entry["docs"].append(dict(file=d_["file"], name=d_["name"], ok=ok)); entry["parts"] += 1
                    else:
                        chunks = [content[i:i + SPLIT_CHARS] for i in range(0, len(content), SPLIT_CHARS)]
                        stem = Path(d_["name"]).stem
                        for i, ch in enumerate(chunks, 1):
                            dd = cj(await s.call_tool("kb_doc_create", {
                                "kb_id": kb_id, "name": f"{stem} (part {i} of {len(chunks)}).md",
                                "content": ch, "description": f"[{i}/{len(chunks)}] {d_['desc']}"}))
                            ok = bool(dd.get("success") or dd.get("files"))
                            entry["docs"].append(dict(file=d_["file"], name=f"{stem} (part {i} of {len(chunks)}).md", ok=ok))
                        entry["parts"] += len(chunks)
                rr = cj(await s.call_tool("kb_reindex", {"kb_id": kb_id}))
                entry["reindex_ok"] = bool(rr.get("success", False))
                report["kbs"][m["kb_name"]] = entry
                print(f"ingest {m['slug']:14s} kb={kb_id[:8]} parts={entry['parts']} reindex={entry['reindex_ok']}",
                      flush=True)
            # PDF 解析链
            if pdfs_all:
                paths = [str(p) for _, _, p, _, _ in pdfs_all]
                d = cj(await s.call_tool("parse_doc_batch", {"file_paths": paths, "use_ocr": True}))
                tid = d.get("task_id", "")
                md_by_src, done = {}, False
                for _ in range(300):
                    await asyncio.sleep(4)
                    d = cj(await s.call_tool("parse_task_status", {"task_id": tid}))
                    st = str(d.get("status", "")).lower()
                    if st in ("done", "completed", "success", "finished", "error", "failed"):
                        done = st in ("done", "completed", "success", "finished")
                        res = d.get("result") if isinstance(d.get("result"), dict) else {}
                        for r_ in res.get("results") or d.get("results") or []:
                            md_by_src[r_.get("source_filename") or ""] = r_.get("markdown_path") or ""
                        break
                print(f"pdf parse done={done} md={len(md_by_src)}/{len(paths)}", flush=True)
                for spec_name, kb_id, p, name, desc in pdfs_all:
                    md = md_by_src.get(p.name, "")
                    ok = False
                    if done and md:
                        dd = cj(await s.call_tool("kb_doc_save_parsed", {
                            "parent_id": kb_id, "markdown_path": md,
                            "source_filename": p.name, "description": desc}))
                        files = dd.get("files") or []
                        ok = bool(dd.get("success") and files)
                    report["kbs"][spec_name]["docs"].append(dict(file=p.name, ok=ok))
                for spec_name in {sn for sn, _, _, _, _ in pdfs_all}:
                    cj(await s.call_tool("kb_reindex", {"kb_id": report["kbs"][spec_name]["kb_id"]}))
    (ART / "s2_ingest_report_v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    total = sum(e["parts"] for e in report["kbs"].values())
    bad = [x for e in report["kbs"].values() for x in e["docs"] if not x.get("ok")]
    print(f"\n=== S2(v2) done: KBs={len(report['kbs'])} parts={total} failures={len(bad)}")
    if bad:
        print(json.dumps(bad[:10], ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run(dry="--dry-run" in sys.argv))
