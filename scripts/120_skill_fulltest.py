#!/usr/bin/env python3
"""全量 skill 实测驱动器 v2 — 沙盒对象上跑完整生命周期（MCP stdio 通道）.

v2 修正: kb_get_documents 返回 catalog 键; 异步任务结果嵌套在 result 下;
experience_* 用 exp_id; soul_rollback 必须带 checkpoint_id; .md 按 skill 契约
直存不 parse(parse_doc 仅收 pdf/png/jpg/jpeg/docx/xlsx); 边界用例按
success=False 判定拒绝(结构化拒绝是正确行为, 不抛 MCP 异常).

覆盖: kb_create → ingest(save/tags/index) → list/read → search(vector/two_stage)
→ librarian(complete_recall) → organize(duplicates) → manage(rename/move) →
batch(batch_index) → verify(stats) → graph(build/search/central) →
experience(CRUD) → soul(init/qdcvr_ask/ask-routing/train_rl/drafts/checkpoint/
rollback/reflect/export/delete) → 规范边界用例 → 清理.

只触碰本次新建的沙盒: KB s-audit-a/b-20260927 + soul-skillaudit, 结束全部删除.
用法: python scripts/120_skill_fulltest.py [--skip-train] [--out review/dir]
退出码: 有 FAIL → 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

KB_A = "s-audit-a-20260927"
KB_B = "s-audit-b-20260927"
SOUL = "soul-skillaudit"
TS = time.strftime("%Y-%m-%d %H:%M:%S")

DOC1 = """# Zephyr-7 Quantum Widget Specification

The Zephyr-7 quantum widget has a coolant capacity of 42 liters.

Operating frequency is 18.4 GHz under standard lab conditions.

Maintenance requires recalibration every 500 operational hours.
"""
DOC2 = """# Aurora-9 Handshake Protocol

The Aurora-9 handshake protocol requires exactly 3 round trips
before key exchange may begin.

Timeout per round trip is 250 ms.
"""

results: list[dict] = []


def step(mc: McpClient, name: str, fn, timeout=120.0):
    t0 = time.perf_counter()
    try:
        ok, detail, ev = fn(mc)
    except Exception as e:  # noqa: BLE001
        ok, detail, ev = False, f"{type(e).__name__}: {str(e)[:200]}", ""
    ms = round((time.perf_counter() - t0) * 1000)
    results.append({"step": name, "ok": ok, "ms": ms, "detail": str(detail)[:400],
                    "evidence": str(ev)[:600]})
    print(f"  {'PASS' if ok else 'FAIL'} [{ms:>6}ms] {name}"
          + (f" — {str(detail)[:120]}" if detail else ""), flush=True)
    return ok


def poll_task(mc: McpClient, task_id: str, timeout_s: float, interval=4.0) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        r = mc.call("kb_task_status", {"task_id": task_id}, timeout=60)
        last = r
        st = str(r.get("status", "")).lower()
        if st in ("done", "completed", "success", "finished", "failed", "error"):
            return r
        time.sleep(interval)
    return {**last, "status": "poll-timeout"}


def task_result(fin: dict) -> dict:
    """异步任务的业务结果嵌套在 result 键下。"""
    r = fin.get("result")
    return r if isinstance(r, dict) else {}


def docs_of(mc: McpClient, kb: str) -> list:
    r = mc.call("kb_get_documents", {"kb_id": kb, "lightweight": True}, timeout=60)
    return r.get("catalog") or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--out", default="review/skill-fulltest-20260927")
    args = ap.parse_args()
    outdir = REPO / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    mc = McpClient()
    ok_all = True
    ctx: dict = {}

    # ── KB 生命周期 ────────────────────────────────────────────────────────
    print(f"[fulltest] {TS} · Phase KB  (sandbox {KB_A} / {KB_B})", flush=True)

    def s_kb_create(m):
        r = m.call("kb_create", {"name": KB_A, "description": "skill fulltest sandbox A"})
        ctx["kb_a"] = (r.get("knowledgeBase") or {}).get("id") or KB_A
        return bool(r.get("success")), f"kb_id={ctx['kb_a']}", r
    ok_all &= step(mc, "kb_create(A)", s_kb_create, timeout=60)

    def s_kb_create_b(m):
        r = m.call("kb_create", {"name": KB_B, "description": "skill fulltest sandbox B"})
        ctx["kb_b"] = (r.get("knowledgeBase") or {}).get("id") or KB_B
        return bool(r.get("success")), f"kb_id={ctx['kb_b']}", r
    ok_all &= step(mc, "kb_create(B)", s_kb_create_b, timeout=60)

    # ingest (A5/A3b/A6) — .md 按 skill 契约直存, 不 parse
    tmp = outdir / "docs"
    tmp.mkdir(exist_ok=True)
    (tmp / "zephyr7-spec.md").write_text(DOC1, encoding="utf-8")

    def s_save(m):
        r = m.call("kb_doc_save_parsed",
                   {"parent_id": ctx["kb_a"], "markdown": DOC1,
                    "source_filename": "zephyr7-spec.md",
                    "description": "Zephyr-7 widget spec with coolant 42 liters fact"},
                   timeout=120)
        files = r.get("files") or []
        name = files[0].get("name", "") if files else ""
        # v2 修复验证: .md 源不应再出现 .md.md / (1) 命名
        okname = name == "zephyr7-spec.md"
        return bool(r.get("success")) and okname, f"saved name={name!r}", r
    ok_all &= step(mc, "kb_doc_save_parsed(A5 存储+.md命名)", s_save, timeout=130)

    def s_create_doc2(m):
        r = m.call("kb_doc_create",
                   {"kb_id": ctx["kb_a"], "name": "aurora9-protocol.md",
                    "content": DOC2, "description": "Aurora-9 handshake protocol",
                    "tags": ["audit", "aurora"]}, timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_doc_create(doc2+tags)", s_create_doc2, timeout=70)

    def s_create_doc3_dup(m):
        # A0 内容去重契约: 与 doc1 完全相同的内容 → 不落新文件, 返回 deduped 标志
        r = m.call("kb_doc_create",
                   {"kb_id": ctx["kb_a"], "name": "zephyr7-spec-copy.md",
                    "content": DOC1, "description": "identical copy (dedup probe)",
                    "tags": ["audit", "zephyr"]}, timeout=60)
        doc = r.get("document") or {}
        deduped = bool(doc.get("deduped"))
        n = len(docs_of(m, ctx["kb_a"]))
        ok = bool(r.get("success")) and deduped and n == 2
        return ok, f"deduped={deduped} catalog={n} (A0 去重契约)", r
    ok_all &= step(mc, "kb_doc_create(identical)→A0 去重不落盘", s_create_doc3_dup, timeout=70)

    def s_create_doc3_near(m):
        # 近重复(多一行) → 应真实落盘, 供改名/移动/查重链路使用
        r = m.call("kb_doc_create",
                   {"kb_id": ctx["kb_a"], "name": "zephyr7-spec-copy.md",
                    "content": DOC1 + "\nVariant note: this copy adds one line for duplicate audit.\n",
                    "description": "near-duplicate of spec (one line differs)",
                    "tags": ["audit", "zephyr"]}, timeout=60)
        n = len(docs_of(m, ctx["kb_a"]))
        return bool(r.get("success")) and n == 3 and not (r.get("document") or {}).get("deduped"), \
            f"catalog={n} near-dup 落盘", r
    ok_all &= step(mc, "kb_doc_create(near-dup)落盘=3", s_create_doc3_near, timeout=70)

    def s_tags(m):
        r = m.call("kb_doc_update_tags",
                   {"kb_id": ctx["kb_a"], "doc_path": "zephyr7-spec.md",
                    "tags": ["audit", "zephyr"]}, timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_doc_update_tags(A3b 标签)", s_tags, timeout=70)

    def s_index(m):
        r = m.call("kb_index_document",
                   {"kb_id": ctx["kb_a"], "doc_path": "zephyr7-spec.md",
                    "content": DOC1}, timeout=120)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_index_document(A6 索引 doc1)", s_index, timeout=130)

    def s_index_all(m):
        r = m.call("kb_batch_index",
                   {"kb_id": ctx["kb_a"],
                    "doc_paths": ["aurora9-protocol.md", "zephyr7-spec-copy.md"],
                    "force": True}, timeout=300)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_batch_index(batch 全量)", s_index_all, timeout=320)

    def s_list(m):
        docs = docs_of(m, ctx["kb_a"])
        names = sorted(d.get("name", "") for d in docs)
        okn = len(docs) == 3 and "zephyr7-spec.md" in names
        return okn, f"docs={len(docs)} {names}", names
    ok_all &= step(mc, "kb_get_documents(catalog=3)", s_list, timeout=70)

    def s_read(m):
        cat = {d.get("name"): d for d in docs_of(m, ctx["kb_a"])}
        d1 = cat.get("zephyr7-spec.md") or {}
        r = m.call("kb_doc_read", {"kb_id": ctx["kb_a"],
                                   "doc_id": d1.get("doc_id", "")}, timeout=60)
        body = json.dumps(r, ensure_ascii=False)
        return "42 liters" in body, "content 含 42 liters", body[:100]
    ok_all &= step(mc, "kb_doc_read(A7 终检·by doc_id)", s_read, timeout=70)

    def s_vec(m):
        r = m.call("kb_search_vector",
                   {"query": "Zephyr-7 coolant capacity", "kb_id": ctx["kb_a"],
                    "top_k": 5, "score_threshold": 0.0}, timeout=120)
        hits = r.get("results") or []
        top = hits[0] if hits else {}
        score = float(top.get("score") or top.get("similarity") or 0)
        blob = json.dumps(top, ensure_ascii=False)
        return ("zephyr" in blob.lower()) and score >= 0.35, f"top_score={score}", blob[:150]
    ok_all &= step(mc, "kb_search_vector(命中≥0.35)", s_vec, timeout=130)

    def s_2stage(m):
        r = m.call("kb_search_two_stage",
                   {"query": "how many round trips does Aurora-9 need",
                    "kb_id": ctx["kb_a"], "stage2_top_k": 3}, timeout=180)
        blob = json.dumps(r, ensure_ascii=False)
        return r.get("success") is not False and "aurora" in blob.lower(), "two_stage 命中 aurora", blob[:150]
    ok_all &= step(mc, "kb_search_two_stage(命中)", s_2stage, timeout=200)

    def s_librarian(m):
        docs = docs_of(m, ctx["kb_a"])
        kb_id = ctx["kb_a"]
        full = m.call("kb_get_documents", {"kb_id": kb_id, "lightweight": False}, timeout=60)
        full_by_name = {d.get("name"): d for d in (full.get("documents") or [])}
        manifest = {
            "query": "Zephyr-7 coolant capacity specification",
            "max_segment_chars": 400,
            "knowledge_bases": [{"kb_id": kb_id, "name": KB_A,
                                 "description": "skill fulltest sandbox"}],
            "documents": [{"kb_id": kb_id,
                           "doc_id": d.get("doc_id", ""),
                           "doc_path": d.get("doc_path", ""),
                           "name": d.get("name", ""),
                           "description": d.get("description", ""),
                           "content": (full_by_name.get(d.get("name", "")) or {}).get("content", "")
                           or (full_by_name.get(d.get("name", "")) or {}).get("markdown", "")}
                          for d in docs],
        }
        man_p = outdir / "librarian-manifest.json"
        man_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        out_p = outdir / "librarian-output.json"
        proc = subprocess.run(
            [sys.executable, str(REPO / ".claude/skills/knowledgebase-librarian/scripts/complete_recall.py"),
             "--input", str(man_p), "--output", str(out_p)],
            capture_output=True, text=True, timeout=180, cwd=str(REPO))
        if proc.returncode != 0:
            return False, f"rc={proc.returncode} {proc.stderr[:150]}", ""
        o = json.loads(out_p.read_text(encoding="utf-8"))
        blob = json.dumps(o, ensure_ascii=False)
        return "zephyr" in blob.lower() and "42" in blob, "complete_recall 保留 Zephyr 事实", blob[:150]
    ok_all &= step(mc, "librarian complete_recall(保真)", s_librarian, timeout=200)

    def s_dup(m):
        r = m.call("kb_find_duplicates", {"kb_id": ctx["kb_a"]}, timeout=300)
        groups = r.get("duplicate_groups") or []
        total = r.get("total_duplicate_groups", len(groups))
        near = [g for g in groups if g.get("type") == "near"]
        sims = [g.get("similarity") for g in near]
        okflag = total >= 1 and len(near) >= 1
        return okflag, f"total={total} near={len(near)} sims={sims} (≥0.90 阈值)", \
            json.dumps(groups[:1], ensure_ascii=False)[:150]
    ok_all &= step(mc, "kb_find_duplicates(organize 检出近重复)", s_dup, timeout=320)

    def s_rename(m):
        r = m.call("kb_doc_update_meta",
                   {"kb_id": ctx["kb_a"], "doc_path": "zephyr7-spec-copy.md",
                    "name": "zephyr7-spec-v2.md"}, timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_doc_update_meta(manage 改名)", s_rename, timeout=70)

    def s_move(m):
        # 契约: doc_path = "kb_path/doc.md" 相对路径(kb_name 前缀, 非 UUID)
        r = m.call("kb_doc_move",
                   {"doc_path": f"{KB_A}/zephyr7-spec-v2.md",
                    "target_kb_id": ctx["kb_b"]}, timeout=120)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_doc_move(A→B)", s_move, timeout=130)

    def s_move_verify(m):
        na = len(docs_of(m, ctx["kb_a"]))
        nb = len(docs_of(m, ctx["kb_b"]))
        return na == 2 and nb == 1, f"A={na} B={nb}", (na, nb)
    ok_all &= step(mc, "move 后计数 A=2 B=1", s_move_verify, timeout=70)

    def s_stats(m):
        r = m.call("kb_search_stats", {}, timeout=60)
        cols = ((r.get("stats") or {}).get("collections")) or []
        okc = isinstance(cols, list) and len(cols) >= 2
        return okc, f"collections={len(cols)}", str(r)[:120]
    ok_all &= step(mc, "kb_search_stats(verify 向量面)", s_stats, timeout=70)

    def s_graph_build(m):
        r = m.call("kb_graph_build", {"kb_id": ctx["kb_a"]}, timeout=180)
        tid = r.get("task_id", "")
        if tid:
            fin = poll_task(m, tid, 120)
            return str(fin.get("status", "")).lower() in ("done", "completed", "success", "finished"), \
                f"task→{fin.get('status')}", fin
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_graph_build(轮询至完成)", s_graph_build, timeout=320)

    def s_graph_search(m):
        r = m.call("kb_graph_search", {"keyword": "zephyr", "limit": 10}, timeout=60)
        blob = json.dumps(r, ensure_ascii=False)
        return "zephyr" in blob.lower(), "图谱含 zephyr 节点", blob[:150]
    ok_all &= step(mc, "kb_graph_search(zephyr)", s_graph_search, timeout=70)

    def s_graph_central(m):
        r = m.call("kb_graph_central_documents", {"kb_id": ctx["kb_a"]}, timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "kb_graph_central_documents", s_graph_central, timeout=70)

    # experience lifecycle
    def s_exp_create(m):
        r = m.call("experience_create",
                   {"kb_id": ctx["kb_a"], "title": "[SkillAudit] near-duplicate detection",
                    "scenario": "fulltest sandbox ingest",
                    "problem": "copy of spec doc could pollute retrieval",
                    "solution": "kb_find_duplicates flags near-duplicates before indexing",
                    "key_lessons": ["always run duplicate audit after bulk ingest"],
                    "tags": ["skillaudit"]}, timeout=60)
        exp = r.get("experience") or {}
        ctx["exp_id"] = exp.get("id", "")
        return bool(r.get("success")) and bool(ctx["exp_id"]), f"exp_id={ctx['exp_id']}", r
    ok_all &= step(mc, "experience_create", s_exp_create, timeout=70)

    def s_exp_search(m):
        r = m.call("experience_search_global",
                   {"query": "near-duplicate detection audit", "top_k": 3}, timeout=60)
        blob = json.dumps(r, ensure_ascii=False)
        return "SkillAudit" in blob or "duplicate" in blob.lower(), "经验检索命中", blob[:150]
    ok_all &= step(mc, "experience_search_global(命中)", s_exp_search, timeout=70)

    def s_exp_update(m):
        # severity 枚举: critical/important/normal/tip (backend ExperienceSeverity)
        r = m.call("experience_update",
                   {"kb_id": ctx["kb_a"], "exp_id": ctx["exp_id"], "severity": "important"},
                   timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "experience_update(exp_id+合法枚举)", s_exp_update, timeout=70)

    def s_exp_readback(m):
        r = m.call("experience_list", {"kb_id": ctx["kb_a"]}, timeout=60)
        blob = json.dumps(r, ensure_ascii=False)
        return str(ctx["exp_id"]) in blob and "important" in blob, "update 落盘可见", blob[:150]
    ok_all &= step(mc, "experience_list(回读校验)", s_exp_readback, timeout=70)

    def s_exp_del(m):
        r = m.call("experience_delete",
                   {"kb_id": ctx["kb_a"], "exp_id": ctx["exp_id"]}, timeout=60)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "experience_delete(清理)", s_exp_del, timeout=70)

    # ── soul 生命周期 ─────────────────────────────────────────────────────
    print(f"[fulltest] Phase SOUL ({SOUL})", flush=True)

    def s_soul_init(m):
        r = m.call("soul_init",
                   {"soul_name": SOUL, "kb_scope": [ctx["kb_a"]],
                    "domain_labels": ["skill-audit"],
                    "supported_task_types": ["qa"]}, timeout=90)
        ctx["soul_kb"] = r.get("kb_id") or SOUL
        ctx["init_task"] = r.get("task_id", "")
        ctx["profile_pending"] = bool(r.get("profile_pending"))
        return bool(r.get("success", True)) and bool(ctx["init_task"]), \
            f"task_id={ctx['init_task']} profile_pending={ctx['profile_pending']}", r
    ok_all &= step(mc, "soul_init(异步 task_id)", s_soul_init, timeout=100)

    def s_init_poll(m):
        fin = poll_task(m, ctx["init_task"], 180)
        return str(fin.get("status", "")).lower() in ("done", "completed", "success", "finished"), \
            f"status={fin.get('status')}", fin
    ok_all &= step(mc, "kb_task_status(init 轮询→done)", s_init_poll, timeout=200)

    def s_soul_status(m):
        r = m.call("soul_status", {"soul_kb_id": ctx.get("soul_kb", SOUL)}, timeout=60)
        ctx["cost"] = r.get("estimated_cost_usd", 0)
        return bool(r), f"cost≈{ctx['cost']}", json.dumps(r, ensure_ascii=False)[:150]
    ok_all &= step(mc, "soul_status(预算面)", s_soul_status, timeout=70)

    def s_qdcvr(m):
        r = m.call("soul_qdcvr_ask",
                   {"query": "What is the coolant capacity of the Zephyr-7?",
                    "soul_kb_id": ctx.get("soul_kb", SOUL), "top_k": 3,
                    "async_mode": True}, timeout=120)
        tid = r.get("task_id", "")
        if not tid:
            return False, f"no task_id: {str(r)[:120]}", r
        fin = poll_task(m, tid, 300)
        res = task_result(fin)
        ans = str(res.get("answer", ""))
        cits = res.get("citations") or []
        ctx["pas"] = res.get("pas_score")
        okans = ("42" in ans) and bool(cits) and res.get("success", True) is not False
        return okans, f"pas={ctx['pas']} citations={len(cits)} answer[:60]={ans[:60]!r}", \
            json.dumps(res, ensure_ascii=False)[:300]
    ok_all &= step(mc, "soul_qdcvr_ask(检索+人格作答 42+citations)", s_qdcvr, timeout=420)

    def s_route(m):
        r = m.call("soul_ask",
                   {"query": "How many round trips does Aurora-9 require?",
                    "task_goal": "protocol lookup", "task_type": "qa",
                    "async_mode": True}, timeout=120)
        tid = r.get("task_id", "")
        if not tid:
            return False, f"no task_id: {str(r)[:120]}", r
        fin = poll_task(m, tid, 300)
        res = task_result(fin)
        routed = str(res.get("selected_soul") or "")
        ans = str(res.get("answer", ""))
        route_reason = str(res.get("route_reason") or "")
        cits = res.get("citations") or []
        if routed:
            # 形态1: 高置信路由 → 应命中 Aurora-9 事实
            okans = ("3" in ans) and bool(routed)
            why = f"routed→{routed} answer[:60]={ans[:60]!r}"
        elif route_reason and not cits:
            # 形态2: 人格库拥挤时低置信→结构化拒答(给出理由/零引用/不编造) — 亦合规
            okans = ("置信" in route_reason) or ("匹配" in route_reason)
            why = f"低置信诚实拒答 route_reason={route_reason!r} (规范: 不强选)"
        else:
            okans = False
            why = f"既未路由也无拒答理由: {json.dumps(res, ensure_ascii=False)[:120]}"
        return okans, why, json.dumps(res, ensure_ascii=False)[:250]
    ok_all &= step(mc, "soul_ask(自动路由或诚实拒答)", s_route, timeout=420)

    if not args.skip_train:
        def s_budget(m):
            c = float(ctx.get("cost") or 0)
            return c <= 0.15, f"estimated_cost_usd={c} (≤0.15 才训)", c
        ok_budget = step(mc, "预算 reverence 检查", s_budget, timeout=30)

        if ok_budget:
            def s_train(m):
                r = m.call("soul_train_rl",
                           {"soul_kb_id": ctx.get("soul_kb", SOUL), "rounds": 1},
                           timeout=120)
                tid = r.get("task_id", "")
                if not tid:
                    return False, f"no task_id: {str(r)[:150]}", r
                fin = poll_task(m, tid, 900, interval=10)
                res = task_result(fin)
                rounds = res.get("per_round") or []
                reward = (rounds[-1].get("reward") if rounds else None) or res.get("reward")
                okd = str(fin.get("status", "")).lower() in ("done", "completed", "success", "finished")
                return okd, f"status={fin.get('status')} reward={reward}", \
                    json.dumps(res, ensure_ascii=False)[:300]
            ok_all &= step(mc, "soul_train_rl(rounds=1)", s_train, timeout=950)
        else:
            results.append({"step": "soul_train_rl", "ok": True, "ms": 0,
                            "detail": "SKIPPED: 预算超限(规则3 reverence)", "evidence": ""})
            print("  SKIP soul_train_rl — 预算超限", flush=True)
    else:
        results.append({"step": "soul_train_rl", "ok": True, "ms": 0,
                        "detail": "SKIPPED: --skip-train", "evidence": ""})

    def s_drafts(m):
        r = m.call("soul_review_drafts",
                   {"soul_kb_id": ctx.get("soul_kb", SOUL), "action": "list",
                    "draft_type": "memory"}, timeout=90)
        n = len(r.get("drafts") or [])
        return bool(r.get("success")), f"drafts={n}", str(r)[:120]
    ok_all &= step(mc, "soul_review_drafts(list)", s_drafts, timeout=100)

    def s_ckpt(m):
        r = m.call("soul_checkpoint", {"soul_kb_id": ctx.get("soul_kb", SOUL)}, timeout=90)
        ctx["ckpt_id"] = r.get("checkpoint_id", "")
        return bool(r.get("success")) and bool(ctx["ckpt_id"]), f"ckpt={ctx['ckpt_id']}", r
    ok_all &= step(mc, "soul_checkpoint", s_ckpt, timeout=100)

    def s_rollback(m):
        r = m.call("soul_rollback",
                   {"soul_kb_id": ctx.get("soul_kb", SOUL),
                    "checkpoint_id": ctx.get("ckpt_id", "")}, timeout=120)
        return bool(r.get("success")), str(r)[:100], r
    ok_all &= step(mc, "soul_rollback(回滚到检查点)", s_rollback, timeout=130)

    def s_reflect(m):
        r = m.call("soul_reflect", {"soul_kb_id": ctx.get("soul_kb", SOUL)}, timeout=120)
        return bool(r.get("success")), str(r.get("report_path", ""))[:100], r
    ok_all &= step(mc, "soul_reflect", s_reflect, timeout=130)

    def s_export(m):
        r = m.call("soul_export",
                   {"soul_kb_id": ctx.get("soul_kb", SOUL), "min_score": 4.9}, timeout=90)
        return bool(r.get("success")), str(r.get("export_path", ""))[:100], r
    ok_all &= step(mc, "soul_export(高分导出)", s_export, timeout=100)

    # ── 规范边界用例 ──────────────────────────────────────────────────────
    print("[fulltest] Phase SPEC 边界用例", flush=True)

    def s_edge_dup_kb(m):
        r = m.call("kb_create", {"name": KB_A}, timeout=30)
        rejected = r.get("success") is False
        return rejected, "重名 KB 被结构化拒绝 ✓" if rejected else f"未拒绝: {str(r)[:100]}", str(r)[:120]
    ok_all &= step(mc, "边界: kb_create 重名拒绝(fail-closed)", s_edge_dup_kb, timeout=40)

    def s_edge_soul_reserved(m):
        r = m.call("soul_init", {"soul_name": "con", "kb_scope": []}, timeout=30)
        rejected = r.get("success") is False
        return rejected, "Windows 保留名被结构化拒绝 ✓" if rejected else f"未拒绝: {str(r)[:80]}", str(r)[:120]
    ok_all &= step(mc, "边界: soul_init 保留名拒绝", s_edge_soul_reserved, timeout=40)

    def s_edge_empty_query(m):
        r = m.call("kb_search_vector", {"query": "", "top_k": 3}, timeout=60)
        rejected = r.get("success") is False
        return rejected, "空查询被拒 ✓" if rejected else f"未拒绝: {str(r)[:80]}", str(r)[:120]
    ok_all &= step(mc, "边界: 空查询拒绝(新门禁)", s_edge_empty_query, timeout=70)

    def s_edge_md_parse(m):
        r = m.call("parse_doc",
                   {"file_path": str(tmp / "zephyr7-spec.md"), "use_ocr": False}, timeout=60)
        rejected = r.get("success") is False
        return rejected, ".md 被 parse_doc 显式拒绝 ✓" if rejected else f"未拒绝: {str(r)[:80]}", str(r)[:150]
    ok_all &= step(mc, "边界: parse_doc .md 显式拒绝(新门禁)", s_edge_md_parse, timeout=70)

    # ── 清理 ──────────────────────────────────────────────────────────────
    print("[fulltest] Phase CLEANUP", flush=True)

    def s_soul_del(m):
        r = m.call("soul_delete", {"soul_kb_id": ctx.get("soul_kb", SOUL)}, timeout=120)
        lst = str(m.call("soul_list", {}, timeout=60))
        gone = SOUL not in lst
        return gone and r.get("success") is not False, f"deleted, soul_list 无残留={gone}", r
    ok_all &= step(mc, "soul_delete(清理+验证)", s_soul_del, timeout=130)

    def s_kb_del(m):
        out = []
        for kb in (ctx.get("kb_a"), ctx.get("kb_b")):
            try:
                names = [d.get("name") for d in docs_of(m, kb) if d.get("name")]
                if names:
                    m.call("kb_doc_batch_delete", {"kb_id": kb, "doc_paths": names}, timeout=120)
                m.call("kb_delete", {"kb_id": kb}, timeout=60)
                out.append(f"{kb}=deleted")
            except Exception as e:  # noqa: BLE001
                out.append(f"{kb}={type(e).__name__}:{str(e)[:60]}")
        lst = str(m.call("kb_list", {"lightweight": True}, timeout=60))
        gone = KB_A not in lst and KB_B not in lst
        return gone, " ".join(out) + f" 残留={not gone}", out
    ok_all &= step(mc, "kb_delete(A/B 清理+验证)", s_kb_del, timeout=300)

    n_fail = sum(1 for r in results if not r["ok"])
    L = ["# Skill 全量实测报告 v2(120) — 沙盒生命周期 + soul 全链路", "",
         f"- 时间: {TS} · 步骤: {len(results)} · FAIL: **{n_fail}**",
         f"- 沙盒: KB `{KB_A}`/`{KB_B}` + 人格 `{SOUL}`(全部已清理)",
         "- 本轮包含修复后复测: .md 命名/空查询门禁/parse_doc 白名单", "",
         "| # | 步骤 | 结果 | 耗时ms | 明细 |", "|---|---|:--:|---:|---|"]
    for i, r in enumerate(results, 1):
        L.append(f"| {i} | {r['step']} | {'✅' if r['ok'] else '❌'} | {r['ms']} | {r['detail'][:160]} |")
    (outdir / "REPORT.md").write_text("\n".join(L), encoding="utf-8")
    (outdir / "steps.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[fulltest] {len(results)} 步 · FAIL={n_fail} → {outdir/'REPORT.md'}", flush=True)
    mc.close()
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
