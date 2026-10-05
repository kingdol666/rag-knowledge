"""Web-only restart: kill whatever holds the web port and respawn nuxt dev.

Deliberately does NOT touch the backend — the KB system (vectors, graph, BM25
memory) must stay up during long experiment runs. Usage:
  python scripts/restart_web.py
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB_PORT = 6789
WEB_DIR = REPO / "web"
LOG_DIR = WEB_DIR / "logs"


def web_up() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{WEB_PORT}/", timeout=6) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    if web_up():
        print("[web] already up, nothing to do")
        return 0
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                         text=True, encoding="gbk", errors="replace").stdout
    for line in out.splitlines():
        parts = line.split()
        if (len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING"
                and parts[1].rsplit(":", 1)[-1] == str(WEB_PORT)):
            pid = int(parts[4])
            try:
                os.kill(pid, 9)
                print(f"[web] killed stale holder {pid}")
            except OSError as e:
                print(f"[web] could not kill {pid}: {e}")
            break
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log = open(LOG_DIR / f"nuxt-dev-{stamp}.log", "ab")
    err = open(LOG_DIR / f"nuxt-dev-{stamp}.err.log", "ab")
    subprocess.Popen(["node", "./start.mjs"], cwd=str(WEB_DIR), stdout=log,
                     stderr=err,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                     | subprocess.DETACHED_PROCESS)
    for i in range(30):
        time.sleep(4)
        if web_up():
            print(f"[web] back up after {(i + 1) * 4}s (backend untouched)")
            return 0
    print("[web] FAILED to come back")
    return 1


if __name__ == "__main__":
    sys.exit(main())
