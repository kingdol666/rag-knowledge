#!/usr/bin/env python3
"""Organize O1+O2 — 全库调研 + 深度内容审计(O2-M 全覆盖清单).

O1: kb_list + kb_tags_list → 拓扑。
O2: 5 门类库逐文档 kb_doc_read(max_chars=1000)(真实 MCP 调用, 不用文件名猜) →
    results/r2_organize/audit_manifest.json, 每行 {kb, path, name, cur_desc,
    cur_tags, content1000}。O2-M 断言: audited == total。
附: kb_find_duplicates(kb_id) 逐库查重(exact SHA256 + near ≥0.90)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

OUT_DIR = SUITE / "results" / "r2_organize"
KB_CATEGORIES = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                 "工程与能源", "经济与社会"]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mc = McpClient()
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kbs = [k for k in (cat.get("catalog") or []) if k.get("name") in KB_CATEGORIES]
    o1 = [{"name": k.get("name"), "kb_id": k.get("kb_id"),
           "doc_count": k.get("doc_count"), "description": k.get("description")}
          for k in kbs]
    (OUT_DIR / "o1_survey.json").write_text(
        json.dumps(o1, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[O1]", [(k["name"], k["doc_count"]) for k in o1], flush=True)

    tags = mc.call("kb_tags_list", {}, timeout=120)
    (OUT_DIR / "o1_tags.json").write_text(
        json.dumps(tags, ensure_ascii=False, indent=1), encoding="utf-8")

    manifest, total, audited = [], 0, 0
    dups = {}
    for k in o1:
        kb = k["name"]
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        total += len(docs)
        for d in docs:
            path = d.get("path") or f"{kb}/{d.get('name','')}"
            read = mc.call("kb_doc_read",
                           {"kb_id": kb, "doc_path": path, "max_chars": 1000},
                           timeout=120)
            content = str((read or {}).get("content") or "")
            audited += 1
            manifest.append({"kb": kb, "path": path, "name": d.get("name"),
                             "cur_desc": str(d.get("description") or ""),
                             "cur_tags": d.get("tags") or [],
                             "content1000": content[:1000]})
        dup = mc.call("kb_find_duplicates", {"kb_id": kb, "threshold": 0.90},
                      timeout=600)
        groups = (dup or {}).get("duplicate_groups") or []
        dups[kb] = groups
        print(f"[O2] {kb}: audited {len(docs)} docs, "
              f"dup_groups={len(groups)}", flush=True)

    (OUT_DIR / "audit_manifest.json").write_text(
        json.dumps({"total": total, "audited": audited, "docs": manifest},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "o2_duplicates.json").write_text(
        json.dumps(dups, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[O2-M] audited={audited}/{total} "
          f"({'PASS' if audited == total else 'FAIL — 禁止进入 O3'})", flush=True)
    mc.close()
    return 0 if audited == total else 1


if __name__ == "__main__":
    sys.exit(main())
