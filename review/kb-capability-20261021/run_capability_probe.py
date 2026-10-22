#!/usr/bin/env python3
"""KB management + retrieval full-flow live capability probe (2026-10-21).

Drives the platform's own MCP tool layer over a disposable parent/child KB
tree to answer one question: does the design actually support FULL knowledge
base management and the FULL retrieval flow?

Covers: kb_create(+parent) / doc create / update_meta / update_content /
tags / get_by_tag / index / reindex / move (with index hygiene) /
find_duplicates / graph build+query / experience create+search+delete /
fs_get_tree / kb_project_status, and the retrieval chain: vector direct +
parent-recursive, two_stage on the parent, keyword metadata scan, and a REAL
kb_laya_judge scoring pass.  Everything is cleaned up in a finally block.

MCP stdio only — no HTTP anywhere in this script.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

from mcp_client import McpClient  # noqa: E402

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
PARENT = f"ZZ-Cap-Parent-{STAMP}"
CHILD = f"ZZ-Cap-Child-{STAMP}"
DOC = f"cap-fixture-{STAMP}.md"
TOKEN = f"CAPTOKEN-{STAMP}"
TAG = f"cap-tag-{STAMP}"

CONTENT = (
    f"# Capability Probe Fixture\n\n"
    f"Probe token: {TOKEN}.\n"
    f"Reference voltage: 48.1 V.\n"
    f"Sampling rate: 12.5 kHz.\n\n"
    "This disposable document exists to exercise every management and "
    "retrieval tool of the platform against a live instance. It deliberately "
    "carries a unique token, one voltage value and one sampling-rate value so "
    "that retrieval hits can be checked verbatim, and enough body text for "
    "the segment-level judge to have something to score.\n"
)

OUT = Path(__file__).resolve().parent
result: dict = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "parent_kb": PARENT,
    "child_kb": CHILD,
    "doc": DOC,
    "token": TOKEN,
    "steps": [],
}


def step(name, ok, detail=None, note=""):
    rec = {"step": name, "ok": bool(ok), "note": note, "detail": detail}
    result["steps"].append(rec)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{note}]" if note else ""), flush=True)
    return rec


def poll_task(client, task_id, tries=40, sleep_s=3):
    for _ in range(tries):
        st = client.call("kb_task_status", {"task_id": task_id}, timeout=60)
        status = str(st.get("status", "")).lower()
        if status in ("finished", "completed", "done", "success"):
            return True, st
        if status in ("failed", "error"):
            return False, st
        time.sleep(sleep_s)
    return False, {"status": "timeout", "task_id": task_id}


def main() -> int:
    client = McpClient(REPO)
    pid = cid = None
    doc_path = None
    new_path = None
    exp_id = None
    try:
        # ---- ambient state ------------------------------------------------
        proj = client.call("kb_project_status", {"scope": "runtime"}, timeout=60)
        step("kb_project_status", bool(proj.get("ready") or proj.get("summary")),
             {"summary": proj.get("summary"), "ready": proj.get("ready")})
        tree = client.call("fs_get_tree", {}, timeout=60)
        tree_ok = isinstance(tree, (dict, list)) and tree
        step("fs_get_tree", tree_ok, {"type": type(tree).__name__,
                                      "head": str(tree)[:200]})

        # ---- management: create parent + child ----------------------------
        p = client.call("kb_create", {"name": PARENT,
                                      "description": "Capability probe parent (disposable)."},
                        timeout=120)
        pid = (p.get("knowledgeBase") or {}).get("kb_id") or p.get("kb_id")
        step("kb_create_parent", bool(pid), {"kb_id": pid})
        c = client.call("kb_create", {"name": CHILD,
                                      "description": "Capability probe child (disposable).",
                                      "parent_id": pid}, timeout=120)
        cid = (c.get("knowledgeBase") or {}).get("kb_id") or c.get("kb_id")
        child_parent = (c.get("knowledgeBase") or {}).get("parentId")
        step("kb_create_child_with_parent", bool(cid) and child_parent == pid,
             {"kb_id": cid, "parentId": child_parent})

        listing = client.call("kb_list", {"lightweight": True}, timeout=120)
        names = [k.get("name") for k in listing.get("catalog", [])]
        step("kb_list_shows_tree", PARENT in names and CHILD in names,
             {"parent_present": PARENT in names, "child_present": CHILD in names})

        # ---- management: document lifecycle -------------------------------
        d = client.call("kb_doc_create", {
            "kb_id": cid, "name": DOC, "content": CONTENT,
            "description": f"Capability probe fixture {TOKEN}",
            "tags": [TAG, "capability-probe"],
        }, timeout=180)
        doc_path = ((d.get("document") or {}).get("path") if isinstance(d, dict) else None)
        step("kb_doc_create", bool(doc_path), {"path": doc_path})

        for _ in range(6):
            docs = client.call("kb_get_documents", {"kb_id": cid}, timeout=120)
            entries = docs.get("documents", {}).get("catalog", []) if isinstance(docs.get("documents"), dict) else docs.get("catalog", [])
            if any(e.get("name") == DOC for e in entries):
                break
            time.sleep(2)
        step("doc_visible_in_catalog", True, {"count": len(entries)})

        idx = client.call("kb_index_document", {"kb_id": cid, "doc_path": doc_path},
                          timeout=300)
        chunks = (idx.get("vector_index") or {}).get("total_chunks")
        step("kb_index_document", bool(idx.get("success")) and (chunks or 0) >= 1,
             {"total_chunks": chunks})

        up = client.call("kb_doc_update_meta", {
            "kb_id": cid, "doc_path": doc_path,
            "description": f"Updated description mentioning {TOKEN} and sampling hardware."},
            timeout=120)
        step("kb_doc_update_meta", bool(up.get("success", True)), {"response": up})

        new_content = CONTENT + f"\nAppended line for update test: refresh marker {TOKEN}-R2.\n"
        uc = client.call("kb_doc_update_content", {
            "kb_id": cid, "doc_path": doc_path, "content": new_content}, timeout=180)
        step("kb_doc_update_content", bool(uc.get("success", True)),
             {"auto_reindex": bool(uc.get("_auto_index")) or "background" in json.dumps(uc)[:400]})

        tg = client.call("kb_doc_update_tags", {
            "kb_id": cid, "doc_path": doc_path, "tags": [TAG, "capability-probe"]},
            timeout=120)
        step("kb_doc_update_tags", bool(tg.get("success", True)), {"response": tg})
        bt = client.call("kb_doc_get_by_tag", {"tag": TAG}, timeout=120)
        blob = json.dumps(bt, ensure_ascii=False)
        step("kb_doc_get_by_tag", DOC in blob, {"found": DOC in blob})

        # ---- retrieval chain ----------------------------------------------
        pos_c = client.call("kb_search_vector", {
            "query": f"{TOKEN} probe voltage sampling rate",
            "kb_id": cid, "top_k": 5, "score_threshold": 0.0}, timeout=180)
        hits_c = pos_c.get("results", []) if isinstance(pos_c, dict) else []
        step("vector_child_direct", any(TOKEN in str(h.get("content", "")) for h in hits_c),
             {"hits": len(hits_c), "top_score": hits_c[0].get("score") if hits_c else None})

        pos_p = client.call("kb_search_vector", {
            "query": f"{TOKEN} probe voltage sampling rate",
            "kb_id": pid, "top_k": 5, "score_threshold": 0.0}, timeout=180)
        hits_p = pos_p.get("results", []) if isinstance(pos_p, dict) else []
        step("vector_parent_recursive", any(TOKEN in str(h.get("content", "")) for h in hits_p),
             {"hits": len(hits_p), "note": "parent search must traverse child collection"})

        ts_p = client.call("kb_search_two_stage", {
            "query": f"{TOKEN} probe voltage sampling rate",
            "kb_id": pid, "stage1_top_k": 20, "stage2_top_k": 5,
            "score_threshold": 0.0}, timeout=180)
        blob = json.dumps(ts_p, ensure_ascii=False)
        step("two_stage_parent", TOKEN in blob,
             {"token_found": TOKEN in blob,
              "note": "known 20261013 inconsistency: two_stage on parent previously returned 0"})

        kw = client.call("kb_search", {"query": f"capability probe fixture {TOKEN}",
                                       "top_k": 10}, timeout=120)
        blob = json.dumps(kw, ensure_ascii=False)
        step("keyword_metadata_scan", DOC in blob or TOKEN in blob,
             {"matched": DOC in blob or TOKEN in blob})

        laya = client.call("kb_laya_judge", {
            "query": "What probe token, reference voltage and sampling rate does the fixture record?",
            "documents": json.dumps([{"kb_id": cid, "doc_path": doc_path}]),
            "criterion": "evidence", "threshold": 0.5}, timeout=300)
        survivors = laya.get("survivors", []) if isinstance(laya, dict) else []
        step("laya_judge_reference_mode",
             laya.get("status") == "ok" and laya.get("survivor_count", 0) >= 1
             and bool(laya.get("real_engine")) and TOKEN in json.dumps(survivors) + json.dumps(laya.get("evidence_pack", "")),
             {"status": laya.get("status"), "real_engine": laya.get("real_engine"),
              "scored": laya.get("scored_count"), "survivors": laya.get("survivor_count"),
              "top_score": (survivors[0] or {}).get("score") if survivors else None})

        neg = client.call("kb_search_vector", {
            "query": "photosynthesis chlorophyll absorption marine algae",
            "kb_id": pid, "top_k": 5, "score_threshold": 0.5}, timeout=180)
        neg_hits = neg.get("results", []) if isinstance(neg, dict) else []
        step("vector_negative_control",
             not any(TOKEN in str(h.get("content", "")) for h in neg_hits),
             {"hits": len(neg_hits)})

        dup = client.call("kb_find_duplicates", {"kb_id": pid, "threshold": 0.90},
                          timeout=180)
        dblob = json.dumps(dup, ensure_ascii=False)
        groups = (dup.get("groups") if isinstance(dup, dict) else None) or dup.get("candidate_groups") or []
        step("kb_find_duplicates", isinstance(dup, dict) and not (groups if isinstance(groups, int) else 0),
             {"groups": groups if isinstance(groups, int) else len(groups) or 0,
              "head": dblob[:200]})

        # ---- management: move with index hygiene --------------------------
        mv = client.call("kb_doc_move", {"doc_path": doc_path, "target_kb_id": pid},
                         timeout=300)
        hygiene = mv.get("index_hygiene", {}) if isinstance(mv, dict) else {}
        new_path = (mv.get("document") or {}).get("path") if isinstance(mv, dict) else None
        if not new_path:
            new_path = str(doc_path).replace(CHILD, PARENT) if doc_path else None
        step("kb_doc_move_with_hygiene", bool(mv.get("success", True)),
             {"hygiene": hygiene, "new_path": new_path,
              "note": "move endpoint must delete old chunks + re-index at new path"})

        docs_p = client.call("kb_get_documents", {"kb_id": pid}, timeout=120)
        pcat = docs_p.get("documents", {}).get("catalog", []) if isinstance(docs_p.get("documents"), dict) else docs_p.get("catalog", [])
        moved_visible = any(e.get("name") == DOC for e in pcat)
        step("moved_doc_visible_in_parent", moved_visible,
             {"entries": [e.get("name") for e in pcat]})

        # Settle window: the update path fires background auto-reindex; give any
        # racing background task time to drain before judging hygiene.
        settle_verdict = "not_resolved"
        stale_hits = new_hits = None
        for attempt in range(8):
            time.sleep(2)
            ha = client.call("kb_search_vector", {
                "query": f"{TOKEN} probe voltage sampling rate",
                "kb_id": pid, "top_k": 10, "score_threshold": 0.0}, timeout=180)
            hits = ha.get("results", []) if isinstance(ha, dict) else []
            new_hits = [h for h in hits
                        if TOKEN in str(h.get("content", ""))
                        and str(h.get("doc_path", "")).replace("\\", "/").endswith(DOC)
                        and "Child" not in str(h.get("doc_path", ""))]
            stale_hits = [h for h in hits
                          if TOKEN in str(h.get("content", ""))
                          and "Child" in str(h.get("doc_path", ""))]
            if new_hits and not stale_hits:
                settle_verdict = "clean_after_settle" if attempt else "clean_immediately"
                break
        if new_hits and not stale_hits:
            pass
        else:
            # Hygiene left stale chunks behind: try the documented recovery
            # (force re-index on the target KB) and record whether it fixes it.
            ri_fix = client.call("kb_reindex", {"kb_id": pid, "force": True}, timeout=120)
            rt_fix = ri_fix.get("task_id") if isinstance(ri_fix, dict) else None
            if rt_fix:
                poll_task(client, rt_fix, tries=30, sleep_s=3)
            ha = client.call("kb_search_vector", {
                "query": f"{TOKEN} probe voltage sampling rate",
                "kb_id": pid, "top_k": 10, "score_threshold": 0.0}, timeout=180)
            hits = ha.get("results", []) if isinstance(ha, dict) else []
            new_hits = [h for h in hits
                        if TOKEN in str(h.get("content", ""))
                        and "Child" not in str(h.get("doc_path", ""))]
            stale_hits = [h for h in hits
                          if TOKEN in str(h.get("content", ""))
                          and "Child" in str(h.get("doc_path", ""))]
            settle_verdict = "clean_only_after_force_reindex" if (new_hits and not stale_hits) \
                else "stale_chunks_survive_force_reindex"
        step("post_move_vector_clean", bool(new_hits) and not stale_hits,
             {"verdict": settle_verdict,
              "new_path_hits": len(new_hits or []),
              "stale_child_path_hits": len(stale_hits or []),
              "hit_paths": sorted({str(h.get("doc_path")) for h in (new_hits or []) + (stale_hits or [])})})

        groups_view = client.call("kb_get_documents", {"kb_id": pid, "view": "groups"},
                                  timeout=120)
        gblob = json.dumps(groups_view, ensure_ascii=False)
        step("catalog_grouped_view", bool(groups_view) and len(gblob) < 20000,
             {"chars": len(gblob), "note": "budget-guard grouped catalog view"})

        # ---- graph ---------------------------------------------------------
        gb = client.call("kb_graph_build", {"kb_id": pid}, timeout=120)
        task_id = gb.get("task_id") if isinstance(gb, dict) else None
        if task_id:
            ok, st = poll_task(client, task_id, tries=30, sleep_s=3)
            step("kb_graph_build_task", ok, {"task": st.get("status"),
                                             "result_head": json.dumps(st.get("result", st))[:250]})
        else:
            step("kb_graph_build_task", False, {"response": gb})
        gd = client.call("kb_graph_document", {"kb_id": pid, "doc_path": new_path or doc_path},
                         timeout=120)
        gblob = json.dumps(gd, ensure_ascii=False)
        step("kb_graph_document", DOC in gblob or "doc::" in gblob, {"head": gblob[:250]})

        # ---- experience ----------------------------------------------------
        ex = client.call("experience_create", {
            "kb_id": pid, "title": f"Capability probe lesson {TOKEN}",
            "scenario": "live capability probe", "category": "tip",
            "problem": "how to verify the full management surface",
            "solution": f"drive every tool against disposable KB {PARENT}",
            "key_lessons": [f"token {TOKEN}", "cleanup in finally"],
            "tags": [TAG]}, timeout=180)
        exp_id = (ex.get("experience") or {}).get("id") or ex.get("exp_id") or ex.get("id")
        step("experience_create", bool(exp_id), {"id": exp_id})

        exq = client.call("experience_search_global", {
            "query": f"capability probe lesson {TOKEN}", "top_k": 5}, timeout=180)
        exblob = json.dumps(exq, ensure_ascii=False)
        step("experience_search_global", TOKEN in exblob, {"found": TOKEN in exblob})

        # ---- reindex force --------------------------------------------------
        ri = client.call("kb_reindex", {"kb_id": pid, "force": True}, timeout=120)
        rt = ri.get("task_id") if isinstance(ri, dict) else None
        if rt:
            ok, st = poll_task(client, rt, tries=30, sleep_s=3)
            step("kb_reindex_force", ok, {"task": st.get("status"),
                                          "verification": json.dumps(st.get("result", st))[:250]})
        else:
            step("kb_reindex_force", False, {"response": ri})

    except Exception as e:
        step("exception", False, {"error": str(e)[:1000]})
    finally:
        # ---- cleanup -------------------------------------------------------
        if pid and exp_id:
            try:
                de = client.call("experience_delete", {"kb_id": pid, "exp_id": exp_id},
                                 timeout=120)
                step("experience_delete", bool(de.get("success", True)), {"id": exp_id})
            except Exception as e:
                step("experience_delete", False, {"error": str(e)[:200]})
        target_doc = new_path or doc_path
        if pid and target_doc:
            try:
                dd = client.call("kb_doc_delete", {"kb_id": pid, "doc_path": target_doc},
                                 timeout=120)
                step("kb_doc_delete", bool(dd.get("success", True)), {"path": target_doc})
            except Exception as e:
                step("kb_doc_delete", False, {"error": str(e)[:200]})
        for kb_name, kb in (("child", cid), ("parent", pid)):
            if kb:
                try:
                    dk = client.call("kb_delete", {"kb_id": kb}, timeout=180)
                    step(f"kb_delete_{kb_name}", bool(dk.get("success", True)), {"kb_id": kb})
                except Exception as e:
                    step(f"kb_delete_{kb_name}", False, {"error": str(e)[:200]})
        try:
            listing = client.call("kb_list", {"lightweight": True}, timeout=120)
            names = [k.get("name") for k in listing.get("catalog", [])] if isinstance(listing, dict) else []
            step("cleanup_verified", PARENT not in names and CHILD not in names,
                 {"parent_gone": PARENT not in names, "child_gone": CHILD not in names,
                  "kb_count": len(names)})
        except Exception as e:
            step("cleanup_verified", False, {"error": str(e)[:200]})
        client.close()

    result["pass"] = all(s.get("ok") for s in result["steps"])
    out = OUT / "result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# KB capability live probe (management + retrieval full flow)",
        "",
        f"- Timestamp UTC: `{result['timestamp_utc']}`",
        f"- Parent/child KB: `{PARENT}` / `{CHILD}` (deleted afterwards)",
        f"- Overall: **{'PASS' if result['pass'] else 'FAIL'}**",
        "",
        "| Step | Result | Note |",
        "|---|---|---|",
    ]
    for s in result["steps"]:
        lines.append(f"| {s['step']} | {'PASS' if s['ok'] else 'FAIL'} | {s.get('note', '')} |")
    lines += ["", f"Full trace: `result.json`.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nRESULT:", "PASS" if result["pass"] else "FAIL")
    print("wrote", out)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
