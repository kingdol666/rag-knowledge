"""Live runtime counts for the README audit (proxy-bypassing opener)."""
import json
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method, url, body=None, token=None, timeout=30):
    req = urllib.request.Request(url, method=method)
    req.add_header("content-type", "application/json")
    if token:
        req.add_header("authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with OP.open(req, data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


st, body = call("POST", "http://localhost:6789/api/auth/login",
                {"username": "uitest", "password": "uitest-dev-2026"})
if st != 200:
    raise SystemExit(f"login failed: {st} {body}")
tok = body["token"]
print(f"login ok (token {tok[:10]}…)\n")

# ---- KB catalog via the web proxy ----
st, cat = call("GET", "http://127.0.0.1:6789/api/kb/catalog", token=tok)
print(f"GET /api/kb/catalog -> {st}")
kbs = (cat or {}).get("knowledgeBases") or (cat or {}).get("catalog") or []
print(f"  top-level KBs: {len(kbs)}")
for k in kbs[:20]:
    print(f"    - {k.get('name')}  docs={k.get('documentCount', k.get('docCount', '?'))}  "
          f"kbId={str(k.get('kbId') or k.get('id'))[:12]}")

# ---- vector stats ----
st, stats = call("GET", "http://127.0.0.1:8771/api/v1/search/stats", token=tok)
print(f"\nGET /api/v1/search/stats -> {st}")
if isinstance(stats, dict):
    s = stats.get("stats", stats)
    cols = s.get("collections") or []
    print(f"  collections: {len(cols)}")
    tot = 0
    for c in cols[:20]:
        n = c.get("chunk_count") or c.get("chunks") or 0
        tot += n if isinstance(n, int) else 0
        print(f"    - {str(c.get('collection'))[:44]:<46} chunks={n}")
    print(f"  TOTAL chunks (sum of listed): {tot}")

# ---- graph stats ----
st, g = call("GET", "http://127.0.0.1:8771/api/v1/graph/stats", token=tok)
print(f"\nGET /api/v1/graph/stats -> {st}")
if isinstance(g, dict):
    print("  ", json.dumps(g.get("stats", g), ensure_ascii=False)[:400])

# ---- experience: does the README's 26-tool claim map to live endpoints? ----
st, h = call("GET", "http://127.0.0.1:8771/api/v1/health")
print(f"\nGET /api/v1/health (no auth) -> {st}  {json.dumps(h)[:160]}")
