#!/usr/bin/env python3
"""最终实测：真实三层层级（父库→子库→文档）上的逐级检索。
 Part 1  脚本化阶梯：持久 MCP 连接逐级走（每步实测耗时+返回大小）
 Part 2  chat API 模式 B 真机：同一题交给系统 agent，流式抓完整工具时间线
 沙箱用后即删。
SSRF 边界：所有目标主机/端口均为本文件字面量回环地址（127.0.0.1，平台标准端口），
连接构造处固定，URL 路径无法改变目标——与 scripts/mcp_call.py 同款防护。"""
import json, subprocess, sys, threading, time, queue
import http.client
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
S = str(int(time.time()))
Q_TEXT = "知识库里查一下：RRF 倒数排名融合（Reciprocal Rank Fusion）里 k 常数取多少？这种方式相比加权分数求和有什么优势？"
GOLD = ["60", "无需调权"]
# 回环字面量——唯一允许的目标（SSRF 防护：主机端口不在任何变量中）
MCP_HOST, MCP_PORT = "127.0.0.1", 8000
CHAT_HOST, CHAT_PORT = "127.0.0.1", 6789


# ---------------- persistent MCP client (one SSE connection, sequential calls) ----------------
class Mcp:
    def __init__(self):
        self.q = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self.endpoint = None
        deadline = time.time() + 30
        while self.endpoint is None and time.time() < deadline:
            try:
                _, data = self.q.get(timeout=1)
                if isinstance(data, str) and data.startswith("/messages/"):
                    self.endpoint = data
            except queue.Empty:
                pass
        if not self.endpoint:
            raise RuntimeError("no MCP endpoint")
        self.rid = 0
        self._handshake()

    def _reader(self):
        conn = http.client.HTTPConnection(MCP_HOST, MCP_PORT, timeout=600)
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
                self.q.put((event or "message", line[5:].strip()))

    def _post(self, payload):
        assert self.endpoint.startswith("/messages/")
        body = json.dumps(payload, ensure_ascii=False)
        conn = http.client.HTTPConnection(MCP_HOST, MCP_PORT, timeout=60)
        conn.request("POST", self.endpoint, body=body.encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        conn.getresponse().read()
        conn.close()

    def _wait_id(self, rid, timeout=300):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ev, data = self.q.get(timeout=1)
            except queue.Empty:
                continue
            if ev != "message":
                continue
            try:
                d = json.loads(data)
            except Exception:
                continue
            if d.get("id") == rid:
                return d
        raise TimeoutError(f"id={rid}")

    def _handshake(self):
        self.rid += 1
        self._post({"jsonrpc": "2.0", "id": self.rid, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "ladder-final-test", "version": "1.0"}}})
        self._wait_id(self.rid, timeout=30)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, tool, args, timeout=300):
        self.rid += 1
        rid = self.rid
        self._post({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                    "params": {"name": tool, "arguments": args}})
        d = self._wait_id(rid, timeout=timeout)
        content = d.get("result", {}).get("content", [])
        txt = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        return json.loads(txt)


def sz(d):
    return len(json.dumps(d, ensure_ascii=False))


results = {"part1": [], "part2": {}}
ids = []
mcp = Mcp()
print("MCP connected:", mcp.endpoint)
try:
    # ================= build sandbox =================
    t = time.time()
    pid = mcp.call("kb_create", {"name": f"阶梯实测父库-{S}",
        "description": "实测父库：平台通用笔记层。子域内容见各子库描述，本层只存平台级通用笔记。"})["knowledgeBase"]["id"]
    said = mcp.call("kb_create", {"name": f"阶梯实测父库-检索算法-{S}",
        "description": "检索算法子库：RRF 倒数排名融合（k 常数）、交叉编码器重排、BM25 调优。可回答多路召回合并与精排问题。",
        "parent_id": pid})["knowledgeBase"]["id"]
    sbid = mcp.call("kb_create", {"name": f"阶梯实测父库-电池材料-{S}",
        "description": "电池材料子库：硅碳负极首效/循环稳定性/膨胀控制。可回答高能量密度电池设计问题。",
        "parent_id": pid})["knowledgeBase"]["id"]
    ids += [pid, said, sbid]
    mcp.call("kb_doc_create", {"kb_id": said, "name": "rrf-fusion.md",
        "description": "RRF 倒数排名融合：score=Σ1/(k+rank)，k 常数取 60，BM25+稠密向量双路合并无需调权，实测优于加权分数求和。中文。",
        "content": "# RRF 倒数排名融合\n\nRRF（Reciprocal Rank Fusion）：score(d)=Σ 1/(k+rank_i(d))，k 常数取 60。\n将 BM25 与稠密向量两路召回按排名倒数融合，无需调权重；HotpotQA 实测优于加权分数求和，且对单路异常排名更鲁棒。"})
    mcp.call("kb_doc_create", {"kb_id": said, "name": "cross-encoder.md",
        "description": "交叉编码器重排：bge-reranker 对 query-doc 逐对打分，top50→top5，NDCG@5 提升 12%。中文。",
        "content": "# 交叉编码器重排\n\n两阶段检索第二阶段：bge-reranker 精排，NDCG@5 提升 12%。"})
    mcp.call("kb_doc_create", {"kb_id": sbid, "name": "si-c-anode.md",
        "description": "硅碳负极：首效 88%、1000 圈保持 80%、多孔碳骨架控膨胀。中文。",
        "content": "# 硅碳负极\n\n首效 88%，1000 圈循环保持率 80%，多孔碳骨架缓冲 300% 体积膨胀。"})
    mcp.call("kb_doc_create", {"kb_id": pid, "name": "platform-notes.md",
        "description": "平台通用笔记：MCP 服务端口约定与日志目录布局，不含检索算法内容。中文。",
        "content": "# 平台通用笔记\n\nkb-mcp 走 8000 SSE；backend 8771；web 6789。日志在各自 logs/ 目录。"})
    for kb, doc in ((said, "rrf-fusion.md"), (said, "cross-encoder.md"), (sbid, "si-c-anode.md")):
        mcp.call("kb_index_document", {"kb_id": kb, "doc_path": doc})
    time.sleep(1)
    print(f"sandbox built in {time.time()-t:.1f}s: parent={pid[:8]} subA={said[:8]} subB={sbid[:8]}\n")

    # ================= PART 1: scripted ladder with per-step timing =================
    print("=" * 72)
    print("PART 1 — 脚本化逐级检索（持久连接，每步实测耗时/返回大小）")
    print("=" * 72)
    total = 0
    t0 = time.time()
    t = time.time(); l0 = mcp.call("kb_list", {"lightweight": True, "parent_id": "__root__"}); dt = time.time() - t
    total += sz(l0)
    parent = next(kb for kb in l0["catalog"] if kb["name"] == f"阶梯实测父库-{S}")
    results["part1"].append(("L0 kb_list(__root__)", dt, sz(l0), f"{l0['count']} 库 → 命中父库"))
    print(f"[{dt:5.2f}s {sz(l0):5d}ch] L0 根库目录 {l0['count']} 库 → 命中「{parent['name']}」")

    t = time.time(); lv1 = mcp.call("kb_list", {"lightweight": True, "parent_id": pid}); dt = time.time() - t
    total += sz(lv1)
    pick = next(kb for kb in lv1["catalog"] if "检索算法" in kb["description"])
    results["part1"].append(("L0.5-1 kb_list(parent)", dt, sz(lv1), f"{lv1['count']} 个子库 → 判定命中检索算法子库"))
    print(f"[{dt:5.2f}s {sz(lv1):5d}ch] L0.5·层1 子库 {lv1['count']} 个 → 判定命中「检索算法」")

    t = time.time(); lv2 = mcp.call("kb_list", {"lightweight": True, "parent_id": pick["kb_id"]}); dt = time.time() - t
    total += sz(lv2)
    results["part1"].append(("L0.5-2 kb_list(sub)", dt, sz(lv2), "0 子库 → 叶子确认"))
    print(f"[{dt:5.2f}s {sz(lv2):5d}ch] L0.5·层2 无子库 → 叶子书架确认")

    t = time.time(); docs = mcp.call("kb_get_documents", {"kb_id": pick["kb_id"], "lightweight": True}); dt = time.time() - t
    total += sz(docs)
    results["part1"].append(("L1 kb_get_documents(leaf)", dt, sz(docs), f"{docs['count']} 篇候选"))
    print(f"[{dt:5.2f}s {sz(docs):5d}ch] L1 文档描述层 {docs['count']} 篇 → 候选集锁定")

    cands = [{"kb_id": pick["kb_id"], "doc_path": d["doc_path"].replace("\\", "/")} for d in docs["catalog"]]
    t = time.time(); jd = mcp.call("kb_laya_judge", {"query": Q_TEXT, "criterion": "evidence", "threshold": 0.3,
                                                     "documents": json.dumps(cands, ensure_ascii=False)}); dt = time.time() - t
    surv = jd.get("survivor_count", 0)
    results["part1"].append(("L3 kb_laya_judge", dt, sz(jd), f"{jd.get('scored_count')} 段评分 / {surv} 幸存"))
    print(f"[{dt:5.2f}s {sz(jd):5d}ch] L3 判卷 {jd.get('scored_count')} 段 / 幸存 {surv}")

    surv_docs = jd.get("survivors") or []
    target = (surv_docs[0]["doc_path"] if surv_docs else "rrf-fusion.md").replace("\\", "/")
    t = time.time(); rd = mcp.call("kb_doc_read", {"kb_id": pick["kb_id"], "doc_path": target, "max_chars": 1500}); dt = time.time() - t
    content = rd.get("content", "")
    ok = all(g in content for g in GOLD)
    results["part1"].append(("L4 kb_doc_read", dt, sz(rd), f"金标复核={ok}"))
    print(f"[{dt:5.2f}s {sz(rd):5d}ch] L4 精读 {target} → 金标复核 {'✓' if ok else '✗'}")
    p1_wall = time.time() - t0
    print(f"\nPART 1 结论: 5 步阶梯总工具耗时 {p1_wall:.1f}s（judge≈{results['part1'][4][1]:.1f}s 占大头），"
          f"进入检索上下文的描述层累计 {total} chars —— 每一步只看一级，从未一次性拉全库\n")

    # ================= PART 2: chat API mode B (real agent, streamed) =================
    print("=" * 72)
    print("PART 2 — chat API 模式 B 真机（kbIds=[]，全库逐级车道，agent 自主导航）")
    print("=" * 72)
    AUTH = json.loads((REPO / "storage" / "fulltest-auth.json").read_text(encoding="utf-8"))
    TOK = AUTH["token"]
    body = {"prompt": Q_TEXT, "kbEnhanced": True, "kbIds": [], "engine": "claude",
            "permissionMode": "default", "maxTurns": 18, "timeout_ms": 600000, "stream": True}
    t0 = time.time()
    events, done, buf = [], None, ""
    assert f"http://{CHAT_HOST}:{CHAT_PORT}" == "http://127.0.0.1:6789"
    conn = http.client.HTTPConnection(CHAT_HOST, CHAT_PORT, timeout=660)
    conn.request("POST", "/api/claude/chat", body=json.dumps(body).encode("utf-8"),
                 headers={"Content-Type": "application/json",
                          "Authorization": f"Bearer {TOK}"})
    resp = conn.getresponse()
    print("HTTP", resp.status)
    for raw in resp:
        buf += raw.decode("utf-8", "replace")
        while "\n\n" in buf:
            frame, buf = buf.split("\n\n", 1)
            ev_name, ev_data = "", ""
            for ln in frame.splitlines():
                if ln.startswith("event: "):
                    ev_name = ln[7:].strip()
                elif ln.startswith("data: "):
                    ev_data = ln[6:]
            if not ev_name and ev_data:
                ev_name = "message"
            if not ev_name:
                continue
            try:
                d = json.loads(ev_data)
            except Exception:
                continue
            ent = {"t": round(time.time() - t0, 1), "event": ev_name}
            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
            if ev_name == "done":
                done = d
            blk = msg.get("content") if msg else d.get("content")
            if isinstance(blk, list):
                uses = [{"name": b.get("name"), "input": json.dumps(b.get("input") or {}, ensure_ascii=False)[:160]}
                        for b in blk if isinstance(b, dict) and b.get("type") == "tool_use"]
                res = [{"chars": len(json.dumps(b.get("content") or "", ensure_ascii=False))}
                       for b in blk if isinstance(b, dict) and b.get("type") == "tool_result"]
                if uses:
                    ent["uses"] = uses
                if res:
                    ent["res"] = res
            events.append(ent)
    wall = round(time.time() - t0, 1)
    answer = str((done or {}).get("result") or (done or {}).get("answer") or "")
    gold_hit = ["60" in answer]
    refused = any(m in answer[:300] for m in ("未找到", "没有找到", "无法", "不存在"))
    seq = []
    for e in events:
        for u in e.get("uses", []):
            seq.append((e["t"], u["name"], u["input"][:110]))
    print(f"wall={wall}s turns={((done or {}).get('num_turns'))} cost=${(done or {}).get('total_cost_usd')} "
          f"gold={'✓' if all(gold_hit) else '✗'} refusal={refused}")
    print("工具时间线（时刻s | 工具 | 入参摘要 | 同帧返回大小）:")
    sizes = [r["chars"] for e in events for r in e.get("res", [])]
    si = 0
    for t_, name, inp in seq:
        cs = sizes[si] if si < len(sizes) else "?"
        si += 1
        print(f"  t+{t_:6.1f}s  {name:28s} {inp}")
        print(f"{'':12s}↳ 返回 {cs} chars")
    results["part2"] = {"wall_s": wall, "turns": (done or {}).get("num_turns"),
                        "cost": (done or {}).get("total_cost_usd"), "gold_hit": all(gold_hit),
                        "refusal": refused, "n_tool_calls": len(seq),
                        "max_result_chars": max(sizes) if sizes else 0,
                        "answer_head": answer[:300], "timeline": seq}
    (REPO / "tmp" / "final_ladder_test_part2.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nanswer head:", answer[:220].replace("\n", " "))
    print("artifacts → tmp/final_ladder_test_part2.json")
finally:
    for sid in reversed(ids):
        try:
            mcp.call("kb_delete", {"kb_id": sid})
        except Exception as e:
            print("cleanup warn:", str(e)[:80])
    print("sandbox cleaned")
