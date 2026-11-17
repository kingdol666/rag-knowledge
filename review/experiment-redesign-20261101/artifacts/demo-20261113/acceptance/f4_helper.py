# -*- coding: utf-8 -*-
"""F4 acceptance helper: run one MCP tool call, append trace line to trace_b.jsonl."""
import json, subprocess, sys, time, io

REPO = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge"
TRACE = REPO + r"\review\experiment-redesign-20261101\artifacts\demo-20261113\acceptance\trace_b.jsonl"

def mcp(tool, args, n=None, phase="F4", max_res=4000):
    t0 = time.time()
    r = subprocess.run(["python", "-X", "utf8", "scripts/mcp_call.py", tool, json.dumps(args, ensure_ascii=False), "--raw"],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    dt = round(time.time() - t0, 1)
    out = r.stdout.strip()
    try:
        parsed = json.loads(out)
    except Exception:
        parsed = {"_raw": out[:max_res], "_stderr": r.stderr[-500:] if r.stderr else ""}
    compact = json.dumps(parsed, ensure_ascii=False)
    if len(compact) > max_res:
        compact = compact[:max_res] + f"...[truncated total {len(json.dumps(parsed, ensure_ascii=False))} chars]"
    if n is not None:
        line = {"n": n, "tool": tool, "args": args, "result": compact, "s": dt, "phase": phase}
        with io.open(TRACE, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"--- n={n} {tool} ({dt}s) ---")
    print(compact)
    return parsed

if __name__ == "__main__":
    spec = json.loads(sys.argv[1])
    mcp(spec["tool"], spec["args"], n=spec.get("n"), phase=spec.get("phase", "F4"))
