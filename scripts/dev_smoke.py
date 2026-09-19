"""Full-stack API smoke test: backend (8771, Bearer token) + web server (6789).

Reads MCP_AUTH_TOKEN from repo .env (never printed). Exits 1 on any FAIL.
SSRF-hardened by construction: every request passes guard_url(), which only
allows http://{127.0.0.1|localhost}:{8771|6789} with resolved-IP pinning and
redirects disabled.
Usage: python scripts/dev_smoke.py
"""
import ipaddress
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def guard_url(url: str) -> None:
    """SSRF guard: this smoke test may only talk to the local dev servers."""
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked smoke target (scheme/host): {url!r}")
    if p.port not in ALLOWED_PORTS:
        raise ValueError(f"blocked smoke target (port): {url!r}")
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError(f"DNS rebinding blocked: {url!r} -> {ip}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def load_token() -> str:
    path = os.path.join(ROOT, ".env")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""), flush=True)


def request(url: str, method: str = "GET", payload: dict = None, token: str = None,
            timeout: int = 30, stream: bool = False):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        resp = OPENER.open(req, data=data, timeout=timeout)
        if stream:
            return resp.status, resp
        return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def jget(url, **kw):
    s, b = request(url, **kw)
    try:
        return s, json.loads(b)
    except Exception:
        return s, b


def main() -> int:
    # ---------- backend ----------
    s, b = jget("http://127.0.0.1:8771/api/v1/health", token=TOKEN)
    check("BE /health", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/meditation/harnesses", token=TOKEN)
    hlist = b.get("harnesses", []) if isinstance(b, dict) else []
    n = len(hlist)
    check("BE /meditation/harnesses (>=14)", s == 200 and n >= 14,
          f"status={s} count={n}")
    if n >= 14:
        avail = sum(1 for h in hlist if h.get("available"))
        with_hint = sum(1 for h in hlist if h.get("hint"))
        print(f"       harnesses available={avail}/{n}, with-hint={with_hint}",
              flush=True)

    s, b = jget("http://127.0.0.1:8771/api/v1/meditation/status", token=TOKEN)
    check("BE /meditation/status", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/meditation/harness-status", token=TOKEN)
    check("BE /meditation/harness-status", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/meditation/models", token=TOKEN, timeout=90)
    check("BE /meditation/models", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/config", token=TOKEN)
    check("BE /config", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/graph/stats", token=TOKEN, timeout=60)
    check("BE /graph/stats", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/search/stats", token=TOKEN, timeout=60)
    check("BE /search/stats", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/experience/health", token=TOKEN, timeout=60)
    check("BE /experience/health", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/soul/list", token=TOKEN, timeout=60)
    check("BE /soul/list", s == 200, f"status={s}")

    s, b = jget("http://127.0.0.1:8771/api/v1/search/debug-paths", token=TOKEN, timeout=60)
    check("BE /search/debug-paths", s == 200, f"status={s}")

    s, b = request("http://127.0.0.1:8771/api/v1/search/vector", method="POST",
                   payload={"query": "transformer attention", "top_k": 3},
                   token=TOKEN, timeout=60)
    check("BE POST /search/vector", s == 200, f"status={s}")

    # ---------- web pages ----------
    for name, url in (("home", "http://127.0.0.1:6789/"),
                      ("chat-page", "http://127.0.0.1:6789/claude-chat"),
                      ("hub-page", "http://127.0.0.1:6789/harnesses")):
        s, b = request(url, timeout=30)
        check(f"WEB page {name}", s == 200, f"status={s}")

    # ---------- web server API (Bearer MCP token — /auth/verify whitelists it) ----------
    s, b = jget("http://127.0.0.1:6789/api/harnesses", token=TOKEN, timeout=60)
    hlist = b.get("harnesses", []) if isinstance(b, dict) else b
    n = len(hlist) if isinstance(hlist, list) else -1
    check("WEB /api/harnesses (>=14)", s == 200 and n >= 14, f"status={s} count={n}")

    s, b = jget("http://127.0.0.1:6789/api/harnesses/claude/models", token=TOKEN,
                timeout=90)
    check("WEB /api/harnesses/claude/models", s == 200, f"status={s}")

    for hid in ("mock", "codex", "dsh"):
        s, b = jget(f"http://127.0.0.1:6789/api/harnesses/{hid}/diagnostics",
                    token=TOKEN, timeout=120)
        check(f"WEB /api/harnesses/{hid}/diagnostics", s == 200, f"status={s}")

    # ---------- chat SSE (mock engine, no external deps) ----------
    payload = {
        "prompt": "ping: reply with exactly PONG",
        "cwd": ROOT,
        "engine": "mock",
        "maxTurns": 2,
    }
    saw_event, saw_result, err = False, False, ""
    try:
        s, resp = request("http://127.0.0.1:6789/api/claude/chat", method="POST",
                          payload=payload, token=TOKEN, timeout=90, stream=True)
        if isinstance(resp, str):
            err = f"no stream (status={s}): {resp[:120]}"
        else:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("event:"):
                    saw_event = True
                if line.startswith("data:"):
                    body = line[5:].strip()
                    if '"type":"result"' in body or '"type": "result"' in body:
                        saw_result = True
    except Exception as e:
        err = str(e)
    detail = err or "" if (saw_event and saw_result) else (
        err or ("no events" if not saw_event else "no result message"))
    check("WEB chat SSE mock (events + result)", saw_event and saw_result, detail)

    failed = RESULTS.count(False)
    print(f"\n==== smoke summary: {len(RESULTS) - failed} passed, {failed} failed ====",
          flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
