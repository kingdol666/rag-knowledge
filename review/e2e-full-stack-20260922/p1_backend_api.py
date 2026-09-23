"""P1 — backend (8771) API surface E2E. Stdlib-only.

SSRF-hardened by construction: every request passes guard_url(), which only
allows http://127.0.0.1:{8771|6789} with resolved-IP pinning and redirects
disabled (same pattern as scripts/dev_smoke.py). Token read from repo .env,
never printed; all test credentials are generated at runtime via `secrets`.
Exits 1 on any FAIL.
Usage: python review/e2e-full-stack-20260922/p1_backend_api.py
"""
import ipaddress
import json
import os
import secrets
import socket
import string
import sys
import time
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


def call(method, url, body=None, token=TOKEN, headers=None, timeout=60):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with OPENER.open(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


BE = "http://127.0.0.1:8771"

# 1. root + openapi
s, j = call("GET", BE + "/", timeout=30)
check("GET / service info", s == 200 and j.get("service"), f"status={s} service={j.get('service')}")
s, j = call("GET", BE + "/openapi.json", timeout=30)
check("GET /openapi.json", s == 200 and len(j.get("paths", {})) > 80, f"status={s} paths={len(j.get('paths', {}))}")

# 2. config
s, j = call("GET", BE + "/api/v1/config/schema")
check("GET /config/schema", s == 200 and j.get("schema") and j.get("env_schema"), f"status={s}")
s, j = call("GET", BE + "/api/v1/config")
eff = j.get("effective", {})
check("GET /config effective", s == 200 and eff.get("backend_port"), f"effective={eff}")

# 3. auth lifecycle (fresh user; credentials generated at runtime)
stamp = time.strftime("%m%d%H%M%S")
user = "e2e-full-" + stamp
alphabet = string.ascii_letters + string.digits
pwd = "".join(secrets.choice(alphabet) for _ in range(14)) + "!aA1"
wrong_pwd = "bad-" + secrets.token_hex(8)
s, j = call("POST", BE + "/api/v1/auth/register", {"username": user, "password": pwd}, token=None)
check("auth register", s == 200 and j.get("success"), f"status={s} user={user}")
s, j = call("POST", BE + "/api/v1/auth/login", {"username": user, "password": pwd}, token=None)
user_token = j.get("token") or ""
check("auth login (1-day session)", s == 200 and bool(user_token), f"status={s} has_token={bool(user_token)}")
s, j = call("POST", BE + "/api/v1/auth/verify", {"token": user_token}, token=None)
check("auth verify user token", s == 200 and j.get("valid"), f"status={s}")
s, j = call("POST", BE + "/api/v1/auth/tokens", {"name": "e2e-full-api", "ttl_days": 1}, token=user_token)
minted = j.get("token") or ""
check("auth tokens create (sk- plaintext once)", s == 200 and minted.startswith("sk-"), f"status={s}")
s, j = call("GET", BE + "/api/v1/auth/tokens", token=user_token)
tok_list = j.get("tokens") or []
new_id = next((t.get("id") for t in tok_list if t.get("name") == "e2e-full-api"), None)
check("auth tokens list", s == 200 and new_id is not None, f"count={len(tok_list)}")
s, j = call("DELETE", BE + "/api/v1/auth/tokens/" + str(new_id), token=user_token)
check("auth token revoke", s == 200 and j.get("revoked"), f"status={s}")
s, j = call("POST", BE + "/api/v1/auth/verify", {"token": minted}, token=None)
check("revoked token now invalid", s == 200 and not j.get("valid"), f"valid={j.get('valid')}")
s, j = call("POST", BE + "/api/v1/auth/login", {"username": user, "password": wrong_pwd}, token=None)
check("bad password rejected", s in (401, 400, 403), f"status={s}")

# 4. documents/split (pure compute) — semantics: split only above the 30000 threshold
long_text = "# 分块测试\n\n" + (
    "这是一段用于验证大文档拆分门禁的真实内容，覆盖向量化前的切分行为。段落包含标题、列表与代码块。\n\n" * 60
)
s, j = call("POST", BE + "/api/v1/documents/split", {"title": "e2e-split", "content": long_text})
below_threshold = (j.get("source_chars") or 0) <= 30000
split_ok = (s == 200 and j.get("split") and j.get("part_count", 0) > 1) if not below_threshold \
    else (s == 200 and j.get("part_count", 0) >= 1)
check("documents/split (threshold semantics)", split_ok,
      f"chars={j.get('source_chars')} parts={j.get('part_count')} split={j.get('split')}")

# 5. system/clean dry-run
s, j = call("POST", BE + "/api/v1/system/clean", {"scope": "mineru", "dry_run": True})
check("system/clean dry_run", s == 200 and j.get("success"), f"items={len(j.get('items', []))}")

# 6. search stats global
s, j = call("GET", BE + "/api/v1/search/stats")
st = j.get("stats", {})
check("search/stats global", s == 200 and j.get("success"), json.dumps(st, ensure_ascii=False)[:160])

print()
failed = [n for n, ok, _ in results if not ok]
print(f"==== P1 backend-api summary: {len(results) - len(failed)}/{len(results)} passed ====")
sys.exit(1 if failed else 0)
