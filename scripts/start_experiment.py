"""One-command launcher: start the KB system, then run the experiment platform.

Usage (from repo root):
  python scripts/start_experiment.py                     # 10-question full set, a,b,c
  python scripts/start_experiment.py --question "..."    # single question smoke
  python scripts/start_experiment.py --question "..." --tracks b,c

Steps:
  1. Health-check backend (8771) and web (6789); if either is down, clean-restart
     both via dev_restart.py and wait until healthy.
  2. Preflight: auth token available, corpus present, platform search reachable.
  3. Hand off to benchmark-suite/experiments.runner (chat mode, harness=claude).

SSRF-hardened: requests only target http://{127.0.0.1|localhost}:{8771|6789},
resolved-IP pinned, redirects disabled.
"""
import ipaddress
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

BE = "http://127.0.0.1:8771"
WEB = "http://127.0.0.1:6789"
_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
_ALLOWED_PORTS = {8771, 6789}


def _guard(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in _ALLOWED_HOSTS:
        raise ValueError(f"blocked non-loopback target: {url!r}")
    if p.port not in _ALLOWED_PORTS:
        raise ValueError(f"blocked port: {url!r}")
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError(f"DNS rebinding blocked: {url!r} -> {ip}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _token() -> str:
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
        if tok:
            return tok
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def _get(url: str, timeout: float = 8):
    _guard(url)
    req = urllib.request.Request(url)
    tok = _token()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with _OPENER.open(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def refresh_loop_token() -> bool:
    """Re-login the loop-* account (web restarts invalidate session tokens)."""
    cred_file = REPO / "storage" / "loop-auth.json"
    if not cred_file.exists():
        return False
    cred = json.loads(cred_file.read_text(encoding="utf-8"))
    if not cred.get("username") or not cred.get("password"):
        return False
    _guard(f"{WEB}/api/auth/login")
    req = urllib.request.Request(
        f"{WEB}/api/auth/login",
        data=json.dumps({"username": cred["username"],
                         "password": cred["password"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with _OPENER.open(req, timeout=15) as resp:
        data = json.loads(resp.read())
    tok = (data.get("token") or data.get("data", {}).get("token")
           or data.get("access_token"))
    if not tok:
        return False
    cred["token"] = tok
    cred_file.write_text(json.dumps(cred, indent=2), encoding="utf-8")
    print("[start] loop-auth token refreshed via /api/auth/login")
    return True


def services_healthy() -> bool:
    try:
        s, _ = _get(f"{BE}/api/v1/health")
        s2, _ = _get(f"{WEB}/")
        return s == 200 and s2 == 200
    except Exception:
        return False


def ensure_services() -> None:
    if services_healthy():
        print("[start] services healthy (backend 8771 / web 6789)")
        return
    print("[start] services down -> clean restart via dev_restart.py ...")
    subprocess.run([sys.executable, str(REPO / "scripts" / "dev_restart.py")],
                   check=False)
    for i in range(30):
        time.sleep(6)
        if services_healthy():
            print(f"[start] services healthy after {(i + 1) * 6}s")
            return
    raise SystemExit("[start] services failed to become healthy")


def preflight() -> None:
    try:
        code, body = _get(f"{WEB}/api/kb/search?query=attention&top_k=1", timeout=60)
    except urllib.error.HTTPError as e:
        code = e.code
    if code == 401:
        print("[preflight] 401 -> refreshing loop-auth token ...")
        if not refresh_loop_token():
            raise SystemExit("[preflight] token refresh FAILED — check "
                             "storage/loop-auth.json credentials")
        code, body = _get(f"{WEB}/api/kb/search?query=attention&top_k=1", timeout=60)
    print(f"[preflight] platform search reachable: {code} "
          f"({'ok' if code == 200 else 'FAIL'})")
    corpus = REPO / "benchmark-suite" / "data" / "corpus_md"
    n = len(list(corpus.glob("*.md"))) if corpus.exists() else 0
    # Corpus scale: 50 papers (R1) or 100 papers (R2, current 2026-09-22 口径).
    expected = {50, 100}
    print(f"[preflight] exported corpus: {n} files "
          f"({'ok' if n in expected else 'UNEXPECTED (expect 50 or 100)'})")
    if code != 200 or n not in expected:
        raise SystemExit("[preflight] FAILED — run PIPELINE stages 0-5 first "
                         "(the experiment requires the same indexed corpus).")


def main() -> int:
    args = sys.argv[1:]
    if not any(a in args for a in ("--question", "--questions")):
        args = ["--questions", "data/papers/qa_questions.json"] + args
    ensure_services()
    preflight()
    print("[start] launching experiment platform (chat mode, harness=claude) ...")
    r = subprocess.run(
        [sys.executable, "-m", "experiments.runner"] + args,
        cwd=str(REPO / "benchmark-suite"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
