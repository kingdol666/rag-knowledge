#!/usr/bin/env python3
"""全链路完整测试 2026-10-12 — chat API(AWS 集成面) 全生命周期 + 双 harness(claude/omp) 三模式.

面板:
  Stage A  POST :6789/api/kb/agent/chat (AWS rag-bridge 集成面, 原生全技能)
           A1 检索命中  A2 如实拒答  A3 入库  A4 入库后回查
           A5 跨库检索  A6 经验沉淀   A7 二次入库+图谱关联
  Stage B  POST :6789/api/claude/chat engine=claude
           B_A 指定库向量快车道(SSE 流程监控)  B_B 全库逐级检索  B_C hybrid 全原生
           B_IN 入库  B_VF 入库后向量回查
  Stage C  同 B, engine=omp

产物: review/fulltest-20261012/<tag>.json + progress.log;  断点续跑: 已存在 JSON 跳过.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402

HERE = Path(__file__).resolve().parent
WEB = "http://127.0.0.1:6789"
BACKEND = "http://127.0.0.1:8771"

AUTH = json.loads((REPO / "storage" / "fulltest-auth.json").read_text(encoding="utf-8"))
TOK = AUTH["token"]
STAMP = time.strftime("%Y%m%d-%H%M%S")
KB_NAME = f"fulltest-e2e-{STAMP}"
KB_DESC = "全链路完整测试沙箱库(蓝鹊/灰隼标定记录)"

DOC1 = ("# 蓝鹊-47 试验记录\n\n"
        "青鸾-7 传感阵列在第四标定段的谐振阈值为 47.3 MHz。\n"
        "漂移补偿系数 0.0837。\n"
        "试验负责人: 沈砚。\n"
        "备注: 本记录仅用于知识库全链路验收, 数据为虚构。\n")
DOC2 = ("# 灰隼-19 校准报告\n\n"
        "灰隼-19 陀螺零偏稳定性标定值为 0.0042 °/h。\n"
        "温补点 19.6 摄氏度, 复现窗口 42 分钟。\n"
        "校准人: 顾清弦。\n"
        "备注: 与《蓝鹊-47 试验记录》同属第四批标定。\n")

KB_CS = ""     # 计算机与人工智能 kbId, 预检时填充
KB_EARTH = ""  # 自然科学与地球科学 kbId
KB_ID = ""     # 沙箱库 kbId

REFUSAL_MARKERS = ("无法", "没有找到", "未找到", "未检索到", "没有检索到", "不存在",
                   "无法回答", "无法作答", "无法据此", "没有相关",
                   "not found", "no document", "cannot answer", "unable to answer",
                   "no evidence", "cannot find", "not covered", "知识库中无",
                   "未收录", "没有命中", "无对应内容", "没有足够")


def req_json(method: str, url: str, body=None, token: str = TOK, timeout: float = 60.0):
    guard_url(url)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, method=method, data=data,
                               headers={"Content-Type": "application/json",
                                        "Authorization": f"Bearer {token}"})
    with OPENER.open(r, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def save(tag: str, rec: dict):
    (HERE / f"{tag}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                      encoding="utf-8")


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(HERE / "progress.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ────────────────────────── 引擎调用面 ──────────────────────────

def agent_chat(prompt: str, tag: str, *, mode: str = "sync",
               timeout_s: float = 540.0) -> dict:
    """AWS 集成面 POST /api/kb/agent/chat; async 自动轮询到终态."""
    t0 = time.time()
    rec: dict = {"tag": tag, "surface": "agent/chat", "mode": mode,
                 "prompt": prompt[:400]}
    try:
        status, payload = req_json("POST", f"{WEB}/api/kb/agent/chat",
                                   {"prompt": prompt, "mode": mode,
                                    "timeout_ms": int(timeout_s * 1000)},
                                   timeout=timeout_s + 30)
        rec["http"] = status
        if mode == "async":
            rec["task_id"] = payload.get("task_id")
            log(f"  {tag}: async task_id={rec['task_id']}, 轮询中…")
            deadline = time.time() + timeout_s
            last: dict = {}
            while time.time() < deadline:
                try:
                    _, last = req_json("GET", f"{WEB}/api/kb/agent/tasks/{rec['task_id']}",
                                       timeout=30)
                except Exception as e:  # noqa: BLE001
                    last = {"poll_error": str(e)[:150]}
                st = str(last.get("status") or "")
                if st in ("completed", "failed", "error"):
                    break
                time.sleep(6)
            rec["task_final"] = last
            payload = last
        rec["reply"] = str(payload.get("reply") or payload.get("result") or "")
        rec["tools_used"] = payload.get("tools_used")
        rec["num_turns"] = payload.get("num_turns")
        rec["duration_ms"] = payload.get("duration_ms")
        rec["cost_usd"] = payload.get("total_cost_usd")
        rec["stop_reason"] = payload.get("stop_reason")
        rec["engine"] = payload.get("engine")
    except urllib.error.HTTPError as e:
        rec.update({"http": e.code, "error": e.read().decode("utf-8", "replace")[:400]})
    except Exception as e:  # noqa: BLE001
        rec.update({"http": None, "error": f"{type(e).__name__}: {str(e)[:250]}"})
    rec["wall_s"] = round(time.time() - t0, 1)
    save(tag, rec)
    err = f" ERR={str(rec.get('error'))[:120]}" if rec.get("error") else ""
    log(f"  {tag}: wall={rec['wall_s']}s dur={rec.get('duration_ms')}ms "
        f"turns={rec.get('num_turns')} reply={len(rec.get('reply') or '')}ch{err}")
    return rec


def harness_chat(prompt: str, tag: str, *, engine: str = "claude",
                 kb_enhanced: bool = True, kb_ids=None,
                 permission_mode: str = "default", max_turns: int = 24,
                 timeout_s: float = 540.0, stream: bool = False) -> dict:
    """harness 面 POST /api/claude/chat (非流式取指标; stream=True 抓流程时间线)."""
    t0 = time.time()
    body = {"prompt": prompt, "engine": engine, "kbEnhanced": kb_enhanced,
            "maxTurns": max_turns, "permissionMode": permission_mode,
            "timeout_ms": int(timeout_s * 1000), "stream": stream}
    if kb_ids:
        body["kbIds"] = kb_ids
    rec: dict = {"tag": tag, "surface": "claude/chat", "engine": engine,
                 "kbEnhanced": kb_enhanced, "kbIds": kb_ids or [],
                 "permissionMode": permission_mode, "prompt": prompt[:400]}
    try:
        if not stream:
            status, payload = req_json("POST", f"{WEB}/api/claude/chat", body,
                                       timeout=timeout_s + 30)
            rec.update({"http": status, "response": payload,
                        "answer": str(payload.get("answer") or ""),
                        "num_turns": payload.get("num_turns"),
                        "duration_ms": payload.get("duration_ms"),
                        "cost_usd": payload.get("total_cost_usd"),
                        "session_id": payload.get("sessionId")})
        else:
            guard_url(f"{WEB}/api/claude/chat")
            data = json.dumps(body).encode("utf-8")
            r = urllib.request.Request(f"{WEB}/api/claude/chat", method="POST",
                                       data=data, headers={
                                           "Content-Type": "application/json",
                                           "Authorization": f"Bearer {TOK}"})
            timeline: list = []
            done_msg: dict | None = None
            buf = ""
            t_start = time.time()
            with OPENER.open(r, timeout=timeout_s + 30) as resp:
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
                            ev_name = "message"  # 裸 data 帧 = 引擎消息流(工具/文本)
                        if not ev_name:
                            continue
                        entry: dict = {"t": round(time.time() - t_start, 1),
                                       "event": ev_name}
                        try:
                            d = json.loads(ev_data)
                        except Exception:  # noqa: BLE001
                            d = {"raw": ev_data[:120]}
                        if ev_name == "done":
                            done_msg = d
                            entry["subtype"] = d.get("subtype")
                        elif ev_name == "meta":
                            entry["engine"] = d.get("engine")
                        else:
                            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
                            mtype = d.get("type") or msg.get("type")
                            entry["mtype"] = mtype
                            blk = msg.get("content") if msg else d.get("content")
                            if isinstance(blk, list):
                                tools = [b.get("name") for b in blk
                                         if isinstance(b, dict) and b.get("type") == "tool_use"]
                                if tools:
                                    entry["tools"] = tools
                                txt = sum(len(b.get("text") or "") for b in blk
                                          if isinstance(b, dict) and b.get("type") == "text")
                                if txt:
                                    entry["text_chars"] = txt
                        timeline.append(entry)
            rec["timeline"] = timeline
            rec["n_events"] = len(timeline)
            if done_msg:
                rec["answer"] = str(done_msg.get("result") or done_msg.get("answer") or "")
                rec["num_turns"] = done_msg.get("num_turns")
                rec["duration_ms"] = done_msg.get("duration_ms")
                rec["cost_usd"] = done_msg.get("total_cost_usd")
                rec["session_id"] = done_msg.get("sessionId") or done_msg.get("session_id")
    except urllib.error.HTTPError as e:
        rec.update({"http": e.code, "error": e.read().decode("utf-8", "replace")[:400]})
    except Exception as e:  # noqa: BLE001
        rec.update({"http": None, "error": f"{type(e).__name__}: {str(e)[:250]}"})
    rec["wall_s"] = round(time.time() - t0, 1)
    save(tag, rec)
    err = f" ERR={str(rec.get('error'))[:120]}" if rec.get("error") else ""
    tl = ""
    if rec.get("timeline"):
        seq = [e.get("tool") or ",".join(e.get("tools") or [])
               for e in rec["timeline"] if e.get("tool") or e.get("tools")]
        tl = f" tools={seq[:14]}"
    log(f"  {tag}: wall={rec['wall_s']}s dur={rec.get('duration_ms')}ms "
        f"turns={rec.get('num_turns')} ans={len(rec.get('answer') or '')}ch{err}{tl}")
    return rec


# ────────────────────────── 质量门 ──────────────────────────

def gold_check(rec: dict, gold_substrs: list, require_citation: bool = True,
               citation_of: str = "") -> dict:
    text = (rec.get("reply") or rec.get("answer") or "")
    hits = {g: (g.lower() in text.lower()) for g in gold_substrs}
    cited = (not require_citation) or any(
        k in text for k in (citation_of, ".md", "《", "出处", "来源"))
    ok = all(hits.values()) and cited
    return {"pass": ok, "gold_hits": hits, "citation": cited, "answer_chars": len(text)}


def refusal_check(rec: dict) -> dict:
    text = (rec.get("reply") or rec.get("answer") or "")
    hit = any(m in text for m in REFUSAL_MARKERS)
    return {"pass": hit and 0 < len(text) < 4000, "refusal_marker": hit,
            "answer_chars": len(text)}


# ────────────────────────── 场景 ──────────────────────────

def main() -> int:
    only = set(sys.argv[1:]) or None
    global KB_CS, KB_EARTH, KB_ID, KB_NAME
    log(f"=== fulltest 启动 · KB={KB_NAME} ===")

    _, cat = req_json("GET", f"{WEB}/api/kb/catalog")
    for k in cat.get("knowledgeBases") or []:
        if k.get("name") == "计算机与人工智能":
            KB_CS = k.get("kbId")
        if k.get("name") == "自然科学与地球科学":
            KB_EARTH = k.get("kbId")
    log(f"KB_CS={KB_CS} KB_EARTH={KB_EARTH}")

    # 沙箱库: 断点续跑复用同一库
    kb_file = HERE / "sandbox-kb.json"
    if kb_file.exists():
        d = json.loads(kb_file.read_text(encoding="utf-8"))
        KB_NAME, KB_ID = d["name"], d["id"]
        log(f"沙箱库(复用): {KB_NAME} id={KB_ID}")
    else:
        _, created = req_json("POST", f"{WEB}/api/kb/create",
                              {"name": KB_NAME, "description": KB_DESC})
        KB_ID = (created.get("knowledgeBase") or {}).get("id", "")
        kb_file.write_text(json.dumps({"name": KB_NAME, "id": KB_ID}),
                           encoding="utf-8")
        log(f"沙箱库(新建): {KB_NAME} id={KB_ID} ok={created.get('success')}")

    def run(tag, fn):
        if only and tag not in only:
            return
        if (HERE / f"{tag}.json").exists():
            log(f"-- {tag}: 已存在, 跳过 (断点续跑)")
            return
        log(f"── {tag} 开始")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log(f"  {tag}: RUNNER-ERROR {type(e).__name__}: {str(e)[:200]}")

    # ════ Stage A — agent/chat (AWS 集成面) ════
    def a1():
        rec = agent_chat(
            "在知识库中回答:语言模型是如何逐步学会事实知识的?请说明学习动力学的阶段划分、"
            "性能平台期对应的内部机制、数据分布不均衡的影响,以及为什么用微调向模型注入新知识会失败。"
            "请给出文档出处。", "a1_retrieval_hit")
        v = gold_check(rec, ["2503.21676", "平台期", "微调"], citation_of="2503.21676")
        save("a1_verdict", v)
        log(f"  a1 verdict: {json.dumps(v, ensure_ascii=False)}")

    def a2():
        rec = agent_chat(
            "Kubernetes Gateway API 的 canary 金丝雀发布流量切分应该如何配置?"
            "请给出知识库中的具体配置步骤和参数。", "a2_refusal")
        v = refusal_check(rec)
        save("a2_verdict", v)
        log(f"  a2 verdict: {json.dumps(v, ensure_ascii=False)}")

    def a3():
        rec = agent_chat(
            f"请在知识库「{KB_NAME}」中新建一篇文档《蓝鹊-47 试验记录》,内容如下(原样入库,"
            "标题做文档名):\n\n" + DOC1 + "\n入库完成后确认文档已建立并且向量索引就绪。",
            "a3_ingest")
        text = rec.get("reply") or ""
        ok = rec.get("http") == 200 and ("47.3" in text or "蓝鹊" in text)
        save("a3_verdict", {"pass": bool(ok), "reply_head": text[:300]})
        log(f"  a3 verdict: pass={ok}")

    def a4():
        rec = agent_chat(
            "青鸾-7 传感阵列第四标定段的谐振阈值是多少?漂移补偿系数是多少?负责人是谁?请给出文档出处。",
            "a4_post_ingest_recall")
        v = gold_check(rec, ["47.3", "0.0837", "沈砚"], citation_of="蓝鹊")
        save("a4_verdict", v)
        log(f"  a4 verdict: {json.dumps(v, ensure_ascii=False)}")

    def a5():
        rec = agent_chat(
            "CoRoT 卫星的系外行星计划有哪些科学目标?截至 2010 年夏共收集了多少条光变曲线?"
            "为什么 CoRoT-7b 这类超级地球只能在较亮恒星的光变曲线中发现?请给出文档出处。",
            "a5_crosskb_corot")
        v = gold_check(rec, ["1105.1887", "129,326"], citation_of="1105.1887")
        if not v["gold_hits"].get("129,326"):
            alt = "129326" in (rec.get("reply") or "").replace(",", "")
            v["gold_hits"]["129326(无逗号)"] = alt
            v["pass"] = v["gold_hits"].get("1105.1887") and alt and v["citation"]
        save("a5_verdict", v)
        log(f"  a5 verdict: {json.dumps(v, ensure_ascii=False)}")

    def a6():
        rec = agent_chat(
            f"请在知识库「{KB_NAME}」沉淀一条结构化经验:场景=第四标定段谐振漂移;"
            "问题=阈值漂移 0.4 MHz 导致锁定失稳;处置=启用 0.0837 漂移补偿系数并 24 小时内复测;"
            "教训=温漂必须在标定后 24 小时内复核。请告诉我这条经验的标题与 ID。",
            "a6_experience")
        save("a6_verdict", {"pass": rec.get("http") == 200 and bool(rec.get("reply")),
                            "reply_head": (rec.get("reply") or "")[:300]})
        try:
            _, gs = req_json("POST", f"{BACKEND}/api/v1/experience/global-search",
                             {"query": "谐振漂移 补偿", "top_k": 5})
            items = gs.get("results") or gs.get("hits") or []
            found = any("谐振漂移" in json.dumps(it, ensure_ascii=False) for it in items)
            save("a6_global_search", {"found": found, "n": len(items),
                                      "head": json.dumps(items[:2], ensure_ascii=False)[:400]})
            log(f"  a6 global-search: found={found} n={len(items)}")
        except Exception as e:  # noqa: BLE001
            log(f"  a6 global-search ERR {str(e)[:150]}")

    def a7():
        rec = agent_chat(
            f"两步操作知识库「{KB_NAME}」:\n"
            "1. 新建文档《灰隼-19 校准报告》,内容如下(原样入库):\n\n" + DOC2 + "\n"
            "2. 在知识图谱中为《蓝鹊-47 试验记录》与《灰隼-19 校准报告》建立 related_to 关联,"
            "理由=同属第四批标定;然后查询图谱确认这条关联已存在。",
            "a7_ingest2_graph")
        text = rec.get("reply") or ""
        v = {"pass": rec.get("http") == 200 and ("0.0042" in text or "灰隼" in text),
             "reply_head": text[:300]}
        save("a7_verdict", v)
        log(f"  a7 verdict: pass={v['pass']}")

    run("a1", a1)
    run("a2", a2)
    run("a3", a3)
    run("a4", a4)
    run("a5", a5)
    run("a6", a6)
    run("a7", a7)

    # ════ Stage B — engine=claude ════
    def q1_prompt():
        return ("在指定知识库中回答:语言模型是如何逐步学会事实知识的?学习动力学分几个阶段,"
                "性能平台期的内部机制是什么,数据分布不均衡有何影响,为什么微调注入新知识会失败?给出出处。")

    def b_a():
        rec = harness_chat(q1_prompt(), "b_a_vector_pinned", engine="claude",
                           kb_ids=[KB_CS], stream=True)
        v = gold_check(rec, ["2503.21676", "平台期"], citation_of="2503.21676")
        v["stream_events"] = rec.get("n_events")
        save("b_a_verdict", v)
        log(f"  b_a verdict: {json.dumps(v, ensure_ascii=False)}")

    def b_b():
        rec = harness_chat(
            "全库逐级检索回答:CoRoT 卫星的系外行星计划有哪些科学目标?截至 2010 年夏共收集了多少条"
            "光变曲线?请给出文档出处。", "b_b_librarian_allkb", engine="claude", kb_ids=[])
        v = gold_check(rec, ["1105.1887"], citation_of="1105.1887")
        save("b_b_verdict", v)
        log(f"  b_b verdict: {json.dumps(v, ensure_ascii=False)}")

    def b_c():
        rec = harness_chat(
            "请用混合检索(hybrid:先向量宽网 kb_search_two_stage,若证据不足再走图书管理员逐级检索)"
            "回答:在分子科学的机器学习中,Noé 等人的综述《Machine learning for molecular simulation》"
            "与深度空间学习+分子振动数据增强方法各自如何应对数据稀缺?后者在聚酰胺纳滤膜实验中把相对误差"
            "和决定系数分别改善到多少?请给出两篇文档出处。",
            "b_c_hybrid_native", engine="claude", permission_mode="bypassPermissions")
        v = gold_check(rec, ["6.71", "0.75"], citation_of="1911.02792")
        save("b_c_verdict", v)
        log(f"  b_c verdict: {json.dumps(v, ensure_ascii=False)}")

    def b_in():
        rec = harness_chat(
            f"请在知识库「{KB_NAME}」(kbId={KB_ID})新建文档《灰隼-19 校准报告-B》,内容如下:\n\n"
            + DOC2 + "\n完成后确认向量索引就绪。",
            "b_in_ingest_claude", engine="claude", kb_ids=[KB_ID],
            permission_mode="bypassPermissions")
        save("b_in_verdict", {"pass": rec.get("http") == 200 and bool(rec.get("answer")),
                              "head": (rec.get("answer") or "")[:300]})
        log(f"  b_in verdict: pass={rec.get('http') == 200}")

    def b_vf():
        rec = harness_chat("灰隼-19 陀螺零偏稳定性标定值是多少?温补点是多少?校准人是谁?给出出处。",
                           "b_vf_verify_claude", engine="claude", kb_ids=[KB_ID])
        v = gold_check(rec, ["0.0042", "19.6"], citation_of="灰隼")
        save("b_vf_verdict", v)
        log(f"  b_vf verdict: {json.dumps(v, ensure_ascii=False)}")

    run("b_a", b_a)
    run("b_b", b_b)
    run("b_c", b_c)
    run("b_in", b_in)
    run("b_vf", b_vf)

    def b_in2():
        """b_in 撞上查重(内容与 a7 相同被 dedup), 此场景用唯一内容验证干净 create 路径."""
        rec = harness_chat(
            f"请在知识库「{KB_NAME}」(kbId={KB_ID})新建文档《沧羽-88 振动台验收单》,内容如下:\n\n"
            + "# 沧羽-88 振动台验收单\n\n随机振动试验量级 6.81 Grms。\n"
            "主振方向: Y 轴。验收工程师: 白棠。\n\n完成后确认向量索引就绪。",
            "b_in2_ingest_claude_unique", engine="claude", kb_ids=[KB_ID],
            permission_mode="bypassPermissions")
        save("b_in2_verdict", {"pass": rec.get("http") == 200 and bool(rec.get("answer")),
                               "head": (rec.get("answer") or "")[:300]})
        log(f"  b_in2 verdict: pass={rec.get('http') == 200}")

    run("b_in2", b_in2)

    # ════ Stage C — engine=omp ════
    def c_a():
        rec = harness_chat(q1_prompt(), "c_a_vector_pinned", engine="omp",
                           kb_ids=[KB_CS])
        v = gold_check(rec, ["2503.21676", "平台期"], citation_of="2503.21676")
        save("c_a_verdict", v)
        log(f"  c_a verdict: {json.dumps(v, ensure_ascii=False)}")

    def c_b():
        rec = harness_chat(
            "全库逐级检索回答:CoRoT 卫星的系外行星计划有哪些科学目标?截至 2010 年夏共收集了多少条"
            "光变曲线?请给出文档出处。", "c_b_librarian_allkb", engine="omp", kb_ids=[])
        v = gold_check(rec, ["1105.1887"], citation_of="1105.1887")
        save("c_b_verdict", v)
        log(f"  c_b verdict: {json.dumps(v, ensure_ascii=False)}")

    def c_c():
        rec = harness_chat(
            "请用混合检索(hybrid:先向量宽网,若证据不足再走图书管理员逐级检索)回答:"
            "在分子科学的机器学习中,Noé 等人的综述与深度空间学习+分子振动数据增强方法各自如何应对数据稀缺?"
            "后者在聚酰胺纳滤膜实验中把相对误差和决定系数分别改善到多少?请给出两篇文档出处。",
            "c_c_hybrid_native", engine="omp", permission_mode="bypassPermissions")
        v = gold_check(rec, ["6.71", "0.75"], citation_of="1911.02792")
        save("c_c_verdict", v)
        log(f"  c_c verdict: {json.dumps(v, ensure_ascii=False)}")

    def c_in():
        rec = harness_chat(
            f"请在知识库「{KB_NAME}」(kbId={KB_ID})新建文档《青鸾-7 复测纪要-C》,内容如下:\n\n"
            + "# 青鸾-7 复测纪要\n\n第四标定段复测谐振阈值 47.4 MHz,漂移 +0.1 MHz,"
            "已启用补偿系数 0.0837。复测人: 沈砚。\n\n完成后确认向量索引就绪。",
            "c_in_ingest_omp", engine="omp", kb_ids=[KB_ID],
            permission_mode="bypassPermissions")
        save("c_in_verdict", {"pass": rec.get("http") == 200 and bool(rec.get("answer")),
                              "head": (rec.get("answer") or "")[:300]})
        log(f"  c_in verdict: pass={rec.get('http') == 200}")

    def c_vf():
        rec = harness_chat("青鸾-7 复测纪要里复测的谐振阈值是多少?漂移了多少?复测人是谁?给出出处。",
                           "c_vf_verify_omp", engine="omp", kb_ids=[KB_ID])
        v = gold_check(rec, ["47.4", "0.0837"], citation_of="青鸾")
        save("c_vf_verdict", v)
        log(f"  c_vf verdict: {json.dumps(v, ensure_ascii=False)}")

    run("c_a", c_a)
    run("c_b", c_b)
    run("c_c", c_c)
    run("c_in", c_in)
    run("c_vf", c_vf)

    log("=== fulltest 全部场景执行完毕 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
