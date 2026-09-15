"""Backend OpenAPI surface: endpoint presence and per-tag operation counts."""
from collections import Counter
import json
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
d = json.loads(OP.open("http://127.0.0.1:8771/openapi.json", timeout=20).read())
paths = d["paths"]

for want in ["/api/v1/search/two-stage", "/api/v1/kb/list", "/api/v1/health"]:
    print(f"  {want:36s} {'present' if want in paths else '*** ABSENT ***'}")

c = Counter()
for p, v in paths.items():
    for m, o in v.items():
        if m in ("get", "post", "put", "patch", "delete"):
            for t in (o.get("tags") or ["Uncategorised"]):
                c[t] += 1

print(f"\n  distinct paths      : {len(paths)}")
print(f"  total operations    : {sum(c.values())}")
print(f"  openapi version     : {d['info'].get('version')}")
print(f"  security schemes    : {list(d.get('components', {}).get('securitySchemes', {}))}")
print("\n  operations by tag:")
for t, n in c.most_common():
    print(f"    {t:26s} {n}")

# how many operations declare bearer auth (i.e. are NOT public)
secured = public = 0
for p, v in paths.items():
    for m, o in v.items():
        if m not in ("get", "post", "put", "patch", "delete"):
            continue
        if o.get("security"):
            secured += 1
        else:
            public += 1
print(f"\n  operations requiring bearerAuth : {secured}")
print(f"  operations explicitly public    : {public}")
