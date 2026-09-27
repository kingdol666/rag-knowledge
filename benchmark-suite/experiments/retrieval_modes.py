"""Three retrieval modes as first-class experiment arms (added 2026-09-27).

Modes (the ONLY variable between arms — same live library, same questions):
  A  QDCVR vector-first   knowledgebase-search/scripts/vector_jev_search.py
     wide-net recall (top_k=30) -> doc dedup -> reread -> segment -> real
     Laya/Jev verdict on EVERY segment (fail-closed) -> all yes kept.
  B  Librarian catalog lane  (ported verbatim from review/three-mode-20260926
     driver mode_b, the proven implementation)
     kb_list -> agent shelf label (L1) -> every doc description (L2) ->
     metadata trust (L3) -> budgeted reads (L4: overlap full / untrusted
     head / stem completion) -> complete_recall.run_manifest (real Laya)
     -> engine verdict is final, every yes survivor is evidence.
  C  Hybrid parallel      knowledgebase-hybrid/scripts/hybrid_search.py
     vector lane || catalog lane -> merge/dedup -> unified reread -> judge
     -> deduplicated result_list (--require-real).

Verification gates (per mode x question): process exit 0, real_engine=true,
survivors/result_list > 0, gold doc present among survivors (question's
gold_substr), latency recorded. Fail => exit code 2 upstream.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"))

SCRIPT_A = REPO / ".claude/skills/knowledgebase-search/scripts/vector_jev_search.py"
SCRIPT_C = REPO / ".claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py"


def resolve_laya_python() -> Path:
    """Interpreter that hosts the Laya engine.

    Priority: $RAG_LAYA_PYTHON -> repo backend/.venv (the MinerU env — it ships
    GPU torch 2.12.1+cu130 and, since 2026-09-27, the `laya` package) -> the
    current interpreter as fallback. The three judging scripts
    (vector_jev_search / hybrid_search / complete_recall) must run under an
    interpreter that can `import laya`; Laya auto-selects CUDA when the
    interpreter's torch has it, so pointing at backend/.venv gives GPU
    verdicts with zero code changes.
    """
    import os

    env = os.environ.get("RAG_LAYA_PYTHON", "").strip()
    if env:
        return Path(env)
    for rel in ("backend/.venv/Scripts/python.exe", "backend/.venv/bin/python"):
        cand = REPO / rel
        if cand.exists():
            return cand
    return Path(sys.executable)

QUESTIONS: dict[str, dict] = {
    "q1": {
        "qid": "q1",
        "lang": "en",
        "text": ("How does InstructDS generate high-quality query-based dialogue "
                 "summaries? (InstructDS dialogue summarization query-based "
                 "instruction tuning data synthesis)"),
        "shelf_b": ["计算机与人工智能"],          # librarian L1 agent shelf label
        "gold_substr": "instructive-dialogue-summarization",  # arXiv:2310.10981 文件名
        "gold_id": "2310.10981",
        "gold_name": "Instructive Dialogue Summarization 论文（4-part 拆分, 即 InstructDS 方法论文）",
        "baseline_20260926": {"a_s": 13.3, "b_s": 342.0, "c_s": 1152.0,
                              "b_survivors": 128, "c_verdicts": 173,
                              "note": "2026-09-26 基线：A 13.3s / B 5.7min(128段) / C 19.2min"},
    },
    "q2": {
        "qid": "q2",
        "lang": "zh→en 跨语言",
        "text": ("基于电子健康记录（EHR）数据用机器学习算法预测中风/卒中风险："
                 "关键风险因素及其影响分析 (stroke prediction electronic health "
                 "records machine learning risk factors)"),
        "shelf_b": ["生命科学与医学"],
        "gold_substr": "stroke-from-electronic-health",
        "gold_id": "1904.11280",
        "gold_name": "predicting-stroke-from-electronic-health-rec 论文",
        "baseline_20260926": {"a_s": 7.4, "b_s": 234.0, "c_s": 1818.0,
                              "b_survivors": 77, "c_verdicts": 0,
                              "note": "2026-09-26 基线：A 7.4s / B 3.9min(77段) / C 30.3min"},
    },
}


# ────────────────────────── mode A: vector-first ──────────────────────────

def run_mode_a(question: dict, out_path: Path, timeout_s: float = 1800) -> dict:
    t0 = time.time()
    proc = subprocess.run(
        [str(resolve_laya_python()), str(SCRIPT_A),
         "--query", question["text"],
         "--top-k", "30",
         "--require-real",
         "--output", str(out_path)],
        capture_output=True, text=True, timeout=timeout_s, cwd=str(REPO))
    wall = round(time.time() - t0, 1)
    res = {}
    if out_path.exists():
        try:
            res = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            return {"mode": "A", "ok": False, "error": f"output parse: {e}",
                    "rc": proc.returncode, "stderr": proc.stderr[-400:]}
    result_list = res.get("result_list") or []
    kept = sorted({str(r.get("doc_path", "")).replace("\\", "/") for r in result_list})
    return {"mode": "A", "ok": proc.returncode == 0 and bool(result_list),
            "rc": proc.returncode, "seconds": res.get("seconds", wall),
            "wall_s": wall,
            "real_engine": bool(res.get("real_engine")),
            "status": res.get("status"),
            "n_result_docs": len(kept),
            "kept_doc_paths": kept,
            "judge": res.get("judge") or {},
            "evidence_chars": len(str(res.get("evidence_pack") or "")),
            "gold_hit": question["gold_substr"] in " ".join(kept).lower(),
            "stderr_tail": proc.stderr[-200:] if proc.returncode else ""}


# ────────────────────────── mode B: librarian ──────────────────────────

def run_mode_b(question: dict, out_path: Path, budget: int = 35,
               head_budget: int = 20, timeout_s: float = 3600) -> dict:
    import re as _re

    from lib import McpClient
    import complete_recall as cr

    query = question["text"]
    keep_shelves = question["shelf_b"]
    t0 = time.time()
    mc = McpClient()
    trace: dict = {"mcp_calls": 0}
    manifest_docs: list[dict] = []
    docs_all: list[dict] = []
    try:
        kbs = (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])
        trace["l0_kbs"] = len(kbs)
        shelves = [k for k in kbs if str(k.get("name") or "") in set(keep_shelves)]
        for k in shelves:
            kb_id = k.get("kb_id") or k.get("name")
            rows = (mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                            timeout=180).get("catalog") or [])
            trace["mcp_calls"] += 1
            for d in rows:
                docs_all.append({**d, "kb_id": kb_id, "kb_name": k.get("name")})
        trace["l1_kept_shelves"] = keep_shelves
        trace["l2_docs"] = len(docs_all)

        qterms = cr._terms(query)
        sibs: dict[str, list[str]] = {}
        for d in docs_all:
            sibs.setdefault(str(d.get("kb_id")), []).append(str(d.get("description") or ""))
        for d in docs_all:
            blob = f"{d.get('name', '')} {d.get('description', '')}"
            d["overlap"] = len(qterms & cr._terms(blob)) if qterms else 0
            trusted, reasons = cr._metadata_trust(str(d.get("description") or ""),
                                                  sibs[str(d.get("kb_id"))])
            d["description_trust"] = "trusted" if trusted else "untrusted"
            d["trust_reasons"] = reasons
        trace["l3_untrusted"] = sum(1 for d in docs_all if d["description_trust"] == "untrusted")

        picked_keys: set = set()

        def full_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked_keys or len(manifest_docs) >= budget:
                return
            picked_keys.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 20000}, timeout=180)
            trace["mcp_calls"] += 1
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "full"})

        def head_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked_keys or len(manifest_docs) >= budget + head_budget:
                return
            picked_keys.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 600}, timeout=120)
            trace["mcp_calls"] += 1
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "trust_head"})

        def stem_of(p: str):
            m = _re.search(r"^(.*) \(part \d+ of \d+\)", str(p or "").replace("\\", "/"))
            return m.group(1) if m else None

        overlaps = sorted((d for d in docs_all if d["overlap"] > 0), key=lambda x: -x["overlap"])
        trace["l4_overlap_docs"] = len(overlaps)
        for d in overlaps:
            if len(manifest_docs) >= budget:
                break
            full_read(d)
        stems_picked = {stem_of(d["doc_path"]) for d in manifest_docs} - {None}
        for d in docs_all:
            if len(manifest_docs) >= budget:
                break
            if stem_of(d.get("doc_path")) in stems_picked:
                full_read(d)
        for d in docs_all:
            if d["description_trust"] == "untrusted":
                head_read(d)
        trace["l4_docs_read"] = sum(1 for d in manifest_docs if d["read_kind"] == "full")
        trace["l4_trust_heads"] = sum(1 for d in manifest_docs if d["read_kind"] == "trust_head")
        read_keys = picked_keys
        trace["unscanned_count"] = sum(
            1 for d in docs_all
            if (str(d.get("kb_id")), str(d.get("doc_path"))) not in read_keys)
    finally:
        mc.close()

    manifest = {"query": query, "engine": "laya", "threshold": 0.5,
                "max_segment_chars": 3000, "max_evidence_chars": 40_000,
                "documents": manifest_docs}
    run = cr.run_manifest(manifest)  # real Laya, fail-closed
    jev = run["jev"]
    survivors = jev.get("survivors") or []
    kept_paths = sorted({str(s.get("doc_path", "")).replace("\\", "/") for s in survivors})
    result = {"mode": "B", "ok": jev.get("real_engine") is True and bool(survivors),
              "seconds": round(time.time() - t0, 1), "wall_s": round(time.time() - t0, 1),
              "real_engine": jev.get("real_engine"),
              "status": jev.get("status"),
              "n_result_docs": len(kept_paths),
              "kept_doc_paths": kept_paths,
              "judge": {"backend": jev.get("backend"), "engine": jev.get("engine"),
                        "criterion": jev.get("criterion"),
                        "candidates": jev.get("candidate_count"),
                        "scored": jev.get("scored_count"),
                        "survivors_kept": len(survivors),
                        "errors": (jev.get("errors") or [])[:5]},
              "trace": trace,
              "evidence_chars": len(str(run.get("evidence_pack") or "")),
              "gold_hit": question["gold_substr"] in " ".join(kept_paths).lower(),
              "survivors": [{"doc_path": s.get("doc_path"), "part_index": s.get("part_index"),
                             "section_path": s.get("section_path"),
                             "start_line": s.get("start_line"), "end_line": s.get("end_line"),
                             "score": s.get("score")} for s in survivors]}
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


# ────────────────────────── mode C: hybrid ──────────────────────────

def run_mode_c(question: dict, out_path: Path, timeout_s: float = 3600) -> dict:
    """Mode C — 并行重定义(2026-09-27): A ∥ B 并行子进程 → 去重合并 →
    合并文档完整读取 → 知识增强包(最终 JSON 只含完整文档内容)。
    旧实现(vector lane ∥ catalog lane → hybrid_search.py)保留为
    RAG_MODE_C_IMPL=hybrid 可回退。检索全程在脚本/子进程内执行。"""
    import os
    script = REPO / "scripts/124_mode_c_parallel.py"
    shelves = ",".join(question.get("shelf_b") or [])
    t0 = time.time()
    if os.environ.get("RAG_MODE_C_IMPL", "").lower() == "hybrid":
        return _run_mode_c_hybrid(question, out_path, timeout_s)
    proc = subprocess.run(
        [str(resolve_laya_python()), str(script),
         "--query", question["text"], "--shelves", shelves,
         "--out", str(out_path)],
        capture_output=True, text=True, timeout=timeout_s, cwd=str(REPO))
    wall = round(time.time() - t0, 1)
    res = {}
    if out_path.exists():
        try:
            res = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            return {"mode": "C", "ok": False, "error": f"output parse: {e}",
                    "rc": proc.returncode, "stderr": proc.stderr[-400:]}
    merged = [r.get("doc_path", "") for r in (res.get("docs") or [])]
    workers = res.get("workers") or {}
    both_real = all((w or {}).get("real_engine") for w in workers.values()) if workers else False
    return {"mode": "C", "ok": proc.returncode == 0 and bool(merged),
            "rc": proc.returncode, "seconds": res.get("total_s", wall),
            "wall_s": res.get("total_s", wall),
            "real_engine": bool(both_real),
            "status": "parallel-A+B",
            "n_result_docs": len(merged),
            "kept_doc_paths": sorted(set(merged)),
            "judge": {"backend": "laya_sdk", "engine": "laya",
                      "worker_A_real": (workers.get("A") or {}).get("real_engine"),
                      "worker_B_real": (workers.get("B") or {}).get("real_engine"),
                      "scored_segments": (workers.get("A") or {}).get("scored"),
                      "errors": []},
            "merge": {"a_docs": (res.get("merge") or {}).get("a_docs"),
                      "b_docs": (res.get("merge") or {}).get("b_docs"),
                      "consensus": (res.get("merge") or {}).get("consensus"),
                      "merged_docs": (res.get("merge") or {}).get("merged"),
                      "impl": "parallel-A+B"},
            "evidence_chars": res.get("total_chars", 0),
            "gold_hit": question["gold_substr"] in " ".join(merged).lower(),
            "stderr_tail": proc.stderr[-200:] if proc.returncode else ""}


def _run_mode_c_hybrid(question: dict, out_path: Path, timeout_s: float = 5400) -> dict:
    t0 = time.time()
    proc = subprocess.run(
        [str(resolve_laya_python()), str(SCRIPT_C),
         "--query", question["text"],
         "--require-real",
         "--output", str(out_path)],
        capture_output=True, text=True, timeout=timeout_s, cwd=str(REPO))
    wall = round(time.time() - t0, 1)
    res = {}
    if out_path.exists():
        try:
            res = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            return {"mode": "C", "ok": False, "error": f"output parse: {e}",
                    "rc": proc.returncode, "stderr": proc.stderr[-400:]}
    result_list = res.get("result_list") or []
    kept = sorted({str(r.get("doc_path", "")).replace("\\", "/") for r in result_list})
    judge = res.get("judge") or {}
    merge = res.get("merge") or {}
    return {"mode": "C", "ok": proc.returncode == 0 and bool(result_list),
            "rc": proc.returncode, "seconds": res.get("seconds", wall),
            "wall_s": wall,
            "real_engine": bool(res.get("real_engine")),
            "status": res.get("status"),
            "n_result_docs": len(kept),
            "kept_doc_paths": kept,
            "judge": {"backend": judge.get("backend"), "engine": judge.get("engine"),
                      "total_segments": judge.get("total_segments"),
                      "scored_segments": judge.get("scored_segments"),
                      "errors": (judge.get("errors") or [])[:5]},
            "merge": {**{k: merge.get(k) for k in
                         ("vector_lane", "catalog_lane", "merged_docs",
                          "kept_docs", "unscanned_count")},
                      "lanes_raw": res.get("lanes"), "impl": "hybrid"},
            "evidence_chars": len(str(res.get("evidence_pack") or "")),
            "gold_hit": question["gold_substr"] in " ".join(kept).lower(),
            "stderr_tail": proc.stderr[-200:] if proc.returncode else ""}


RUNNERS = {"A": run_mode_a, "B": run_mode_b, "C": run_mode_c}


def ensure_laya_interpreter() -> None:
    """Re-exec the CURRENT process under the Laya env unless already there.

    Call at the top of any launcher that judges Laya in-process (mode B does:
    complete_recall -> jev_filter -> laya). A/C subprocesses resolve their own
    interpreter via resolve_laya_python() and do not need this. The default
    env is the repo MinerU venv (backend/.venv, GPU torch); override with
    $RAG_LAYA_PYTHON. Fixed script + argv list, never a shell.
    """
    laya_py = resolve_laya_python()
    if not laya_py.exists():
        return
    resolved = laya_py.resolve()
    if Path(sys.executable).resolve() == resolved:
        return
    if not str(resolved).startswith(str(REPO.resolve())):
        # 默认路径恒在仓库内; RAG_LAYA_PYTHON 指向仓库外属显式操作员选择, 放行前提示
        print(f"[laya-env] interpreter outside repo (explicit override): {resolved}")
    print(f"[laya-env] re-exec under Laya env: {resolved}")
    ret = subprocess.run(  # noqa: S603 — 固定脚本 + 参数列表, 不经 shell
        [str(resolved), str(Path(sys.argv[0]).resolve()), *sys.argv[1:]],
        shell=False)
    sys.exit(ret.returncode)


def verify_gate(arm_result: dict, question: dict) -> dict:
    """Hard acceptance gates — anything False means the arm run is NOT normal."""
    checks = {
        "exit_ok": arm_result.get("ok") is True,
        "real_engine": arm_result.get("real_engine") is True,
        "evidence_nonempty": (arm_result.get("n_result_docs") or 0) > 0,
        "gold_hit": arm_result.get("gold_hit") is True,
        "latency_recorded": isinstance(arm_result.get("wall_s"), (int, float)),
    }
    return {"passed": all(checks.values()), "checks": checks}
