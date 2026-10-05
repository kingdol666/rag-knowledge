#!/usr/bin/env python3
"""最终验收 · 对外 API 面：外部系统按需调用知识库能力，逐个验证。

1. GET  /api/kb/catalog             — 库目录（外部发现）
2. POST /api/kb/native-search      — 一次性原生检索（rag-bridge 契约）
3. POST /api/kb/agent/chat         — 外部任务移交给平台 agent（自治完成）
4. POST /api/claude/chat           — 平台聊天 API（kbEnhanced 检索增强）

全部走真实鉴权（loop-auth 凭据，401 自动重登）。输出每接口耗时与答案摘录。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "experiments"))

from lib import _token, login_refresh, WEB  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
results: list[tuple[str, bool, str]] = []


def call(method: str, path: str, payload: dict | None, timeout: float) -> tuple[int, dict | str]:
    tok = _token()
    req = urllib.request.Request(WEB + path, method=method,
                                 data=json.dumps(payload).encode() if payload else None)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.build_opener().open(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw[:400]
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", "replace")[:300])


def step(label: str, ok: bool, detail: str) -> None:
    results.append((label, ok, detail))
    print(f"  {'✅' if ok else '❌'} {label} {('— ' + detail) if detail else ''}")


login_refresh()
print(f"[final-e2e] web = {WEB}")

# 1) catalog
t0 = time.time()
code, d = call("GET", "/api/kb/catalog", None, 30)
el = round(time.time() - t0, 1)
kbs = (d.get("catalog") or d.get("knowledgeBases") or d.get("kbs") or []) if isinstance(d, dict) else []
step("GET /api/kb/catalog", code == 200 and len(kbs) > 0,
     f"HTTP {code} · {el}s · {len(kbs)} KBs")

# 2) native-search（外部 rag-bridge 一次性检索）
t0 = time.time()
code, d = call("POST", "/api/kb/native-search",
               {"query": "CoRoT 截至 2010 年夏共收集了多少条光变曲线？", "top_k": 5,
                "timeout_ms": 300000, "max_turns": 12}, 360)
el = round(time.time() - t0, 1)
answer = str(d.get("answer") or d.get("result") or "") if isinstance(d, dict) else str(d)
hit = ("129" in answer) or ("129,326" in answer) or ("129 326" in answer)
step("POST /api/kb/native-search", code == 200 and hit,
     f"HTTP {code} · {el}s · answer {len(answer)}ch · 数值命中={hit}")

# 3) agent/chat（外部移交任务 —— async 提交 + 轮询，标准外部集成模式）
t0 = time.time()
code, d = call("POST", "/api/kb/agent/chat",
               {"prompt": "用知识库检索回答：BERT 使用哪个分词器、词表多大？给出文档路径。完成后以 Result 结尾。",
                "mode": "async", "timeout_ms": 480000}, 30)
task_id = d.get("task_id") if isinstance(d, dict) else None
ok_submit = code == 200 and bool(task_id)
step("POST /api/kb/agent/chat (async submit)", ok_submit,
     f"HTTP {code} · task_id={task_id}")
answer3 = ""
if ok_submit:
    for _ in range(150):  # up to ~750s (agent flow runs 6-8 min legitimately)
        time.sleep(5)
        code_t, d_t = call("GET", f"/api/kb/agent/tasks/{task_id}", None, 20)
        st = d_t.get("status") if isinstance(d_t, dict) else None
        if st in ("completed", "failed"):
            res = d_t.get("result") or {} if isinstance(d_t, dict) else {}
            answer3 = str(res.get("reply") or res.get("result") or res.get("answer") or "")
            break
el = round(time.time() - t0, 1)
hit3 = ("WordPiece" in answer3) or ("30,000" in answer3) or ("30522" in answer3)
step("GET  /api/kb/agent/tasks/:id (poll → result)", hit3,
     f"{el}s · answer {len(answer3)}ch · WordPiece 命中={hit3}")

# 4) claude/chat（kbEnhanced，SSE 流式——读到 done 事件为止）
t0 = time.time()
tok = _token()
req = urllib.request.Request(WEB + "/api/claude/chat", method="POST",
                             data=json.dumps({"prompt": "CoRoT 任务延伸期到什么时候结束？",
                                              "engine": "claude", "kbEnhanced": True,
                                              "kbIds": ["1e6199ea-f380-44e2-94fc-d431f0f9bb6b"],
                                              "maxTurns": 12}).encode())
req.add_header("Content-Type", "application/json")
req.add_header("Accept", "text/event-stream")
req.add_header("Authorization", f"Bearer {tok}")
answer4, done, err = "", False, ""
with urllib.request.build_opener().open(req, timeout=420) as resp:
    cur = ""
    for raw in resp:
        line = raw.decode("utf-8", "replace").strip()
        if line.startswith("event:"):
            cur = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        try:
            msg = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if cur == "done":
            done = True
            u = msg.get("usage") or {}
            texts = []
            break
        if msg.get("type") == "assistant":
            for blk in (msg.get("message") or {}).get("content", []):
                if blk.get("type") == "text" and (blk.get("text") or "").strip():
                    answer4 = blk["text"]
el = round(time.time() - t0, 1)
hit4 = ("2013" in answer4)
step("POST /api/claude/chat (kbEnhanced SSE)", done and hit4,
     f"done={done} · {el}s · answer {len(answer4)}ch · 2013 命中={hit4}")

(OUT_DIR / "external_apis_result.json").write_text(
    json.dumps({r[0]: {"ok": r[1], "detail": r[2]} for r in results},
               ensure_ascii=False, indent=1), encoding="utf-8")

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n[final-e2e] external APIs: {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
