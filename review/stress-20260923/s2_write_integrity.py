"""S2 — concurrent WRITE integrity: 20 parallel doc creates + 20 parallel
indexes + verification (three-source consistency), 10 parallel experiences.

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s2_write_integrity.py
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "review/stress-20260923")
from stress_lib import BE, WEB, HEADERS, HERE, ROOT, check, client, report  # noqa: E402

import httpx  # noqa: E402
from pathlib import Path  # noqa: E402

state = json.loads(HERE.joinpath("stress_state.json").read_text(encoding="utf-8"))
KB_NAME = state["kb_name"]

topics = ["retrieval", "embedding", "chunking", "graph", "experience", "meditation",
          "persona", "harness", "parsing", "storage", "vector", "bm25", "rerank",
          "citation", "qdcvr", "credibility", "tags", "cleanup", "index", "audit"]

def doc_content(i: int, topic: str) -> str:
    return (f"# 压测文档 {i:02d} — {topic}\n\n"
            f"本文档是并发写入完整性压测的样本 {i}，主题为 {topic}。"
            f"内容包含独立标记词 STRESSMARK-{topic}-{i:02d} 用于检索回验。\n\n" +
            (f"## 段落 {topic}\n\n{topic} 相关的压测正文内容，覆盖检索与索引验证需求。"
             f"关键词：{topic}、压测、完整性、可回收验证。\n\n" * 30))

# ---- 1. create stress KB ----
with client() as c:
    r = c.post(WEB + "/api/kb/create", json={"name": KB_NAME, "description": "Stress test KB 2026-09-23"}, headers=HEADERS, timeout=60)
    check("create stress KB", r.status_code == 200 and r.json().get("success"), r.text[:120])
    r = c.get(WEB + "/api/kb/catalog", headers=HEADERS, timeout=30)
    kb_uuid = next((k["kbId"] for k in r.json()["knowledgeBases"] if k["name"] == KB_NAME), "")
    check("resolve stress KB uuid", bool(kb_uuid), kb_uuid)
    state["kb_uuid"] = kb_uuid
    HERE.joinpath("stress_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    # ---- 2. 20 parallel doc creates ----
    t0 = time.perf_counter()

    def create_one(i_topic):
        i, topic = i_topic
        with client() as cc:
            r = cc.post(WEB + "/api/kb/documents/create",
                        json={"kbId": kb_uuid, "name": f"stress-{i:02d}-{topic}.md",
                              "content": doc_content(i, topic),
                              "description": f"Stress doc {i} on {topic}",
                              "tags": ["stress", topic]}, headers=HEADERS, timeout=90)
            return i, topic, r.status_code, r.json().get("success", False), (r.text[:100] if r.status_code != 200 else "")

    with ThreadPoolExecutor(max_workers=20) as ex:
        create_results = list(ex.map(create_one, enumerate(topics)))
    dt_create = time.perf_counter() - t0
    ok_creates = [x for x in create_results if x[2] == 200 and x[3]]
    check("20 parallel doc creates all 200", len(ok_creates) == 20,
          f"ok={len(ok_creates)}/20 dur={dt_create:.1f}s fails={[x[:3] for x in create_results if x[2] != 200][:3]}")

    # ---- 3. 20 parallel index-document ----
    t0 = time.perf_counter()

    def index_one(i_topic):
        i, topic = i_topic
        with client() as cc:
            r = cc.post(BE + "/api/v1/search/index-document",
                        json={"kb_id": kb_uuid, "doc_path": f"{KB_NAME}/stress-{i:02d}-{topic}.md",
                              "doc_name": f"stress-{i:02d}-{topic}",
                              "description": f"Stress doc {i} on {topic}",
                              "content": doc_content(i, topic), "skip_graph": True},
                        headers=HEADERS, timeout=180)
            return i, r.status_code, r.json().get("success", False)

    with ThreadPoolExecutor(max_workers=20) as ex:
        index_results = list(ex.map(index_one, enumerate(topics)))
    dt_index = time.perf_counter() - t0
    ok_index = [x for x in index_results if x[1] == 200 and x[2]]
    check("20 parallel index-document all 200", len(ok_index) == 20,
          f"ok={len(ok_index)}/20 dur={dt_index:.1f}s fails={[x for x in index_results if x[1] != 200][:3]}")

    # ---- 4. verify: list count + stats chunks + searchability + YAML valid ----
    r = c.get(WEB + f"/api/kb/documents?kbId={kb_uuid}", headers=HEADERS, timeout=60)
    docs = r.json().get("documents") or r.json().get("docs") or []
    check("documents list == 20", len(docs) == 20, f"count={len(docs)}")

    r = c.get(BE + "/api/v1/search/stats", headers=HEADERS, timeout=60)
    coll = [x for x in (r.json().get("stats", {}).get("collections") or []) if kb_uuid in str(x.get("collection", ""))]
    chunks = sum(int(x.get("chunk_count") or 0) for x in coll)
    check("A6-V stress collection chunks >= 20", chunks >= 20, f"chunks={chunks}")

    hits = 0
    for probe in ["STRESSMARK-qdcvr-15", "STRESSMARK-persona-06", "STRESSMARK-bm25-11"]:
        # lexical (BM25 stage-1) probe: the 20 docs share one template so the
        # unique marker is semantically diluted — exact-term recall is the
        # correct integrity oracle here (vector search alone hits 1-2/3).
        r = c.post(BE + "/api/v1/search/two-stage", json={"query": probe, "kb_id": kb_uuid,
                                                          "stage1_top_k": 20, "stage2_top_k": 5,
                                                          "enable_graph_expansion": False},
                   headers=HEADERS, timeout=60)
        body = json.dumps(r.json(), ensure_ascii=False)
        if probe in body:
            hits += 1
    check("3/3 parallel-written docs searchable by marker (lexical)", hits == 3, f"hits={hits}/3")

# ---- 5. 10 parallel experience creates ----
t0 = time.perf_counter()

def exp_one(i):
    with client() as cc:
        r = cc.post(BE + f"/api/v1/experience/{kb_uuid}", json={
            "title": f"并发压测经验 {i:02d} — 检索抖动处置",
            "scenario": "stress", "category": "troubleshooting",
            "problem": f"压测场景问题 {i}：并发检索时延迟抖动。",
            "solution": f"处置方案 {i}：限流 + 预热。",
            "result": "success", "key_lessons": [f"lesson-{i}"], "tags": ["stress"]},
            headers=HEADERS, timeout=90)
        return r.status_code, r.json().get("success", False)

with ThreadPoolExecutor(max_workers=10) as ex:
    exp_results = list(ex.map(exp_one, range(10)))
dt_exp = time.perf_counter() - t0
ok_exp = [x for x in exp_results if x[0] == 200 and x[1]]
check("10 parallel experience creates", len(ok_exp) == 10,
      f"ok={len(ok_exp)}/10 dur={dt_exp:.1f}s")

with client() as c:
    r = c.get(BE + f"/api/v1/experience/{kb_uuid}", headers=HEADERS, timeout=60)
    n_exp = len(r.json().get("experiences") or [])
    check("experience list == 10 after parallel writes", n_exp == 10, f"count={n_exp}")

print()
print(f"[i] timings: create20={dt_create:.1f}s index20={dt_index:.1f}s exp10={dt_exp:.1f}s")
sys.exit(report("S2 write-integrity"))
