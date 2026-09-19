#!/usr/bin/env python3
"""A3b 补齐 — 给 5 门类库中每个文档 part 打上所属论文的内容标签.

paper(slug) → CLASSIFY tags(与 61 号脚本同一映射, 读 ingest_report.json 路由结果)。
part 文件名以 slug 开头(大文档自动拆分), 逐 part PATCH 标签。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

def kb_catalog(mc) -> dict:
    """kb_list 双形状回退: lightweight 的 catalog 偶发为空(上游缺 success 标志),
    此时回退 full 模式的 knowledgeBases(kbId/name)。"""
    r = mc.call("kb_list", {"lightweight": True}, timeout=120)
    cat = r.get("catalog") or []
    if cat:
        return {k.get("name"): k.get("kb_id") for k in cat}
    r = mc.call("kb_list", {}, timeout=120)
    return {k.get("name"): k.get("kbId")
            for k in (r.get("knowledgeBases") or [])}


def main() -> int:
    report = json.loads((SUITE / "results" / "ingest_report.json")
                        .read_text(encoding="utf-8"))
    tag_by_slug = {r["slug"]: {"tags": r["tags"], "kb": r["kb"]}
                   for r in report["routed"]}
    mc = McpClient()
    uuid = kb_catalog(mc)
    if not uuid:
        raise RuntimeError("kb_list returned empty catalog (both shapes)")
    target_kbs = {v["kb"] for v in tag_by_slug.values()}
    ok = fail = 0
    t0 = time.perf_counter()
    for kb_name, kid in uuid.items():
        if not kid or kb_name not in target_kbs:
            continue
        docs = mc.call("kb_get_documents", {"kb_id": kid}, timeout=180)
        for d in docs.get("documents") or []:
            name = str(d.get("name", ""))
            slug = next((s for s in tag_by_slug if name.startswith(s)), None)
            if not slug:
                continue
            meta = tag_by_slug[slug]
            r = mc.call("kb_doc_update_tags",
                        {"kb_id": kid, "doc_path": f"{kb_name}/{name}",
                         "tags": meta["tags"]}, timeout=120)
            if (r or {}).get("success"):
                ok += 1
            else:
                fail += 1
                print(f"[fail] {name[:50]}: {str(r)[:120]}", flush=True)
            if (ok + fail) % 100 == 0:
                print(f"[progress] ok={ok} fail={fail}", flush=True)
    mc.close()
    (SUITE / "results" / "tags_report.json").write_text(
        json.dumps({"ok": ok, "fail": fail,
                    "seconds": round(time.perf_counter() - t0, 1)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] tagged ok={ok} fail={fail} in {time.perf_counter()-t0:.0f}s")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
