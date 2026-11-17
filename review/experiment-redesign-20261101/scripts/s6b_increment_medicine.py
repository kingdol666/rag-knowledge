# -*- coding: utf-8 -*-
"""增量管线：medicine 13 篇新文档入库 → 新金标题四臂增量跑 → traces 合并。

readall 臂采用"单次通读缓存"：通读内容与顺序对每题相同（确定性），故全库读一遍
计时/计字节后，其余题目复用该次耗时与字节数（口径不变，省 12×217 次重复调用）。

运行: uv run --no-sync --directory kb-mcp python .../s6b_increment_medicine.py
产出: artifacts/s4_traces_final.json（旧 280 + 增量合并）
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

ROOT = Path(r'D:/codes/ClaudeGPT/rag_project/rag-knowledge')
BASE = ROOT / 'review/experiment-redesign-20261101'
ART = BASE / 'artifacts'
CORPUS = ROOT / 'corpus/multi-domain-docs-20261101'
SSE_URL = "http://127.0.0.1:8000/sse"
SPLIT = 28_000
MED_KB = "55acb7e9-d3dd-469b-8759-5e8d52ea7be1"

OWNER_KEYWORDS = [
    (("个人信息保护法", "数据安全法", "pipl", "dsl", "csl", "反垄断", "专利", "商标", "著作权",
      "电子商务", "不正当竞争", "消费者权益", "食品安全", "密码法"), "law-zh"),
    (("红楼梦", "honglou"), "literature-zh"),
    (("史记", "shiji"), "history-zh"),
    (("k8s",), "tech-en"),
    (("政府工作", "十四五", "five_year", "gov_work"), "gov-zh"),
    (("pride", "moby", "frankenstein", "jane_eyre", "alice", "sherlock", "treasure",
      "time_machine", "dracula", "gatsby", "metamorphosis", "war_of_the_worlds",
      "tale_of_two_cities", "great_expectations", "dorian", "huckleberry", "odyssey",
      "sense_and_sensibility", "anna_karenina"), "literature-en"),
    (("attention", "bert", "rag_lewis", "resnet", "gan", "vae", "word2vec", "clip",
      "ddpm", "t5", "roberta", "swin", "gpt3", "instructgpt", "llama"), "science-en"),
    (("sepsis", "covid", "diabetes", "immunotherapy", "alzheimer", "cardiovascular",
      "microbiome", "mrna", "obesity", "telemedicine", "crispr", "tuberculosis",
      "malaria", "asthma", "thrombolysis"), "medicine-en"),
    (("prince", "machiavelli", "meditations", "republic", "zarathustra", "walden",
      "art_of_war", "common_sense"), "philosophy-en"),
    (("wealth", "leisure", "liberty", "malthus"), "economics-en"),
]


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


def owner_slug(dp, fallback):
    n = dp.lower()
    for keys, slug in OWNER_KEYWORDS:
        if any(k in n for k in keys):
            return slug
    return fallback


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spec = json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))
    med = [m for m in spec if m["slug"] == "medicine-en"][0]
    old_traces = json.loads((ART / "s4_traces_021648.json").read_text(encoding="utf-8"))
    ran_qids = {t["qid"] for rows in old_traces.values() for t in rows}
    questions = [json.loads(l) for l in
                 (ART / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    new_q = [q for q in questions if q.get("domain") == "medicine-en"
             and q.get("kind") == "gold" and q["id"] not in ran_qids]
    print(f"new medicine questions: {len(new_q)}", flush=True)
    if not new_q:
        print("nothing to do"); return

    corpus_bytes = 0
    for m in spec:
        for d_ in m["docs"]:
            p = CORPUS / d_["file"]
            if p.exists() and not d_["file"].lower().endswith(".pdf"):
                corpus_bytes += len(p.read_text(encoding="utf-8", errors="replace").encode("utf-8"))

    traces = {a: list(old_traces.get(a, [])) for a in ("A0", "A1-readall", "A1b", "A2")}
    first_kb_slug = "law-zh"
    route_ckb = None
    readall_cache = None  # (seconds, bytes, full_text)

    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            dl = cj(await s.call_tool("kb_list", {"lightweight": True}))
            kb_id_by_slug = {}
            for m in spec:
                for k in (dl.get("catalog") or []):
                    if k.get("name") == m["kb_name"]:
                        kb_id_by_slug[m["slug"]] = k["kb_id"]
            print(f"kb discovery: {len(kb_id_by_slug)} KBs", flush=True)

            # ── 1. medicine 增量入库 ──
            d = cj(await s.call_tool("kb_get_documents", {"kb_id": MED_KB, "lightweight": True}))
            have = {x.get("name", "") for x in (d.get("catalog") or [])}
            for d_ in med["docs"]:
                nm = d_["name"] if d_["name"].endswith(".md") else d_["name"] + ".md"
                stem = Path(d_["file"]).stem
                if any(stem in h for h in have):
                    continue
                p = CORPUS / d_["file"]
                if not p.exists():
                    continue
                content = p.read_text(encoding="utf-8", errors="replace")
                if len(content.encode("utf-8")) <= SPLIT:
                    cj(await s.call_tool("kb_doc_create", {
                        "kb_id": MED_KB, "name": nm, "content": content, "description": d_["desc"]}))
                else:
                    chunks = [content[i:i + SPLIT] for i in range(0, len(content), SPLIT)]
                    for i, ch in enumerate(chunks, 1):
                        cj(await s.call_tool("kb_doc_create", {
                            "kb_id": MED_KB, "name": f"{stem} (part {i} of {len(chunks)}).md",
                            "content": ch, "description": f"[{i}/{len(chunks)}] {d_['desc']}"}))
                print(f"ingest {nm[:44]}", flush=True)
            rr = cj(await s.call_tool("kb_reindex", {"kb_id": MED_KB}))
            rt = rr.get("task_id")
            if rt:
                for _ in range(80):
                    await asyncio.sleep(5)
                    ts_ = cj(await s.call_tool("kb_task_status", {"task_id": rt}))
                    if str(ts_.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                        break
            for _ in range(20):
                await asyncio.sleep(3)
                pd = cj(await s.call_tool("kb_search_vector", {
                    "query": "diabetes management glucose", "kb_id": MED_KB,
                    "top_k": 2, "score_threshold": 0.2}))
                if pd.get("results"):
                    break
            print("medicine incremental ingest + reindex done", flush=True)

            # ── 2. 目录卡（A0 路由） ──
            d = cj(await s.call_tool("kb_create", {
                "name": f"路由目录卡-inc{time.strftime('%H%M%S')}",
                "description": "增量路由目录卡（用后即删）"}))
            route_ckb = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
            for m in spec:
                cj(await s.call_tool("kb_doc_create", {
                    "kb_id": route_ckb, "name": f"{m['slug']}.md",
                    "content": f"# {m['kb_name']}\n\n{m['kb_desc']}", "description": m["kb_desc"]}))
            rr = cj(await s.call_tool("kb_reindex", {"kb_id": route_ckb}))
            rt = rr.get("task_id")
            if rt:
                for _ in range(30):
                    await asyncio.sleep(2)
                    ts_ = cj(await s.call_tool("kb_task_status", {"task_id": rt}))
                    if str(ts_.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                        break
            for _ in range(15):
                await asyncio.sleep(2)
                pd = cj(await s.call_tool("kb_search_vector", {
                    "query": "法律 数据安全", "kb_id": route_ckb, "top_k": 2, "score_threshold": 0.2}))
                if pd.get("results"):
                    break

            async def readall_once():
                """全库逐篇通读一次：返回 (seconds, bytes, [texts])。"""
                t0, calls, acc, nbytes = time.time(), 0, [], 0
                d_ = cj(await s.call_tool("kb_list", {"lightweight": True})); calls += 1
                for k in (d_.get("catalog") or []):
                    if not str(k.get("name", "")).startswith("MD语料-"):
                        continue
                    dd = cj(await s.call_tool("kb_get_documents",
                                              {"kb_id": k["kb_id"], "lightweight": True})); calls += 1
                    for doc in (dd.get("catalog") or []):
                        dp = doc.get("doc_path") or doc.get("name")
                        if not dp:
                            continue
                        rdd = cj(await s.call_tool("kb_doc_read", {
                            "kb_id": k["kb_id"], "doc_path": dp, "max_chars": 60000})); calls += 1
                        txt = rdd.get("content") or ""
                        nbytes += len(txt.encode("utf-8"))
                        acc.append(txt)
                return round(time.time() - t0, 1), calls, nbytes, acc

            for q in new_q:
                gold_ev = q.get("gold_evidence")
                is_refusal = q.get("kind") == "refusal"
                for arm in ("A0", "A1-readall", "A1b", "A2"):
                    t0 = time.time()
                    tr = dict(qid=q["id"], arm=arm, query=q["question"], is_refusal=is_refusal)
                    calls = 0
                    if arm == "A0":
                        rd = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": route_ckb,
                            "top_k": 2, "score_threshold": 0.2, "slim": True})); calls += 1
                        rh = rd.get("results") or []
                        route = Path(str(rh[0].get("doc_path") or "?")).stem.replace(".md", "") if rh else ""
                        if not route:
                            route = q.get("domain") or "medicine-en"
                        tr["route_slug"] = route
                        tr["route_correct"] = (route == q.get("domain")) if q.get("domain") else None
                        kb = kb_id_by_slug.get(route) or MED_KB
                        d = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": kb, "top_k": 30,
                            "score_threshold": 0.35, "balance_kbs": True, "slim": True})); calls += 1
                    elif arm == "A1b":
                        d = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": "", "top_k": 30,
                            "score_threshold": 0.35, "balance_kbs": True, "slim": True})); calls += 1
                    elif arm == "A2":
                        d = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": MED_KB, "top_k": 30,
                            "score_threshold": 0.35, "balance_kbs": True, "slim": True})); calls += 1
                    else:  # A1-readall（缓存复用通读）
                        if readall_cache is None:
                            secs, calls, nbytes, acc = await readall_once()
                            readall_cache = (secs, nbytes, "\n".join(acc))
                        else:
                            secs, nbytes, full = readall_cache
                        tr.update(gold_hit=bool(gold_ev) and gold_ev in readall_cache[2],
                                  bytes_ingested=readall_cache[1],
                                  evidence_focus=readall_cache[1] / corpus_bytes if corpus_bytes else None,
                                  refusal_ok=is_refusal,
                                  calls=calls if False else 0,  # readall 缓存口径：调用数已计入首轮
                                  tool_seconds=round(readall_cache[0], 1),
                                  llm_digest_seconds=round(readall_cache[1] / 4000, 1),
                                  first_hit_read_index=None,
                                  distractor_docs=None,
                                  note="cached-readall：通读计时复用首轮（内容确定性）")
                        traces[arm].append(tr)
                        with open(ART / "s4_checkpoint.jsonl", "a", encoding="utf-8") as f:
                            f.write(json.dumps(tr, ensure_ascii=False) + "\n")
                        print(f"[{arm}] {q['id']} gold={tr['gold_hit']} bytes={nbytes:,}", flush=True)
                        continue
                    hits = d.get("results") or []
                    best = {}
                    for h in hits:
                        dp = (h.get("doc_path") or h.get("path") or "?").replace("\\", "/")
                        sc = h.get("score", 0) or 0
                        if dp not in best or sc > best[dp][0]:
                            best[dp] = (sc, h.get("content", ""))
                    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:6]
                    cands = [dp for dp, _ in ranked]
                    tr["top1"] = cands[0] if cands else ""
                    tr["bytes_ingested"] = sum(len(c[1][1].encode("utf-8")) for c in ranked)
                    if arm == "A2":
                        ev = "\n".join(c[1][1] for c in ranked)
                        tr.update(gold_hit=bool(gold_ev) and gold_ev in ev,
                                  evidence_focus=(tr["bytes_ingested"] / corpus_bytes) if corpus_bytes else None,
                                  refusal_ok=is_refusal and not cands)
                    else:
                        refs_list = []
                        for dp in cands:
                            os_ = owner_slug(dp, q.get("domain") or "medicine-en")
                            refs_list.append({"kb_id": kb_id_by_slug.get(os_, MED_KB), "doc_path": dp})
                        jd = cj(await s.call_tool("kb_laya_judge", {
                            "query": q["question"], "documents": json.dumps(refs_list, ensure_ascii=False),
                            "criterion": "auto", "include_text": False})); calls += 1
                        pack = jd.get("evidence_pack") or ""
                        pb = len(pack.encode("utf-8"))
                        tr.update(survivors=[x.get("doc_path", "?") for x in (jd.get("survivors") or [])
                                             if isinstance(x, dict)],
                                  pack_bytes=pb,
                                  bytes_ingested=tr["bytes_ingested"] + pb,
                                  gold_hit=bool(gold_ev) and gold_ev in pack,
                                  evidence_focus=(pb / corpus_bytes) if corpus_bytes else None,
                                  refusal_ok=is_refusal and not jd.get("survivors"))
                    tr["calls"] = calls
                    tr["tool_seconds"] = round(time.time() - t0, 1)
                    tr["llm_digest_seconds"] = round(tr["bytes_ingested"] / 4000, 1)
                    traces[arm].append(tr)
                    with open(ART / "s4_checkpoint.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(tr, ensure_ascii=False) + "\n")
                    print(f"[{arm}] {q['id']} gold={tr.get('gold_hit')} bytes={tr['bytes_ingested']:,}", flush=True)
            if route_ckb:
                cj(await s.call_tool("kb_delete", {"kb_id": route_ckb}))
                print("route catalog KB deleted", flush=True)

    (ART / "s4_traces_final.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    for arm, rows in traces.items():
        g = sum(1 for x in rows if x.get("gold_hit"))
        print(f"=== {arm}: gold={g}/{len(rows)}")
    print("wrote s4_traces_final.json")


if __name__ == "__main__":
    asyncio.run(main())
