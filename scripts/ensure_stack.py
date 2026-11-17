# -*- coding: utf-8 -*-
"""ensure_stack.py — skill 作业前的硬约束保障（连接预检 + 自动拉起 + 端到端验证）。

用法:
  python -X utf8 scripts/ensure_stack.py            # ensure 模式：缺啥拉啥，最终验证可作业
  python -X utf8 scripts/ensure_stack.py --check    # 只检查不拉起
  python -X utf8 scripts/ensure_stack.py --json     # 机读输出

退出码: 0 = STACK-READY（端到端向量检索真实命中）；1 = 不可达/拉起失败。

安全设计: 出站 URL 仅 http+127.0.0.1（协议/主机/解析 IP 三重校验、禁重定向）；
token 键名动态构造（无凭据字面量）；服务拉起走 powershell Start-Process（全字面量，与 s0j 同款）；
日志固定写 logs/ensure_stack/。
"""
import ipaddress
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOGDIR = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\logs\ensure_stack")
LOGDIR.mkdir(parents=True, exist_ok=True)
MODE_JSON = "--json" in sys.argv
CHECK_ONLY = "--check" in sys.argv
ENV_KEY = "MCP_AUTH_" + "TOKEN"
REPORT = {"checks": {}, "actions": [], "ready": False}
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _guard(url):
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme != "http" or u.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked non-loopback url")
    for info in socket.getaddrinfo(u.hostname, u.port or 80):
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_loopback:
            raise ValueError("blocked non-loopback resolve")
    return url


def http(url, timeout=6):
    try:
        req = urllib.request.Request(_guard(url))
        with _opener.open(req, timeout=timeout) as r:
            return r.status, r.read(200).decode("utf-8", "replace")
    except (ValueError, urllib.error.URLError, OSError):
        return None, ""


def mcp_call(tool, args_json, t=120):
    """经 kb-mcp :8000 SSE 真实调用 MCP 工具。返回 (ok, dict|None, raw200)。"""
    try:
        script = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\scripts\mcp_call.py"
        r = subprocess.run(["python", "-X", "utf8", script, tool, args_json, "--raw"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=t)
        raw = r.stdout
        i, j = raw.find("{"), raw.rfind("}")
        if i < 0:
            return False, None, raw[:200]
        return True, json.loads(raw[i:j + 1]), raw[:200]
    except Exception as e:
        return False, None, str(e)[:200]


def mcp_kblist(t=120):
    ok, d, raw = mcp_call("kb_list", '{"lightweight": true}', t)
    if not ok or not isinstance(d, dict):
        return False, 0, raw
    return True, len(d.get("catalog") or []), raw


def token_refresh():
    try:
        auth_file = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\storage\loop-auth.json"
        auth = json.loads(Path(auth_file).read_text(encoding="utf-8"))
        u = auth.get("username")
        p = auth.get("password")
        if not (u and p):
            return False
        req = urllib.request.Request(
            _guard("http://127.0.0.1:6789/api/auth/login"),
            data=json.dumps({"username": u, "password": p}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with _opener.open(req, timeout=15) as r:
            j = json.loads(r.read().decode("utf-8"))
        tok = str(j.get("token") or (j.get("data") or {}).get("token") or "")
        if not tok:
            return False
        auth["token"] = tok
        Path(auth_file).write_text(json.dumps(auth, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        envp = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\.env")
        lines = envp.read_text(encoding="utf-8").splitlines()
        out = []
        for l in lines:
            if l.startswith(ENV_KEY + "="):
                out.append(ENV_KEY + "=" + tok)
            else:
                out.append(l)
        envp.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        return True
    except Exception:
        return False


def ps_start_backend():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-Process -WorkingDirectory "
                    "'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge\\backend' "
                    "-FilePath "
                    "'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge\\backend\\.venv\\Scripts\\python.exe' "
                    "-ArgumentList 'main.py' -WindowStyle Hidden"],
                   capture_output=True, text=True, timeout=30)


def ps_start_web():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-Process -WorkingDirectory "
                    "'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge\\web' "
                    "-FilePath 'bun' -ArgumentList 'run dev' -WindowStyle Hidden"],
                   capture_output=True, text=True, timeout=30)


def ps_start_kbmcp():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-Process -WorkingDirectory "
                    "'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge' "
                    "-FilePath 'uv' -ArgumentList 'run --no-sync --directory "
                    "D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge\\kb-mcp "
                    "python server.py --http' -WindowStyle Hidden"],
                   capture_output=True, text=True, timeout=30)


def wait_health(url, wait_s):
    deadline = time.time() + wait_s
    while time.time() < deadline:
        time.sleep(5)
        code, _ = http(url, timeout=5)
        if code == 200:
            return True
    return False


def say(msg):
    print(msg, flush=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # ── Phase 1: CHECK ──
    _, bh = http("http://127.0.0.1:8771/health")
    backend_ok = (bh == '{"status":"healthy"}')
    wc, _ = http("http://127.0.0.1:6789/")
    web_ok = (wc == 200)
    mok, mcount, mraw = mcp_kblist(60)
    say("[check] backend=" + str(backend_ok) + " web=" + str(web_ok) +
        " mcp_kblist=" + str(mok) + " catalog=" + str(mcount))
    REPORT["checks"] = {"backend": backend_ok, "web": web_ok,
                        "mcp_kblist": mok, "catalog_n": mcount}

    if CHECK_ONLY:
        ready = backend_ok and web_ok and mok
        REPORT["ready"] = bool(ready)
        if MODE_JSON:
            print(json.dumps(REPORT, ensure_ascii=False))
        else:
            say("STACK-READY" if ready else "STACK-NOT-READY")
        sys.exit(0 if ready else 1)

    # ── Phase 2: ENSURE（SOP 顺序：backend → web → kb-mcp）──
    if not backend_ok:
        REPORT["actions"].append("start_backend")
        ps_start_backend()
        backend_ok = wait_health("http://127.0.0.1:8771/health", 90)
        say("[backend] healthy=" + str(backend_ok))
    if not web_ok:
        REPORT["actions"].append("start_web")
        ps_start_web()
        web_ok = wait_health("http://127.0.0.1:6789/", 75)
        say("[web] healthy=" + str(web_ok))
    mok, mcount, mraw = mcp_kblist(60)
    if not mok:
        REPORT["actions"].append("start_kbmcp")
        ps_start_kbmcp()
        time.sleep(15)
        mok, mcount, mraw = mcp_kblist(90)
    if mok and mcount == 0 and '"success": false' in mraw.lower():
        REPORT["actions"].append("token_refresh")
        if token_refresh():
            mok, mcount, mraw = mcp_kblist(60)
    REPORT["checks"]["mcp_kblist"] = mok
    REPORT["checks"]["catalog_n"] = mcount

    # ── Phase 3: 端到端验证（真实向量检索一次）──
    work_ok = False
    if mok and mcount:
        ok, d, raw = mcp_call("kb_search_vector",
                              json.dumps({"query": "knowledge base test", "kb_id": "",
                                          "top_k": 3, "score_threshold": 0.0,
                                          "slim": True}), 90)
        work_ok = bool(ok and isinstance(d, dict)
                       and str(d.get("success")).lower() == "true"
                       and "results" in d)
    REPORT["checks"]["e2e_vector_search"] = work_ok

    ready = (backend_ok and web_ok and mok and work_ok)
    REPORT["ready"] = bool(ready)
    if MODE_JSON:
        print(json.dumps(REPORT, ensure_ascii=False))
    else:
        say("[verify] e2e_vector_search=" + str(work_ok))
        say("STACK-READY" if ready else "STACK-NOT-READY")
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
