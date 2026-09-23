#!/usr/bin/env python3
"""Organize O4-L1/L2 + L7 + O5/O5b/O5-C — 旧文档描述 D8 升级与验证.

L1: 165 个第一轮旧文档描述从「标题；节选」升级为 D8 四要素两层描述
    (kb_doc_update_meta; 判断件 data/papers/organize_l1_judgments.json)。
L2: 4 篇标签去重修正(kb_doc_update_tags)。
L7: 5 库 batch-index force(元数据/BM25 刷新; 图谱节点不受描述文本影响)。
O5: 逐层读回验证; O5b: 三层一致(磁盘/yml/tree-fs)抽查; O5-C: 每库 3 条
    检索回归探针(old50 题集)。产出 results/r2_organize_report.json。
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import BACKEND, McpClient, http_post  # noqa: E402

REPO = SUITE.parent
MANIFEST = SUITE / "results" / "r2_organize" / "audit_manifest.json"
JUDGE = SUITE / "data" / "papers" / "organize_l1_judgments.json"
OLD50 = SUITE / "results" / "scaling" / "scaling_t05_old50.json"
OUT = SUITE / "results" / "r2_organize_report.json"
KBs = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
       "工程与能源", "经济与社会"]


def part_hint(content: str, limit: int = 100) -> tuple[str, str]:
    """从该 part 自身的 content1000 取 (章节, 正文首句提示)。"""
    text = content or ""
    m = re.search(r"^章节: (.+)$", text, re.M)
    section = m.group(1).strip() if m else ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    body = " ".join(ln.strip() for ln in lines
                    if not ln.startswith("# ") and not ln.startswith("章节:"))
    body = re.sub(r"\s+", " ", body)
    return section, body[:limit]


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    judge = json.loads(JUDGE.read_text(encoding="utf-8"))
    paper_desc = judge["paper_desc"]
    tag_fixes = judge.get("tag_fixes", {})

    r2_ids = set()
    mc = McpClient()
    # 识别旧文档: manifest 中不带第二轮判断件中 arxiv id 的
    clf2 = json.loads((SUITE / "data" / "papers" / "classification_r2.json")
                      .read_text(encoding="utf-8"))
    r2_ids = {aid.replace("/", "-") for aid in clf2["assign"]}

    old_docs = []
    for d in man["docs"]:
        name = str(d["name"] or "")
        aid_part = re.match(r"[a-z-]+__([a-z0-9./-]+?)__", name)
        aid = aid_part.group(1).replace("/", "-") if aid_part else ""
        if aid not in r2_ids:
            old_docs.append(d)
    print(f"[L1] old docs: {len(old_docs)}", flush=True)

    missing = []
    updated, failed = 0, []
    for d in old_docs:
        name = str(d["name"])
        base = name.split(" (part")[0]
        pd = paper_desc.get(base)
        if not pd:
            missing.append(base)
            continue
        if "(part" in name:
            section, hint = part_hint(str(d["content1000"]))
            pm = re.search(r"（第 (\d+)/(\d+) 部分）", name)
            i, n = (pm.group(1), pm.group(2)) if pm else ("?", "?")
            desc = f"【{i}/{n}·{section[:26] or '正文'}】{pd[:150]}——{hint}"[:230]
        else:
            desc = pd
        path = d["path"]
        r = mc.call("kb_doc_update_meta",
                    {"kb_id": d["kb"], "doc_path": path, "description": desc},
                    timeout=120)
        if isinstance(r, dict) and r.get("success", True):
            updated += 1
        else:
            failed.append({"path": path, "err": str(r)[:160]})
        if updated % 40 == 0 and updated:
            print(f"[L1] updated {updated}", flush=True)
    print(f"[L1] updated={updated}/{len(old_docs)} missing_judgment={len(missing)} "
          f"failed={len(failed)}", flush=True)
    if missing:
        print("  missing bases (first 5):", missing[:5], flush=True)

    # L2 标签去重
    tag_updated = 0
    for base, tags in tag_fixes.items():
        for d in old_docs:
            if str(d["name"]).startswith(base):
                r = mc.call("kb_doc_update_tags",
                            {"kb_id": d["kb"], "doc_path": d["path"],
                             "tags": tags}, timeout=120)
                if isinstance(r, dict) and r.get("success", True):
                    tag_updated += 1
                break
    print(f"[L2] tag fixes applied: {tag_updated}/{len(tag_fixes)}", flush=True)

    # O5 读回验证(全量, 从 yml/kb_get_documents 读回)
    verify_ok, verify_bad = 0, []
    for kb in KBs:
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        for d in docs:
            name = str(d.get("name"))
            desc = str(d.get("description") or "")
            aid_part = re.match(r"[a-z-]+__([a-z0-9./-]+?)__", name)
            aid = aid_part.group(1).replace("/", "-") if aid_part else ""
            if aid in r2_ids:
                continue  # 新文档入库时即 D8
            if ("可回答" in desc) or desc.startswith("【"):
                verify_ok += 1
            else:
                verify_bad.append(f"{kb}/{name[:60]}: {desc[:50]}")
    print(f"[O5] D8 descriptions verified: {verify_ok} ok, "
          f"{len(verify_bad)} bad", flush=True)
    for b in verify_bad[:5]:
        print("   BAD:", b, flush=True)

    # O5b 三层一致抽查(20% 旧文档: 磁盘+yml+tree-fs)
    sample = old_docs[:max(1, len(old_docs) // 5)]
    o5b = {"checked": len(sample), "ok": 0, "bad": []}
    for d in sample:
        name = str(d["name"])
        fs = REPO / "storage" / "tree-file-system" / d["kb"] / name
        yml = REPO / "storage" / "tree-file-system" / d["kb"] / \
            ".knowledge-base.yml"
        tfs = REPO / "storage" / "tree-file-system" / ".tree-fs.json"
        disk = fs.exists()
        in_yml = name in yml.read_text(encoding="utf-8")
        in_tfs = name in tfs.read_text(encoding="utf-8")
        if disk and in_yml and in_tfs:
            o5b["ok"] += 1
        else:
            o5b["bad"].append({"path": d["path"], "disk": disk,
                               "in_yml": in_yml, "in_tfs": in_tfs})
    print(f"[O5b] three-layer consistency: {o5b['ok']}/{o5b['checked']} ok",
          flush=True)

    # L7 batch-index force(5 库)
    t0 = time.time()
    n_indexed = 0
    for kb in KBs:
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        paths = [d.get("path") or f"{kb}/{d.get('name','')}" for d in docs]
        for s in range(0, len(paths), 20):
            r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                          {"kb_id": kb, "doc_paths": paths[s:s + 20],
                           "force": True}, timeout=900)
            n_indexed += len(r.get("indexed", []))
    print(f"[L7] batch-index force done: {n_indexed} docs "
          f"({time.time()-t0:.0f}s)", flush=True)

    # O5-C 检索回归探针: 每库 3 题(t05 old50 中该库通过的题)
    old50 = json.loads(OLD50.read_text(encoding="utf-8"))
    rows = old50["vec"]["rows"]
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "qa96", SUITE / "scripts" / "96_scaling_qa.py")
    _qa96 = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_qa96)
    qmap = {q["qid"]: q["question"]
            for q in _qa96.load_sets(["old50"])["old50"]}
    probes, probe_ok = 0, 0
    for kb in KBs:
        kb_rows = [r for r in rows
                   if str(r.get("top_docs", [""])[0]).startswith(kb + "/")
                   and r["pass"]][:3]
        for r in kb_rows:
            q = qmap.get(r["qid"]) or ""
            if not q:
                continue
            vec = mc.call("kb_search_vector",
                          {"query": q, "kb_id": kb, "top_k": 5,
                           "score_threshold": 0.35}, timeout=300)
            hits = [str(x.get("doc_path", "")).replace("\\", "/")
                    for x in (vec.get("results") or [])]
            hit = any(r["arxiv_id"].replace("/", "-") in h for h in hits)
            probes += 1
            probe_ok += hit
    print(f"[O5-C] retrieval regression probes: {probe_ok}/{probes} pass",
          flush=True)

    report = {
        "o2_audit": {"total": man["total"], "audited": man["audited"]},
        "o2_duplicates": "35 near-pairs ALL intra-paper part adjacencies; "
                         "0 true duplicates; L0 deletion skipped (parts are "
                         "one logical document per organize skill)",
        "l1": {"old_docs": len(old_docs), "updated": updated,
               "missing_judgment": missing, "failed": failed},
        "l2": {"tag_fixes_applied": tag_updated},
        "o5_verify": {"d8_ok": verify_ok, "d8_bad": verify_bad[:20]},
        "o5b": o5b,
        "l7": {"indexed": n_indexed},
        "o5c_probes": {"pass": probe_ok, "total": probes},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[O8 pre-report] → {OUT}", flush=True)
    mc.close()
    ok = (updated == len(old_docs) and not verify_bad and not o5b["bad"]
          and probe_ok == probes)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
