#!/usr/bin/env python3
"""Per-engine stdout shape probe — one tool-triggering turn per harness,
captured with the EXACT argv the chat adapter uses. Output: probes/<eng>.txt
(truncated event dump for adapter design)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probes"
OUT.mkdir(exist_ok=True)
CWD = str(HERE.parents[2])  # repo root
PROMPT = "列出当前目录下名叫 web 的文件夹里有什么文件。用你的文件/终端工具实际执行,不要凭记忆回答。"

def run(name, argv, prompt, stdin=True, env_extra=None, timeout=120, win_cmd=False):
    t0 = time.time()
    env = {**os.environ, **(env_extra or {})}
    if win_cmd and os.name == "nt":
        argv = ["cmd.exe", "/d", "/s", "/c"] + argv
    try:
        p = subprocess.run(argv, input=prompt if stdin else None,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=CWD, env=env,
                           shell=False)
        out, err, code = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        code = "TIMEOUT"
    dt = round(time.time() - t0, 1)
    lines = [f"### {name} rc={code} {dt}s stdout={len(out)}ch stderr={len(err)}ch"]
    # 结构行摘要:每行只留 type/关键字段
    n_json = 0
    for ln in out.splitlines():
        t = ln.strip()
        if not (t.startswith("{") or t.startswith("[")):
            if t:
                lines.append("TEXT| " + t[:150])
            continue
        try:
            ev = json.loads(t)
        except Exception:
            lines.append("RAWJSON| " + t[:150])
            continue
        n_json += 1
        def brief(o, depth=0):
            if depth > 2: return "…"
            if isinstance(o, dict):
                keep = {}
                for k, v in o.items():
                    if k in ("content", "text", "output", "delta", "arguments", "rawInput", "command", "title", "name", "type", "item", "itemType", "status", "role", "toolName", "toolCallId", "kind", "sessionUpdate", "options", "toolCall", "data", "phase", "message", "response", "result", "error", "prompt", "cmd", "command_execution", "mcp_tool_call", "tool_use", "tool_result", "reasoning", "summary", "input"):
                        keep[k] = brief(v, depth + 1)
                    elif isinstance(v, (str, int, float, bool)):
                        keep[k] = v if len(str(v)) < 60 else str(v)[:57] + "..."
                return keep
            if isinstance(o, list):
                return [brief(x, depth + 1) for x in o[:4]]
            s = str(o)
            return s if len(s) < 80 else s[:77] + "..."
        lines.append("JSON| " + json.dumps(brief(ev), ensure_ascii=False)[:400])
    if err.strip():
        lines.append("## stderr tail")
        lines += [l[:200] for l in err.strip().splitlines()[-6:]]
    (OUT / f"{name}.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"{name}: rc={code} {dt}s json_events={n_json} -> probes/{name}.txt", flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "codex"):
        run("codex", ["codex", "exec", "--json", "--skip-git-repo-check", "--approve-for-me", "-"], PROMPT,
            stdin=True, win_cmd=True)
    if which in ("all", "cursor"):
        run("cursor", ["cursor-agent", "-p", "--output-format", "json", PROMPT], None,
            stdin=False, win_cmd=True)
    if which in ("all", "goose"):
        run("goose", ["goose", "run", "--output-format", "stream-json", "-t", PROMPT], None,
            stdin=False, env_extra={"GOOSE_MODE": "auto", "GOOSE_DISABLE_SESSION_NAMING": "true"}, win_cmd=True)
    if which in ("all", "pi"):
        import tempfile
        d = tempfile.mkdtemp(prefix="pi-probe-")
        f = os.path.join(d, "prompt.txt")
        Path(f).write_text(PROMPT, encoding="utf-8")
        run("pi", ["pi", "-p", "--mode", "json", "@" + f], None, stdin=False, win_cmd=True)
    if which in ("all", "qwen"):
        run("qwen", ["qwen"], PROMPT, stdin=True, win_cmd=True)
    if which in ("all", "copilot"):
        run("copilot", ["copilot", "--allow-all-tools", "--output-format", "json", "--no-ask-user", "-p", PROMPT], None,
            stdin=False, win_cmd=True)
    if which in ("all", "gemini"):
        run("gemini", ["gemini", "--output-format", "json", "--approval-mode", "yolo", "-p", PROMPT], None,
            stdin=False, win_cmd=True)
    if which in ("all", "opencode"):
        run("opencode", ["opencode", "run", PROMPT], None, stdin=False, win_cmd=True, timeout=150)
    if which in ("all", "crush"):
        run("crush", ["crush", "run", PROMPT], None, stdin=False, win_cmd=True, timeout=150)
