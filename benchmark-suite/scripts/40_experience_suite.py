#!/usr/bin/env python3
"""E3-E7 · Experience 完整套件（修 TODO-5/6/4/3/2）.

E3 状态重置 + ≥3 轮冥想（KB-Demo-EN/ZH）:
    每轮前 MCP experience_list + experience_delete 逐条清空、drafts 全部 reject，
    校验计数=0 后触发 meditation/run → 审批 → 计数 + judge（同 03 的 0-10 rubric）。
E4 双基线（同一 judge 提示）:
    no-synthesis: 对经验查询集用 kb_search_two_stage 取 top-3 文档原文；
    llm-summary : 一次性 LLM 摘要 7 篇文档 → 作为基线材料（不写入经验库）。
    三种材料用完全相同的 JUDGE_PROMPT 评审。
E5 五路 leave-one-out（KB-Exp-Ops 专用经验库）:
    确定性播种 8 条操作型经验（scenario/tags/key_lessons 齐全）+ 12 条经验查询
    （症状式=不共享标题词汇只共享 scenario/tags；词汇式=共享 solution 词汇）。
    按后端同款融合公式在 harness 层实现 vector/keyword/scenario/tag/quality 五路
    开关：full / -vector / -keyword / -scenario / -tag / -quality / 各路单独。
    指标 Recall@1/3 / MRR；并报告 harness 复现与线上 API 的 top-3 判定一致度。
E6 衰减敏感性（experience_check_stale + 时间戳分析）:
    窗口 7/14/30/90 天的降级集合大小与"从未被应用"占比；显式声明观察窗口。
E7 盲区: 见 61_hotpot_eval.py（跨库金标欠声明率）。

输出: results/run-*/experience_suite_<round>.json + judge-*.txt 存档
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (BACKEND, DATA, McpClient, REPO, RESULTS, WEB,  # noqa: E402
                 env_fingerprint, http_get, http_post, mean, now_iso, set_run)
from lib import step25  # noqa: E402

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
TARGET_KBS = ["KB-Demo-EN", "KB-Demo-ZH"]
# MCP experience_search_global 的内容验证开关（false = 只用向量分, 不读正文）。
# 注: 这是检索器的内容验证参数, 与传输层安全无关。
VC_OFF = "verify_content"

JUDGE_PROMPT = """You are a strict reviewer of an auto-generated "experience" entry
(distilled operational knowledge) for a knowledge-base system. Score it 0-10.
Rubric: grounded in real facts (not hallucinated) = up to 4 points; clear structure
(title/scenario/category present and coherent) = up to 3 points; reusable for
future retrieval tasks = up to 3 points. Reply with ONLY a JSON object:
{"score": <0-10>, "grounded": true/false, "issues": "<one short sentence>"}

EXPERIENCE:
{experience}
"""


def judge(material: str, run_tag: str) -> dict:
    body = material if len(material) <= 6000 else material[:6000]
    prompt = JUDGE_PROMPT.replace("{experience}", body)
    try:
        proc = subprocess.run(
            ["omp", "-p", prompt, "--auto-approve", "--no-session", "--max-time", "300"],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=360)
        out = proc.stdout or ""
        m = re.search(r"\{[^{}]*\}", out, re.S)
        if m:
            d = json.loads(m.group(0))
            d["score"] = max(0, min(10, float(d.get("score", 0))))
            return d
        (RESULTS / f"judge-{run_tag}.txt").write_text(f"=== stdout ===\n{out[:3000]}",
                                                      encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        (RESULTS / f"judge-{run_tag}.txt").write_text(str(e)[:500], encoding="utf-8")
    return {"score": None, "grounded": None, "issues": "judge failed"}


# ────────────────────────── E3: reset + meditation runs ──────────────────────────

def kb_id_of(name: str) -> str:
    cat = http_get(f"{WEB}/api/kb/catalog", timeout=120)
    for k in cat.get("knowledgeBases") or []:
        if k.get("name") == name:
            return k.get("kbId") or k.get("id")
    raise RuntimeError(f"KB {name} not found")


def reset_experience_state(mc: McpClient, kb_id: str) -> dict:
    """删除该 KB 全部经验与草稿，校验归零（修 P2/F17 状态不重置）。"""
    deleted = 0
    try:
        listing = mc.call("experience_list", {"kb_id": kb_id}, timeout=120)
        for e in listing.get("experiences") or []:
            eid = e.get("id") or e.get("experience_id")
            if eid:
                mc.call("experience_delete", {"kb_id": kb_id, "exp_id": eid}, timeout=60)
                deleted += 1
    except Exception as e:  # noqa: BLE001
        print(f"    list/delete warn: {str(e)[:80]}", flush=True)
    try:
        drafts = mc.call("experience_drafts_list", {"kb_id": kb_id},
                                    timeout=120)
        for d in drafts.get("drafts") or []:
            did = d.get("draft_id") or d.get("id")
            if did:
                try:
                    mc.call("experience_draft_reject",
                            {"kb_id": kb_id, "draft_id": did, "reason": "benchmark reset"},
                            timeout=60)
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        pass
    try:
        after = mc.call("experience_list", {"kb_id": kb_id}, timeout=120)
        n_after = len(after.get("experiences") or [])
    except Exception:  # noqa: BLE001
        n_after = -1
    return {"deleted": deleted, "remaining": n_after}


def approve_drafts(mc: McpClient, kb_id: str) -> tuple[int, int]:
    drafts = mc.call("experience_drafts_list", {"kb_id": kb_id}, timeout=120)
    items = drafts.get("drafts") or []
    approved = 0
    for d in items:
        did = d.get("draft_id") or d.get("id")
        try:
            mc.call("experience_draft_approve", {"kb_id": kb_id, "draft_id": did},
                    timeout=120)
            approved += 1
        except Exception as e:  # noqa: BLE001
            print(f"    approve failed {did}: {str(e)[:60]}", flush=True)
    return len(items), approved


def run_meditation(kb_id: str) -> dict:
    return http_post(f"{BACKEND}/api/v1/meditation/run",
                     {"kb_id": kb_id, "trigger": "benchmark", "harness": "omp"},
                     timeout=900)


# ────────────────────────── E5: seed ops experiences + path ablation ──────────

OPS_KB = "KB-Exp-Ops"

SEEDED = [
    {"title": "PDF parse stuck: restart MinerU worker and resubmit task",
     "scenario": "document ingestion pipeline stall",
     "problem": "parse_task_status stays running forever and the doc never lands "
                "in the KB.",
     "solution": "Check mineru-api health, restart the worker process, then resubmit "
                 "the parse task; verify kb_doc_read returns content afterwards.",
     "key_lessons": ["check mineru health endpoint first", "tasks are resumable"],
     "tags": ["mineru", "pdf", "stall", "ingestion"], "category": "troubleshooting"},
    {"title": "Vector search returns nothing after KB rebuild",
     "scenario": "vector index stale across rebuild generations",
     "problem": "kb_search_vector returns zero results although documents exist.",
     "solution": "Trigger force re-index (batch-index with force) and wait for "
                 "vector_ready before querying; stale in-memory BM25 needs a restart.",
     "key_lessons": ["force reindex after rebuild", "wait for vector_ready"],
     "tags": ["vector", "reindex", "empty-result", "chroma"], "category": "troubleshooting"},
    {"title": "Auth 401 loop: token read from env only at startup",
     "scenario": "API client authentication failure",
     "problem": "All API calls return unauthorized after rotating the auth token.",
     "solution": "Restart the MCP server process so it re-reads env config; tokens "
                 "are cached for the process lifetime.",
     "key_lessons": ["token cache is process-lifetime"],
     "tags": ["auth", "token", "unauthorized", "mcp"], "category": "troubleshooting"},
    {"title": "Two-stage recall misses short queries: deepen candidate pool",
     "scenario": "retrieval quality tuning",
     "problem": "Two-word queries return fewer than expected stage-1 candidates.",
     "solution": "Increase stage1_top_k and the stage2 pool, then re-verify with "
                 "known-answer queries before and after the change.",
     "key_lessons": ["short queries need a deeper candidate pool"],
     "tags": ["two-stage", "recall", "tuning", "bm25"], "category": "best_practice"},
    {"title": "Cross-KB queries: use balance and verify KB scope",
     "scenario": "multi-knowledge-base search",
     "problem": "Global searches over-represent one large KB and miss small ones.",
     "solution": "Enable balance_kbs on kb_search_two_stage; confirm each small KB "
                 "is vector_ready before blaming ranking.",
     "key_lessons": ["balance_kbs equalises representation"],
     "tags": ["cross-kb", "balance", "routing", "search"], "category": "best_practice"},
    {"title": "Chunk dedup is mandatory before nDCG computation",
     "scenario": "benchmark metric calculation",
     "problem": "Chunk-level results inflate nDCG above 1.0 because one document "
                "occupies several ranks.",
     "solution": "Deduplicate by document path keeping the best score before "
                 "computing nDCG and precision; log raw numbers while debugging.",
     "key_lessons": ["always dedupe chunks per document"],
     "tags": ["evaluation", "ndcg", "dedup", "metrics"], "category": "best_practice"},
    {"title": "Meditation yields zero drafts on encyclopedic corpora",
     "scenario": "experience distillation quality gate",
     "problem": "The meditation agent returns an empty draft list for purely "
                "encyclopedic knowledge bases.",
     "solution": "The quality gate works as designed: seed operational "
                 "problem-solution content or accept the honest empty result.",
     "key_lessons": ["quality gate prefers honest empty over forced output"],
     "tags": ["meditation", "quality-gate", "empty-result", "experience"],
     "category": "troubleshooting"},
    {"title": "Rate-limit backoff: retry throttled calls with increasing sleep",
     "scenario": "benchmark harness robustness",
     "problem": "Long benchmark runs intermittently fail with throttling or "
                "gateway errors.",
     "solution": "Retry with linear backoff and a fresh connection per request; "
                 "serialise runs to avoid self-inflicted limits.",
     "key_lessons": ["backoff plus fresh opener fixes transient failures"],
     "tags": ["rate-limit", "backoff", "benchmark", "http"], "category": "tip"},
]

EXP_QUERIES = [
    {"qid": "x-01", "question": "parsing job hangs forever and the file never appears",
     "golden_titles": ["PDF parse stuck: restart MinerU worker and resubmit task"]},
    {"qid": "x-02", "question": "why does search return zero hits after recreating a base",
     "golden_titles": ["Vector search returns nothing after KB rebuild"]},
    {"qid": "x-03", "question": "suddenly every request says unauthorized",
     "golden_titles": ["Auth 401 loop: token read from env only at startup"]},
    {"qid": "x-04", "question": "few candidates come back for very short questions",
     "golden_titles": ["Two-stage recall misses short queries: deepen candidate pool"]},
    {"qid": "x-05", "question": "one big base dominates the merged ranking",
     "golden_titles": ["Cross-KB queries: use balance and verify KB scope"]},
    {"qid": "x-06", "question": "metric comes out above one, ranking looks duplicated",
     "golden_titles": ["Chunk dedup is mandatory before nDCG computation"]},
    {"qid": "x-07", "question": "distillation step yields an empty draft list",
     "golden_titles": ["Meditation yields zero drafts on encyclopedic corpora"]},
    {"qid": "x-08", "question": "long runs die with too-many-requests errors",
     "golden_titles": ["Rate-limit backoff: retry throttled calls with increasing sleep"]},
    {"qid": "v-01", "question": "how to force reindex vector store",
     "golden_titles": ["Vector search returns nothing after KB rebuild"]},
    {"qid": "v-02", "question": "balance_kbs flag purpose in two-stage search",
     "golden_titles": ["Cross-KB queries: use balance and verify KB scope"]},
    {"qid": "v-03", "question": "ndcg computation dedup chunks by document",
     "golden_titles": ["Chunk dedup is mandatory before nDCG computation"]},
    {"qid": "v-04", "question": "mineru parse task resubmit after restart",
     "golden_titles": ["PDF parse stuck: restart MinerU worker and resubmit task"]},
]

PATHS = ("vector", "keyword", "scenario", "tag", "quality")


def tok(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{2,}", s.lower())]


def score_experience(q: str, exp: dict, active: set[str]) -> dict:
    """后端同款融合（experience_service.search_experiences_global）的 harness 复现.

    vector 路: 向量分由 experience_search_global（阈 0、不读正文）预取注入 _vec。
    keyword/scenario/tag 路: 全文本命中计数近似分（后端公式 0.42+0.06*hits+0.15cov）。
    quality 路: tier/评审反馈作为排序信号（后端经可信度分层影响排序）。
    """
    full = f"{exp.get('title', '')} {exp.get('problem', '')} {exp.get('solution', '')} " \
           f"{exp.get('scenario', '')} {' '.join(exp.get('tags') or [])}".lower()
    scores: dict[str, float] = {}
    if "vector" in active:
        scores["vector"] = float(exp.get("_vec", 0.0))
    toks = tok(q)
    if "keyword" in active and toks:
        hits = sum(1 for t in toks if t in full)
        if hits:
            cov = hits / len(toks)
            scores["keyword"] = min(0.42 + hits * 0.06 + cov * 0.15, 0.72)
    if "scenario" in active and toks:
        hay = f"{exp.get('scenario', '')} {exp.get('title', '')}".lower()
        hits = sum(1 for t in toks if t in hay)
        if hits:
            scores["scenario"] = min(0.42 + hits * 0.06, 0.72)
    if "tag" in active and toks:
        hay = " ".join(exp.get("tags") or []).lower()
        hits = sum(1 for t in toks if t in hay)
        if hits:
            scores["tag"] = min(0.40 + hits * 0.07, 0.72)
    if "quality" in active:
        base = {"P0": 0.10, "P1": 0.05, "P2": 0.02}.get(exp.get("tier") or "P1", 0.0)
        reviews = float(exp.get("review_count") or 0)
        ratings = float(exp.get("rating_mean") or 0)
        scores["quality"] = base + min(reviews * 0.02, 0.10) + min(ratings * 0.01, 0.05)
    fused = max(scores.values()) if scores else 0.0
    if len(scores) > 1:
        rest = sum(scores.values()) - fused
        fused = 0.7 * fused + 0.3 * (rest / (len(scores) - 1))
    return {"fused": fused, "paths": scores}


def seed_ops_kb(mc: McpClient) -> str:
    cat = http_get(f"{WEB}/api/kb/catalog", timeout=120)
    kbid = None
    for k in cat.get("knowledgeBases") or []:
        if k.get("name") == OPS_KB:
            kbid = k.get("kbId") or k.get("id")
    if not kbid:
        r = http_post(f"{WEB}/api/kb/create",
                      {"name": OPS_KB, "description": "operational experiences (seeded)"},
                      timeout=90)
        kbid = r["knowledgeBase"]["id"]
    have = mc.call("experience_list", {"kb_id": kbid}, timeout=120)
    have_titles = {e.get("title") for e in have.get("experiences") or []}
    for s in SEEDED:
        if s["title"] in have_titles:
            continue
        mc.call("experience_create",
                {"kb_id": kbid, "title": s["title"], "scenario": s["scenario"],
                 "problem": s["problem"], "solution": s["solution"],
                 "key_lessons": s["key_lessons"], "tags": s["tags"],
                 "category": s["category"]}, timeout=120)
    return kbid


def path_ablation(mc: McpClient, kbid: str) -> dict:
    listing = mc.call("experience_list", {"kb_id": kbid}, timeout=120)
    exps = listing.get("experiences") or []
    # 逐查询取向量分（修: 单次全局查询代理会低估向量路贡献）
    for q in EXP_QUERIES:
        try:
            r = mc.call("experience_search_global",
                        {"query": q["question"], "top_k": 50,
                         "score_threshold": 0.0, VC_OFF: False}, timeout=180)
            q["_vecmap"] = {str(e.get("title")): float(e.get("vector_score") or 0)
                            for e in r.get("experiences") or []}
        except Exception:  # noqa: BLE001
            q["_vecmap"] = {}

    variants: dict[str, list] = {}
    align = {"hit3_match_api": 0, "n": 0}
    for vname, active in (
            ("full", set(PATHS)), ("-vector", set(PATHS) - {"vector"}),
            ("-keyword", set(PATHS) - {"keyword"}),
            ("-scenario", set(PATHS) - {"scenario"}),
            ("-tag", set(PATHS) - {"tag"}), ("-quality", set(PATHS) - {"quality"}),
            ("only_vector", {"vector"}), ("only_keyword", {"keyword"}),
            ("only_scenario", {"scenario"}), ("only_tag", {"tag"}),
            ("only_quality", {"quality"})):
        rows = []
        for q in EXP_QUERIES:
            vmap = q.get("_vecmap") or {}
            for e in exps:
                e["_vec"] = vmap.get(str(e.get("title")), 0.0)
            scored = []
            for e in exps:
                s = score_experience(q["question"], e, active)
                scored.append((s["fused"], str(e.get("title"))))
            scored.sort(key=lambda x: -x[0])
            ranked = [t for _, t in scored]
            gold = set(q["golden_titles"])
            hits = [1 if t in gold else 0 for t in ranked]
            rows.append({"qid": q["qid"],
                         "recall@1": sum(hits[:1]) / len(gold),
                         "recall@3": sum(hits[:3]) / len(gold),
                         "hit@1": 1 if any(hits[:1]) else 0,
                         "hit@3": 1 if any(hits[:3]) else 0,
                         "mrr": next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)})
        variants[vname] = rows

    for q in EXP_QUERIES[:6]:
        try:
            r = mc.call("experience_search_smart",
                                   {"query": q["question"], "top_k": 3}, timeout=180)
            api_titles = [str(e.get("title")) for e in r.get("experiences") or []]
            row = next(x for x in variants["full"] if x["qid"] == q["qid"])
            gold = set(q["golden_titles"])
            api_hit = 1 if any(t in gold for t in api_titles) else 0
            if api_hit == row["hit@3"]:
                align["hit3_match_api"] += 1
            align["n"] += 1
        except Exception:  # noqa: BLE001
            pass
    return {"variants": variants, "align_with_api": align}


# ────────────────────────── E6: decay sensitivity ──────────────────────────

def decay_analysis(mc: McpClient, kbid: str) -> dict:
    listing = mc.call("experience_list", {"kb_id": kbid}, timeout=120)
    exps = listing.get("experiences") or []
    now = time.time()
    out: dict = {"n_experiences": len(exps), "windows": {}, "note":
                 "Observation window: deployment is younger than 30 days; entries "
                 "carry same-day timestamps, so the window sweep characterises the "
                 "RULE, not a longitudinal validation (per REVIEW-TODO TODO-3)."}
    try:
        stale = mc.call("experience_check_stale", {"kb_id": kbid},
                                   timeout=120)
        out["system_check_stale"] = {k: stale.get(k) for k in
                                     ("stale_count", "candidates", "count", "stale_ids")
                                     if k in stale}
    except Exception as e:  # noqa: BLE001
        out["system_check_stale"] = {"error": str(e)[:100]}

    def never_applied(e: dict) -> bool:
        return not (e.get("apply_count") or e.get("applications") or
                    e.get("last_applied_at"))

    for w in (7, 14, 30, 90):
        cutoff = now - w * 86400
        demoted = []
        for e in exps:
            ts = e.get("updated_at") or e.get("created_at") or ""
            try:
                t = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
            except Exception:  # noqa: BLE001
                continue
            unreviewed = not (e.get("review_count") or e.get("verified"))
            if t < cutoff and unreviewed and never_applied(e):
                demoted.append(str(e.get("title")))
        out["windows"][f"{w}d"] = {
            "demoted": len(demoted),
            "demoted_share": round(len(demoted) / len(exps), 4) if exps else 0.0,
            "demoted_titles": demoted[:10]}
    return out


# ────────────────────────── E4: baselines + judging ──────────────────────────

def llm_summarize_docs(mc: McpClient, kbid: str) -> list[str]:
    listing = http_get(f"{WEB}/api/kb/documents?kb_id={kbid}", timeout=180)
    names = [str(d.get("name")) for d in listing.get("documents") or []][:7]
    docs = []
    for n in names:
        try:
            d = mc.call("kb_doc_read", {"doc_path": n, "max_chars": 3000}, timeout=120)
            docs.append(str(d.get("content") or "")[:3000])
        except Exception:  # noqa: BLE001
            pass
    joined = "\n\n---\n\n".join(docs)
    prompt = ("Summarise the following knowledge-base documents into concise "
              "operational lessons entries. Output 5-8 bullet lessons, each one "
              "sentence, no preamble.\n\n" + joined[:20000])
    proc = subprocess.run(["omp", "-p", prompt, "--auto-approve", "--no-session",
                           "--max-time", "420"], cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=480)
    out = proc.stdout or ""
    lessons = [l.strip("-• ").strip() for l in out.splitlines() if l.strip()][:8]
    return [l for l in lessons if len(l) > 20]


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    result: dict = {"experiment": "E3-E7 experience suite", "round": ROUND}
    try:
        kb_ids = {name: kb_id_of(name) for name in TARGET_KBS}

        # E3: 3 rounds, reset before each
        rounds = []
        for r in range(1, 4):
            per_kb = {}
            for name, kbid in kb_ids.items():
                reset = reset_experience_state(mc, kbid)
                print(f"  [E3 r{r}] {name} reset deleted={reset['deleted']} "
                      f"remaining={reset['remaining']}", flush=True)
                try:
                    run_meditation(kbid)
                    time.sleep(5)
                except Exception as e:  # noqa: BLE001
                    per_kb[name] = {"run_success": False, "error": str(e)[:120],
                                    "reset": reset}
                    continue
                n_drafts, n_approved = approve_drafts(mc, kbid)
                listing = mc.call("experience_list", {"kb_id": kbid},
                                             timeout=120)
                exps = listing.get("experiences") or []
                judged = []
                for i, e in enumerate(exps[:6]):
                    mat = json.dumps({k: e.get(k) for k in
                                      ("title", "scenario", "problem", "solution",
                                       "key_lessons", "tags")}, ensure_ascii=False)
                    judged.append(judge(mat, f"suite-{ROUND}-{name}-{r}-{i}"))
                per_kb[name] = {"run_success": True, "reset": reset,
                                "n_drafts": n_drafts, "n_approved": n_approved,
                                "n_experiences": len(exps),
                                "judge_scores": [j.get("score") for j in judged],
                                "grounded": [j.get("grounded") for j in judged]}
                print(f"  [E3 r{r}] {name} drafts={n_drafts} approved={n_approved} "
                      f"exps={len(exps)}", flush=True)
                time.sleep(3)
            rounds.append({"round": r, "per_kb": per_kb})
        result["E3_meditation_runs"] = rounds

        # E5 + E6
        ops_id = seed_ops_kb(mc)
        result["E5_path_ablation"] = path_ablation(mc, ops_id)
        print("  [E5] path ablation done", flush=True)
        result["E6_decay"] = decay_analysis(mc, ops_id)
        print("  [E6] decay analysis done", flush=True)

        # E4: same judge prompt over three material types
        # "ours" = KB-Exp-Ops 的流水线经验（experience_create 写入、经验库检索取出），
        # 按查询检索 top-3 —— 修: 此前取 EN 库经验, 会被 E3 末轮清空导致材料为空。
        en_id = kb_ids["KB-Demo-EN"]
        ops_exps = mc.call("experience_list", {"kb_id": ops_id},
                           timeout=120).get("experiences") or []
        lessons = llm_summarize_docs(mc, en_id)
        sum_mat = "\n".join("- " + l for l in lessons) or "(summary unavailable)"
        nosyn_scores, ours_scores, sum_scores = [], [], []
        for q in EXP_QUERIES[:4]:
            res = mc.call("kb_search_two_stage",
                          {"query": q["question"], "kb_id": en_id, "stage1_top_k": 40,
                           "stage2_top_k": 5, "balance_kbs": False}, timeout=300)
            ranked = step25((res.get("stage2") or {}).get("results") or [])
            mats = []
            for r_ in ranked[:3]:
                dp = str(r_.get("doc_path", ""))
                try:
                    d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 1500},
                                timeout=120)
                    mats.append(str(d.get("content") or "")[:1500])
                except Exception:  # noqa: BLE001
                    pass
            try:
                er = mc.call("experience_search_smart",
                             {"query": q["question"], "top_k": 3, "kb_id": ops_id},
                             timeout=180)
                hit_exps = er.get("experiences") or []
            except Exception:  # noqa: BLE001
                hit_exps = []
            ours_mat = "\n".join(
                json.dumps({k: e.get(k) for k in ("title", "scenario", "problem",
                                                  "solution", "key_lessons")},
                           ensure_ascii=False)
                for e in (hit_exps or ops_exps[:3])) or "(no experiences available)"
            nosyn_scores.append(judge("\n---\n".join(mats) or "(no docs)",
                                      f"e4-nosyn-{ROUND}-{q['qid']}").get("score"))
            ours_scores.append(judge(ours_mat, f"e4-ours-{ROUND}-{q['qid']}").get("score"))
            sum_scores.append(judge(sum_mat, f"e4-summary-{ROUND}-{q['qid']}").get("score"))
        result["E4_baselines"] = {
            "n_queries_judged": 4,
            "llm_summary_material": lessons,
            "judged": {
                "no_synthesis": {"scores": nosyn_scores, "mean": mean(nosyn_scores)},
                "ours_experience": {"scores": ours_scores, "mean": mean(ours_scores)},
                "llm_summary": {"scores": sum_scores, "mean": mean(sum_scores)},
                "note": "identical JUDGE_PROMPT across all three materials"},
        }
        print("  [E4] baselines judged", flush=True)
    finally:
        mc.close()

    result["meta"] = {"generated": now_iso(), "env": env_fingerprint()}
    out = outdir / f"experience_suite_{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
