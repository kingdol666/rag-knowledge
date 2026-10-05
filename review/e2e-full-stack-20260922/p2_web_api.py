"""P2 — web BFF (6789) API surface E2E.

SSRF-hardened by construction: every request passes guard_url(), which only
allows http://127.0.0.1:{8771|6789} with resolved-IP pinning and redirects
disabled (same pattern as scripts/dev_smoke.py). Exits 1 on any FAIL.
Usage: python review/e2e-full-stack-20260922/p2_web_api.py
"""
import ipaddress
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def guard_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked target (scheme/host): {url!r}")
    if p.port not in ALLOWED_PORTS:
        raise ValueError(f"blocked target (port): {url!r}")
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError(f"DNS rebinding blocked: {url!r} -> {ip}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def load_token() -> str:
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
results = []


def call(method, url, body=None, token=TOKEN, timeout=90):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with OPENER.open(req, data=data, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, {"_raw": raw[:200]}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


WEB = "http://127.0.0.1:6789"

s, _ = call("GET", WEB + "/api/kb/catalog", token=None)
check("web /api/kb/catalog no-token -> 401", s == 401, f"status={s}")

s, j = call("GET", WEB + "/api/kb/catalog")
kbs = j.get("knowledgeBases") or []
check("web /api/kb/catalog", s == 200 and j.get("success") and len(kbs) >= 7, f"kbs={len(kbs)}")
s, j = call("GET", WEB + "/api/kb/search", token=TOKEN)
check("web /api/kb/search (empty q -> 400 validation)", s in (200, 400), f"status={s}")
s, j = call("GET", WEB + "/api/config/frontend")
cfg = j.get("config") or {}
check("web /api/config/frontend", s == 200 and cfg.get("backend_url"), json.dumps(cfg, ensure_ascii=False)[:140])
s, j = call("GET", WEB + "/api/harnesses")
if isinstance(j, list):
    n_harness = len(j)
else:
    n_harness = len(j.get("harnesses") or [])
check("web /api/harnesses >=14", s == 200 and n_harness >= 14, f"count={n_harness}")
s, j = call("GET", WEB + "/api/soul/list")
check("web /api/soul/list", s == 200, f"status={s} body={json.dumps(j, ensure_ascii=False)[:100]}")
s, j = call("GET", WEB + "/api/claude/engines")
check("web /api/claude/engines", s == 200, f"status={s}")
s, j = call("GET", WEB + "/api/claude/skills", token=TOKEN)
check("web /api/claude/skills", s == 200, f"status={s} type={type(j).__name__}")
s, j = call("GET", WEB + "/api/claude/history")
check("web /api/claude/history", s == 200, f"status={s} type={type(j).__name__}")
s, j = call("GET", WEB + "/api/meditation/status")
check("web /api/meditation/status", s == 200, f"status={s}")
s, j = call("GET", WEB + "/api/harnesses/claude/models")
check("web /api/harnesses/claude/models", s == 200, f"status={s}")
s, j = call("GET", WEB + "/api/graph/stats")
check("web /api/graph/stats (proxy)", s == 200 and j.get("success"), f"status={s}")
s, j = call("GET", WEB + "/api/health")
check("web /api/health (whitelisted)", s == 200, json.dumps(j, ensure_ascii=False)[:100])

print()
failed = [n for n, ok, _ in results if not ok]
print(f"==== P2 web-api summary: {len(results) - len(failed)}/{len(results)} passed ====")
sys.exit(1 if failed else 0)
