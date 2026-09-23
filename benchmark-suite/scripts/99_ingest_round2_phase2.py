#!/usr/bin/env python3
"""Ingest R2 Phase 2 (A5+A6+A6-V+A3c-R+A7+A9) — round-2 拆分件路由入库.

输入:
  results/r2_survey.json              — Phase 1 真实解析产物(三窗口/拆分件清单)
  data/papers/classification_r2.json  — Archival(执行 Agent) 判断件(A3d 归属 +
    A3b 清洗后标签 + A3c 论文级 D8 描述 + problem_query 检索自测句), 消费不内嵌。
流程(每篇): 逐 part 组装两层描述(【i/N·章节】论文级主体方法 —— 本部分内容)
  → kb_doc_create(直路, 拆分后许可) → kb_doc_update_tags → 批量索引(force)
  → 各 KB kb_graph_build(force, 异步轮询) → A6-V 逐篇探针(problem_query 在
  归属库召回) → A3c-R 双通道自测(kb_search 元数据 + kb_search_vector 改述)
  → C1-C9 终检 → A9 报告 results/r2_ingest_report.json。
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

PAPERS = SUITE / "data" / "papers"
SURVEY = SUITE / "results" / "r2_survey.json"
CLF = SUITE / "data" / "papers" / "classification_r2.json"
OUT = SUITE / "results" / "r2_ingest_report.json"
INDEX_WAIT = 600


def part_body_hint(content: str, limit: int = 110) -> str:
    """取 part 头(标题+章节行)之后的真实正文首句作本部分内容提示。"""
    lines = content.splitlines()
    body_start = 0
    for i, ln in enumerate(lines[:8]):
        if ln.startswith("# ") or ln.startswith("章节:"):
            body_start = i + 1
    body = " ".join(l.strip() for l in lines[body_start:] if l.strip())
    body = re.sub(r"\s+", " ", body)
    return body[:limit]


def compose_part_desc(paper_desc: str, i: int, n: int, section: str,
                      content: str) -> str:
    hint = part_body_hint(content)
    core = paper_desc[:150]
    head = f"【{i}/{n}·{section[:26] or '正文'}】"
    d = f"{head}{core}——{hint}"
    return d[:230]


def main() -> int:
    survey = json.loads(SURVEY.read_text(encoding="utf-8"))
    clf = json.loads(CLF.read_text(encoding="utf-8"))
    assign = clf["assign"]
    ok_papers = [p for p in survey["papers"]
                 if not p.get("error") and not p.get("rejected")]
    missing = [p["arxiv_id"] for p in ok_papers if p["arxiv_id"] not in assign]
    if missing:
        raise SystemExit(f"classification_r2.json 缺少判断: {missing}")
    kbs = sorted({assign[p["arxiv_id"]]["kb"] for p in ok_papers})
    print(f"[plan] {len(ok_papers)} papers -> {len(kbs)} KBs: {kbs}", flush=True)

    mc = McpClient()
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    have = {k.get("name"): (k.get("kb_id") or k.get("name"))
            for k in cat.get("catalog") or []}
    for kb in kbs:
        if kb not in have:
            raise SystemExit(f"目标库不存在: {kb}")

    records, failures = [], []
    for p in ok_papers:
        aid, slug = p["arxiv_id"], p["slug"]
        j = assign[aid]
        kb, tags, desc = j["kb"], j["tags"], j["desc"]
        pq_meta = j.get("problem_query") or j.get("pq_meta") or ""
        pq_vec = j.get("pq_vec") or pq_meta
        if not pq_meta or not pq_vec:
            raise RuntimeError(f"{aid}: 判断件缺少 problem_query/pq_vec")
        part_dir = Path(p["part_dir"]) if p.get("split") else None
        names = p["parts"] if p.get("split") else [Path(p["single_path"]).name]
        created = []
        try:
            for idx, name in enumerate(names, 1):
                if part_dir:
                    content = (part_dir / name).read_text(encoding="utf-8")
                else:
                    content = Path(p["single_path"]).read_text(encoding="utf-8")
                section = ""
                m = re.search(r"^章节: (.+)$", content, re.M)
                if m:
                    section = m.group(1).strip()
                pdesc = compose_part_desc(desc, idx, len(names), section,
                                          content) if len(names) > 1 else desc
                r = mc.call("kb_doc_create",
                            {"kb_id": kb, "name": name, "content": content,
                             "description": pdesc}, timeout=180)
                if not (isinstance(r, dict) and r.get("success", True)):
                    raise RuntimeError(f"create failed part {idx}: "
                                       f"{str(r)[:200]}")
                created.append({"name": name, "path": f"{kb}/{name}",
                                "chars": len(content), "desc": pdesc})
            for c in created:
                tr = mc.call("kb_doc_update_tags",
                             {"kb_id": kb, "doc_path": c["path"], "tags": tags},
                             timeout=120)
                if not (tr or {}).get("success", True):
                    print(f"[warn] tags failed {c['path']}", flush=True)
            records.append({"arxiv_id": aid, "slug": slug, "field": p["field"],
                            "kb": kb, "tags": tags, "desc": desc,
                            "pq_meta": pq_meta, "pq_vec": pq_vec,
                            "parts": created, "title": p["title"]})
            print(f"[stored] {kb} <- {slug[:48]} ({len(created)} parts)",
                  flush=True)
        except Exception as ex:  # noqa: BLE001
            failures.append({"arxiv_id": aid, "slug": slug,
                             "error": str(ex)[:300]})
            print(f"[ERROR] {slug[:50]}: {str(ex)[:200]}", flush=True)

    # 批量索引(force) + 图谱重建(异步轮询) — 逐 KB
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb_uuid = {k.get("name"): (k.get("kb_id") or k.get("name"))
               for k in cat.get("catalog") or []}
    n_indexed = 0
    for kb in kbs:
        docs_list = mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
        paths = [d.get("path") or f"{kb}/{d.get('name','')}"
                 for d in docs_list.get("documents") or []]
        for s in range(0, len(paths), 20):
            r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                          {"kb_id": kb_uuid.get(kb, kb),
                           "doc_paths": paths[s:s + 20], "force": True},
                          timeout=900)
            n_indexed += len(r.get("indexed", []))
        print(f"[index] {kb}: batch submitted ({len(paths)} docs)",
              flush=True)
    deadline = time.time() + INDEX_WAIT
    for kb in kbs:
        mc.call("kb_graph_build", {"kb_id": kb, "force": True}, timeout=300)
        print(f"[graph] {kb}: build submitted", flush=True)
    time.sleep(30)
    graph_ok = {}
    deadline = time.time() + INDEX_WAIT
    pending = set(kbs)
    while pending and time.time() < deadline:
        time.sleep(20)
        for kb in list(pending):
            probe = next((r for r in records if r["kb"] == kb), None)
            if not probe:
                pending.discard(kb)
                continue
            doc_path = probe["parts"][0]["path"]
            g = mc.call("kb_graph_document", {"doc_path": doc_path},
                        timeout=120)
            if isinstance(g, dict) and g.get("document"):
                pending.discard(kb)
        print(f"[graph-wait] pending={sorted(pending)}", flush=True)
    graph_ok = {kb: kb not in pending for kb in kbs}

    # A6-V + A3c-R + C1/C8 — 逐篇(A6-V/A3c-R 向量通道用改述 pq_vec, 元数据通道用问题原述 pq_meta)
    for r in records:
        aid, kb = r["arxiv_id"], r["kb"]
        pq_vec, pq_meta = r["pq_vec"], r["pq_meta"]
        first_path = r["parts"][0]["path"]
        vec = mc.call("kb_search_vector",
                      {"query": pq_vec, "kb_id": kb, "top_k": 10,
                       "score_threshold": 0.3}, timeout=300)
        paths = [str(x.get("doc_path", "")).replace("\\", "/")
                 for x in (vec.get("results") or [])]
        a6v = any(aid in pp for pp in paths)
        r["a6v_probe"] = a6v
        meta = mc.call("kb_search", {"query": pq_meta, "top_k": 8}, timeout=300)
        meta_paths = [str(x.get("doc_path", "")).replace("\\", "/")
                      for x in (meta.get("results") or [])]
        c9_meta = any(aid in pp for pp in meta_paths)
        read = mc.call("kb_doc_read", {"kb_id": kb, "doc_path": first_path,
                                       "max_chars": 500}, timeout=120)
        c1 = bool((read or {}).get("content"))
        # C8 三层一致: yml 磁盘层含该文档
        yml = SUITE.parent / "storage" / "tree-file-system" / kb / \
            ".knowledge-base.yml"
        c8 = first_path.rsplit("/", 1)[-1] in yml.read_text(encoding="utf-8")
        g = mc.call("kb_graph_document", {"doc_path": first_path}, timeout=120)
        c7 = bool(isinstance(g, dict) and g.get("document"))
        r["final_check"] = {"C1_readback": c1, "C7_graph": c7 and graph_ok.get(kb, False),
                            "C8_three_layer": c8, "C9_meta_hit": c9_meta,
                            "A6V_vec_probe": a6v}
        flag = "OK " if all(r["final_check"].values()) else "!! "
        print(f"[{flag}A7] {aid}: {r['final_check']}", flush=True)

    n_ok = sum(1 for r in records
               if all(r["final_check"].values()) and r["a6v_probe"])
    report = {
        "round": 2, "papers_total": len(ok_papers), "papers_ok": n_ok,
        "papers_failed": failures, "docs_created": sum(len(r["parts"])
                                                       for r in records),
        "indexed_docs": n_indexed, "graph_ok": graph_ok,
        "kb_distribution": {kb: sum(1 for r in records if r["kb"] == kb)
                            for kb in kbs},
        "records": records}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[A9 done] ok={n_ok}/{len(ok_papers)} papers, "
          f"{report['docs_created']} docs, failed={len(failures)} → {OUT}",
          flush=True)
    mc.close()
    return 0 if n_ok == len(ok_papers) and not failures else 1


if __name__ == "__main__":
    sys.exit(main())
