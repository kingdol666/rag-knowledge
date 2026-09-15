"""Trace the README's benchmark claims to recorded artefacts."""
import json
import os
import re

ROOT = "."
SKIP = re.compile(r"node_modules|\\\.git\\|site-packages|\.venv|\.nuxt|\.output"
                  r"|\.mimosa|utils\\output|docs\\paper\\cikm")

print("=" * 78)
print("A. README claim: 'Flat vector P@5 0.590 FPR 12.0% 84ms / QDCVR 0.630 3.0% 38ms'")
print("=" * 78)

# The traceable in-house run
d = json.load(open("docs/paper/cikm/data-snapshot/module_b_retrieval_r2.json",
                   encoding="utf-8-sig"))
s = d["summary"]["overall"]
for m in ("staged", "vector"):
    v = s[m]
    print(f"  module_b {m:8s}: P@5={v.get('precision@5')}  hit@1={v.get('hit@1')}  "
          f"r@5={v.get('recall@5')}  lat={v.get('latency_s_mean')}s")
meta = d.get("meta", {})
print(f"  module_b meta: n_queries={meta.get('n_queries')} kbs={meta.get('n_kbs')} "
      f"threshold={meta.get('threshold')}")

print("\n  Searching for a structured artefact holding 0.590 / 0.630 / 12.0 / 3.0% ...")
hits = []
for base, dirs, files in os.walk(ROOT):
    if SKIP.search(base):
        continue
    for fn in files:
        if not fn.endswith((".json", ".cs", ".csv", ".tex")):
            continue
        p = os.path.join(base, fn)
        try:
            if os.path.getsize(p) > 2_000_000:
                continue
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        # look for the README's PAIR of numbers close together, not isolated floats
        if ("0.590" in t and "0.630" in t) or ('"p_at_5"' in t and "0.59" in t):
            hits.append(p)
print(f"  artefacts containing BOTH 0.590 and 0.630: {len(hits)}")
for h in hits[:10]:
    print(f"    {h}")

print("\n" + "=" * 78)
print("B. README claim: '6 domains, 20 adversarial queries'")
print("=" * 78)
q = json.load(open("docs/paper/benchmark/datasets/queries.json", encoding="utf-8-sig"))
if isinstance(q, dict):
    qs = q.get("queries", [])
    print(f"  queries.json keys: {list(q)[:8]}")
else:
    qs = q
print(f"  query count: {len(qs)}")
domains = {(x.get("domain") or x.get("expected_domain") or "") for x in qs if isinstance(x, dict)}
domains.discard("")
print(f"  distinct domains: {len(domains)} -> {sorted(domains)[:12]}")
adv = [x for x in qs if isinstance(x, dict) and not (x.get("domain") or x.get("expected_domain"))]
print(f"  entries with NO domain (adversarial?): {len(adv)}")

print("\n" + "=" * 78)
print("C. README-ZH claim: 'backend 106 endpoints, web 122 routes'")
print("=" * 78)
import urllib.request
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
oa = json.loads(OP.open("http://127.0.0.1:8771/openapi.json", timeout=20).read())
paths = oa.get("paths", {})
ops = sum(len([m for m in v if m in ("get", "post", "put", "patch", "delete")])
          for v in paths.values())
print(f"  LIVE backend: {len(paths)} paths / {ops} operations  (README-ZH says 106)")
web = 0
for base, dirs, files in os.walk("web/server/api"):
    web += len([f for f in files if f.endswith(".ts")])
print(f"  web route files: {web}  (README-ZH says 122)")
