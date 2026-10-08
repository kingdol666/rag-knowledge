#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared infrastructure for the KBS-paper experiments (QDCVR platform).

- NoProxyOpener: urllib opener that bypasses the system proxy (localhost!).
- get_token(): loop-auth.json -> .env MCP_AUTH_TOKEN fallback.
- McpClient: persistent SSE JSON-RPC client for the resident kb-mcp (:8000).
- chat_once(): one blocking POST /api/claude/chat call.
- QUESTIONS: 8 gold-annotated domain questions over the 5 production KBs.
"""
from __future__ import annotations

import http.client
import json
import queue
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path(r"D:\codes\ragproject\rag-knowledge")
RESULTS = Path(r"D:\codes\ragproject\rag-knowledge\paper-kbs\experiments\results")

CHAT_URL = "http://127.0.0.1:6789/api/claude/chat"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def get_token() -> str:
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        try:
            tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
            if tok:
                return tok
        except Exception:
            pass
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


class McpClient:
    """Persistent SSE JSON-RPC client for kb-mcp at 127.0.0.1:8000.

    Mirrors scripts/mcp_call.py transport: GET /sse -> endpoint event ->
    POST JSON-RPC per call -> match response by id on the SSE stream.
    """

    def __init__(self, host="127.0.0.1", port=8000, timeout=660.0):
        self.host, self.port, self.timeout = host, port, timeout
        self._q: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._t = threading.Thread(target=self._sse_reader, daemon=True)
        self._endpoint = None
        self._next_id = 0
        self._t.start()
        deadline = time.time() + 30
        while self._endpoint is None and time.time() < deadline:
            try:
                ev, data = self._q.get(timeout=1)
            except queue.Empty:
                continue
            if ev == "endpoint":
                self._endpoint = data
        if self._endpoint is None:
            raise RuntimeError("MCP SSE endpoint not received within 30s")
        self._init_ok = self._rpc("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "kbs-paper-exp", "version": "1.0"},
        }, timeout=30) is not None
        try:
            self._notify("notifications/initialized", {})
        except Exception:
            pass

    def _sse_reader(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=700)
        conn.request("GET", "/sse")
        resp = conn.getresponse()
        event = None
        while True:
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                self._q.put((event or "message", line[5:].strip()))

    def _post(self, payload: dict, timeout: float):
        body = json.dumps(payload)
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        conn.request("POST", self._endpoint, body=body,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status

    def _notify(self, method: str, params: dict):
        self._post({"jsonrpc": "2.0", "method": method, "params": params}, 15)

    def _rpc(self, method: str, params: dict, timeout: float):
        self._next_id += 1
        rid = self._next_id
        self._post({"jsonrpc": "2.0", "id": rid, "method": method,
                    "params": params}, timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ev, data = self._q.get(timeout=min(5, deadline - time.time()))
            except queue.Empty:
                continue
            if ev != "message":
                continue
            try:
                msg = json.loads(data)
            except Exception:
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {str(msg['error'])[:200]}")
                return msg.get("result")
        raise TimeoutError(f"MCP call {method} timed out after {timeout}s")

    def call(self, tool: str, args: dict, timeout: float | None = None):
        result = self._rpc("tools/call", {"name": tool, "arguments": args},
                           timeout or self.timeout)
        # tools/call wraps payload as content[0].text JSON
        try:
            content = result["content"]
            text = content[0]["text"] if isinstance(content, list) else str(content)
            return json.loads(text)
        except Exception:
            return result

    def close(self):
        pass


def chat_once(prompt: str, engine: str = "omp", kb_ids: list | None = None,
              kb_enhanced: bool = True, max_turns: int = 24,
              timeout_s: int = 660) -> dict:
    """One blocking POST /api/claude/chat; returns payload + wall time."""
    body = {"prompt": prompt, "kbEnhanced": kb_enhanced,
            "kbIds": kb_ids or [], "engine": engine,
            "permissionMode": "default", "maxTurns": max_turns}
    t0 = time.time()
    http, payload, err = 0, {}, ""
    try:
        req = urllib.request.Request(CHAT_URL, method="POST",
                                     data=json.dumps(body).encode("utf-8"))
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {get_token()}")
        with OPENER.open(req, timeout=timeout_s) as resp:
            http = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {str(e)[:200]}"
    wall = round(time.time() - t0, 1)
    return {"http": http, "payload": payload, "wall_s": wall, "error": err}


def norm_path(p: str) -> str:
    return str(p).replace("\\", "/")


def gold_hit(ranked_paths: list[str], gold_substrings: list[str], top_k=5):
    """Return (hits_in_topk, best_rank). ranked_paths: normalized doc paths."""
    ranks = []
    for g in gold_substrings:
        for i, p in enumerate(ranked_paths[:top_k], 1):
            if g.lower() in p.lower():
                ranks.append(i)
                break
    hits = len(ranks)
    best = min(ranks) if ranks else None
    return hits, best


# ---------------------------------------------------------------------------
# Gold question set: 8 domain questions over the 5 production KBs.
# gold_doc_substrings: unique filename fragments of the gold document(s).
# fact_markers: strings a factually grounded answer should contain.
# exp2: include in the (expensive) agentic end-to-end experiment.
# ---------------------------------------------------------------------------
QUESTIONS = [
    {"qid": "Q1", "kb": "薄膜工艺知识库",
     "text": "EVA光伏封装膜的层压工艺中，温度、压力和时间窗口应如何设定？交联度如何控制？",
     "gloss": "EVA encapsulation film lamination process window and cure control",
     "gold_doc_substrings": ["EVA封装膜工艺要点", "EVA封装膜湿热老化失效物理机理"],
     "fact_markers": ["层压", "交联"],
     "exp2": False},
    {"qid": "Q2", "kb": "光伏组件失效分析库",
     "text": "EL检测发现光伏组件边缘脱层，可能的根因是什么？应采取什么纠正措施？",
     "gloss": "EL edge delamination root cause and corrective actions",
     "gold_doc_substrings": ["EL-2025-0317"],
     "fact_markers": ["61", "85", "层压机"],
     "exp2": True},
    {"qid": "Q3", "kb": "光伏组件失效分析库",
     "text": "湿热环境下EVA封装膜为什么会生成乙酸并腐蚀焊带？水汽渗透机理是什么？",
     "gloss": "EVA hydrothermal aging acetic acid corrosion mechanism",
     "gold_doc_substrings": ["EVA封装膜湿热老化失效物理机理"],
     "fact_markers": ["乙酸", "水汽"],
     "exp2": False},
    {"qid": "Q4", "kb": "aw-industrial",
     "text": "POE光伏封装胶膜的水汽阻隔特性如何？层压工艺与EVA相比有什么差异？",
     "gloss": "POE encapsulant moisture barrier and lamination differences vs EVA",
     "gold_doc_substrings": ["POE胶膜工艺要点"],
     "fact_markers": ["水汽", "POE"],
     "exp2": True},
    {"qid": "Q5", "kb": "光伏电站运维知识库",
     "text": "光伏电站夏季发电量突然下降，应按什么顺序系统排查？",
     "gloss": "PV plant summer power drop systematic troubleshooting order",
     "gold_doc_substrings": ["发电量骤降排查手册", "电站运维经验教训"],
     "fact_markers": ["排查", "组串"],
     "exp2": False},
    {"qid": "Q6", "kb": "生产值守条款",
     "text": "注塑验收线1027收口件的克重警报触发条件是什么？标称克重和允差分别是多少？",
     "gloss": "injection line 1027 part weight alarm trigger condition and tolerance",
     "gold_doc_substrings": ["收口件克重警报值守条款"],
     "fact_markers": ["31.35", "0.05", "5"],
     "exp2": True},
    {"qid": "Q7", "kb": "aw-industrial",
     "text": "演示线1挤出主机熔体温度从206℃跌落到180℃事件，最终定案的根因是什么？",
     "gloss": "demo line 1 extruder melt temperature drop 206 to 180 final root cause verdict",
     "gold_doc_substrings": ["根因修订与跨频道对齐"],
     "fact_markers": ["TC", "死回路"],
     "exp2": True},
    {"qid": "Q8", "kb": "薄膜工艺知识库",
     "text": "PET双向拉伸薄膜的拉伸工艺流程是怎样的？关键温度区间如何控制？",
     "gloss": "PET biaxially oriented film stretching process and temperature control",
     "gold_doc_substrings": ["PET双向拉伸薄膜工艺规程"],
     "fact_markers": ["拉伸", "PET"],
     "exp2": False},
    {"qid": "Q9", "kb": "光伏电站运维知识库",
     "text": "逆变器频繁告警脱网，应该如何处置？常见告警的处理步骤是什么？",
     "gloss": "inverter frequent alarm trips handling steps",
     "gold_doc_substrings": ["逆变器告警处置手册"],
     "fact_markers": ["告警", "逆变器"],
     "exp2": False},
    {"qid": "Q10", "kb": "光伏电站运维知识库",
     "text": "光伏组件热斑的判定标准是什么？发现热斑后应如何处置？",
     "gloss": "PV module hot spot criteria and handling",
     "gold_doc_substrings": ["组件热斑检测与处置规程"],
     "fact_markers": ["热斑"],
     "exp2": False},
    {"qid": "Q11", "kb": "光伏电站运维知识库",
     "text": "组串失配的原因有哪些？如何通过IV曲线分析判断组串失配？",
     "gloss": "string mismatch causes and IV curve analysis",
     "gold_doc_substrings": ["组串失配分析方法"],
     "fact_markers": ["IV", "失配"],
     "exp2": False},
    {"qid": "Q12", "kb": "薄膜工艺知识库",
     "text": "PP流延薄膜的挤出流延工艺关键参数有哪些？急冷辊温度如何设定？",
     "gloss": "PP cast film extrusion parameters and chill roll temperature",
     "gold_doc_substrings": ["PP流延薄膜工艺规程"],
     "fact_markers": ["流延", "PP"],
     "exp2": False},
    {"qid": "Q13", "kb": "aw-industrial",
     "text": "注塑一线的克重闭环调优run1记录中，阶梯激励是如何设计和执行的？",
     "gloss": "injection line 1 weight closed-loop run1 staircase excitation design",
     "gold_doc_substrings": ["克重寻优-阶梯激励"],
     "fact_markers": ["阶梯", "克重"],
     "exp2": False},
    {"qid": "Q14", "kb": "aw-industrial",
     "text": "注塑一线P0优化后的FT全功能大考全链回归测试，结论是什么？",
     "gloss": "injection line 1 FT full-function regression test after P0 optimization",
     "gold_doc_substrings": ["FT全功能大考"],
     "fact_markers": ["FT", "回归"],
     "exp2": False},
    {"qid": "Q15", "kb": "aw-industrial",
     "text": "注塑一线多源异构三模态闭环诊断中，标量、向量与图像信号是如何融合的？",
     "gloss": "injection line multimode closed-loop scalar vector image fusion diagnosis",
     "gold_doc_substrings": ["三模态闭环"],
     "fact_markers": ["三模态", "融合"],
     "exp2": False},
    {"qid": "Q16", "kb": "aw-industrial",
     "text": "演示线1挤出主机heatdecay092跌落事件补偿后，R2工况恢复闭环复核的结论是什么？",
     "gloss": "demo line 1 extruder heatdecay092 post-compensation R2 recovery verification",
     "gold_doc_substrings": ["heatdecay092补偿后验证"],
     "fact_markers": ["补偿", "稳态"],
     "exp2": False},
]
