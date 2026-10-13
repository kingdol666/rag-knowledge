#!/usr/bin/env python3
"""Verify the ladder navigation fix (budget guard + pagination + groups + parent drill).
Run from repo root: python tmp/verify_ladder.py"""
import json
import subprocess
import sys

REPO = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge"
KB_CS = "b1199132-e4d4-4305-8c2e-82dc1753b0ba"  # 计算机与人工智能, 131 docs
BUDGET = 28000
results = []


def mcp(tool, payload, timeout=120):
    r = subprocess.run([sys.executable, "scripts/mcp_call.py", tool, json.dumps(payload, ensure_ascii=False), "--raw"],
                       capture_output=True, text=True, encoding="utf-8", cwd=REPO, timeout=timeout)
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        raise RuntimeError(f"{tool} rc={r.returncode}: {(r.stderr or out)[:200]}")
    return json.loads(out)


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL"), name, "-", detail)


# 1. L0: root-only catalog
d = mcp("kb_list", {"lightweight": True, "parent_id": "__root__"})
roots = d.get("catalog", [])
sizes = len(json.dumps(d, ensure_ascii=False))
check("kb_list __root__ filter", d.get("success") and d.get("parent_filter") == "__root__"
      and all(not (kb.get("parent_id") or "") for kb in roots),
      f"roots={len(roots)} chars={sizes}")
check("kb_list small return", sizes < 8000, f"{sizes} chars (< 8000)")

# 2. kb_list whole catalog unchanged default
d2 = mcp("kb_list", {"lightweight": True})
check("kb_list default=all", d2.get("success") and d2.get("count") == len(d2.get("catalog", []))
      and d2.get("count", 0) > 0 and d2.get("parent_filter") == "all",
      f"count={d2.get('count')} entries={len(d2.get('catalog', []))} filter={d2.get('parent_filter')}")

# 3. children of a leaf KB (flat platform: expect 0, but the call must work)
d3 = mcp("kb_list", {"lightweight": True, "parent_id": KB_CS})
check("kb_list parent_id drill", d3.get("success") and d3.get("count") == 0,
      f"children of KB_CS={d3.get('count')} (flat shelf, no sub-KBs)")

# 4. groups view on the 131-doc shelf
g = mcp("kb_get_documents", {"kb_id": KB_CS, "lightweight": True, "view": "groups"})
gs = len(json.dumps(g, ensure_ascii=False))
groups = {x["group"]: x["count"] for x in g.get("groups", [])}
check("groups view tiny", g.get("success") and g.get("total_docs") == 131 and gs < 2000,
      f"{len(groups)} groups={sum(groups.values())} docs, {gs} chars")
print("   groups:", groups)

# 5. legacy auto call → budget guard page 1
a = mcp("kb_get_documents", {"kb_id": KB_CS, "lightweight": True})
as_ = len(json.dumps(a, ensure_ascii=False))
check("budget guard on legacy call", a.get("truncated") == "budget_guard" and a.get("page") == 1
      and a.get("has_more") is True and as_ <= BUDGET,
      f"page {a.get('page')}/{a.get('page_count')} {as_} chars total={a.get('total')}")

# 6. explicit pagination: walk all pages, each within budget, union = 131 unique docs
pages, seen, p = [], set(), 1
while True:
    pg = mcp("kb_get_documents", {"kb_id": KB_CS, "lightweight": True, "page": p})
    psz = len(json.dumps(pg, ensure_ascii=False))
    pages.append((p, psz, pg.get("count")))
    assert psz <= BUDGET, f"page {p} exceeded budget: {psz}"
    for e in pg.get("catalog", []):
        seen.add(e.get("doc_id") or e.get("doc_path"))
    if not pg.get("has_more"):
        break
    p += 1
check("paged walk complete", pg.get("page") == pg.get("page_count") and len(seen) == 131,
      f"pages={[(p_, s_, c_) for p_, s_, c_ in pages]} unique={len(seen)}")
check("every page within budget", all(s <= BUDGET for _, s, _ in pages),
      f"max page = {max(s for _, s, _ in pages)} chars")

# 7. explicit oversized page_size gets clamped by budget
big = mcp("kb_get_documents", {"kb_id": KB_CS, "lightweight": True, "page": 1, "page_size": 200})
bs = len(json.dumps(big, ensure_ascii=False))
check("page_size clamp", bs <= BUDGET and big.get("page_size", 0) <= 45,
      f"asked 200 → served page_size={big.get('page_size')} {bs} chars")

# 8. group-filtered docs page
nl = mcp("kb_get_documents", {"kb_id": KB_CS, "lightweight": True, "view": "docs", "group": "nlp", "page": 1})
check("group filter", nl.get("total") == groups.get("nlp") and nl.get("has_more") is False,
      f"nlp total={nl.get('total')} has_more={nl.get('has_more')}")

# 9. mechanical description pre-scan hits the gold doc (no LLM eyeballing needed)
s = mcp("kb_search", {"query": "InstructDS", "top_k": 5})
hits = s.get("hits", [])
gold = [h for h in hits if "instructds" in (h.get("docName") or "").lower()
        or "instructds" in (h.get("description") or "").lower()]
check("kb_search pre-scan gold", bool(gold), f"hits={len(hits)} gold={[h.get('docName') for h in gold][:2]}")
if gold:
    print("   gold hit:", gold[0].get("kbName"), "|", gold[0].get("docName"))
    print("   desc:", (gold[0].get("description") or "")[:120])

print()
failed = [n for n, ok, _ in results if not ok]
print(f"=== {len(results) - len(failed)}/{len(results)} PASS ===" + (f" FAILED: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
