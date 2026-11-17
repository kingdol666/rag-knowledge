# -*- coding: utf-8 -*-
"""路由诊断：同一平台下 spec 卡 vs s8 ENRICHED 卡的路由正确率对照 + 失败题逐卡分数。
判别：若 spec 卡现在仍差而 ENRICHED 卡好 → 卡文本是决定因素；
     若两者都差 → 平台向量层状态劣化（与卡文本无关）。
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
ART = ROOT / "review" / "experiment-redesign-20261101" / "artifacts"
SSE_URL = "http://127.0.0.1:8000/sse"

sys.path.insert(0, str(ROOT / "review" / "experiment-redesign-20261101" / "scripts"))
from s8_route_v2 import ENRICHED  # noqa: E402


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


async def route_acc(s, tag, cards, spec, questions, kb_slug):
    d = cj(await s.call_tool("kb_create", {
        "name": f"路由诊断-{tag}-{time.strftime('%H%M%S')}", "description": "诊断用，即删"}))
    ckb = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
    for slug, desc in cards.items():
        nm = kb_slug[slug]["kb_name"]
        cj(await s.call_tool("kb_doc_create", {
            "kb_id": ckb, "name": f"{slug}.md", "content": f"# {nm}\n\n{desc}",
            "description": desc}))
    rr = cj(await s.call_tool("kb_reindex", {"kb_id": ckb}))
    rt = rr.get("task_id")
    if rt:
        for _ in range(60):
            await asyncio.sleep(2)
            ts_ = cj(await s.call_tool("kb_task_status", {"task_id": rt}))
            if str(ts_.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                break
    # 额外等 30s 让 embedding 队列彻底追平
    await asyncio.sleep(30)
    results, samples = [], []
    for q in questions:
        rd = cj(await s.call_tool("kb_search_vector", {
            "query": q["question"], "kb_id": ckb, "top_k": 3,
            "score_threshold": 0.05, "slim": True}))
        rh = rd.get("results") or []
        route = Path(str(rh[0].get("doc_path") or "?")).stem.replace(".md", "") if rh else ""
        ok = (route == q.get("domain")) if q.get("domain") else None
        results.append(ok)
        if ok is False and len(samples) < 3:
            samples.append(dict(qid=q["id"], route=route,
                                scores=[(Path(str(h.get('doc_path') or '?')).stem,
                                         round(h.get('score', 0) or 0, 3)) for h in rh]))
    gold_rows = [r for r in results if r is not None]
    acc = sum(1 for r in gold_rows if r)
    print(f"[{tag}] route_correct {acc}/{len(gold_rows)} = {acc/max(len(gold_rows),1)*100:.0f}%", flush=True)
    for sm in samples:
        print("   misroute:", json.dumps(sm, ensure_ascii=False), flush=True)
    cj(await s.call_tool("kb_delete", {"kb_id": ckb}))
    return acc, len(gold_rows)


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spec = json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))
    kb_slug = {m["slug"]: m for m in spec}
    spec_cards = {m["slug"]: m["kb_desc"] for m in spec}
    questions = [json.loads(l) for l in
                 (ART / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = [q for q in questions if not q.get("needs_expansion")]
    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await route_acc(s, "spec", spec_cards, spec, questions, kb_slug)
            await route_acc(s, "enriched", ENRICHED, spec, questions, kb_slug)


if __name__ == "__main__":
    asyncio.run(main())
