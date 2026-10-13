"""Chat-API three-mode system arms (added 2026-09-30).

The --retmodes arms exercise the retrieval SCRIPTS in subprocesses. These arms
exercise the SYSTEM ITSELF: every run goes through the official chat API
(`POST /api/claude/chat`, default NON-STREAM — one blocking JSON) with the
mode expressed exactly the way an external caller expresses it:

  mode A  pinned-KB vector fast lane   kbEnhanced=true, kbIds=[pin]
  mode B  all-KB librarian lane        kbEnhanced=true, kbIds=[]
  mode C  hybrid                       kbEnhanced=true, kbIds=[pin] + suffix

Tool gating (disallowedTools, lane instructions, MCP mounting) is the server's
job — that IS the execution flow under test. The arm verifies the caller-visible
contract: HTTP 200 + success + answer non-empty + answer-level gold marker
(found questions) or honest refusal (out-of-corpus questions).

Gates per (mode x question):
  found   : http_200 ∧ success ∧ answer_nonempty ∧ answer_marker_hit
  refusal : http_200 ∧ success ∧ refusal_marker ∧ (wall_s recorded)
Arm JSON is written per run; CHAT-MODES-COMPARE.md is the report.
"""
from __future__ import annotations

import json
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from chat_tracks import CHAT, OPENER, _token, guard_url  # noqa: E401

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent

# live five-shelf KB ids (verified 2026-09-30 via kb_list)
KB_CS = "b1199132-e4d4-4305-8c2e-82dc1753b0ba"    # 计算机与人工智能
KB_LIFE = "b28f0a25-1e1d-40ad-96b8-61bd2b093a28"  # 生命科学与医学

HYBRID_SUFFIX = ("【混合检索模式】先用 kb_search_two_stage / kb_search_vector 宽网检索"
                 "并用 kb_laya_judge 判定；若幸存证据不足以回答，再用 kb_list → "
                 "kb_get_documents 逐级检索补齐后才作答。")

REFUSAL_MARKERS = (
    "无法", "没有找到", "未找到", "未能找到", "未检索到", "没有检索到", "不存在",
    "无法回答", "无法作答", "无法据此",
    "not found", "no document", "no content", "cannot answer",
    "unable to answer", "does not exist", "no evidence", "cannot find",
    "not covered", "outside the corpus", "not in the library",
    "无对应内容", "没有覆盖",
    # 2026-10-13 弃答盲测补充: 真实弃答措辞的其余常见形态（均无歧义的否定结论短语）
    "未发现", "没有任何关于", "没有任何一个", "没有相关", "未收录", "没有收录",
    "无从查证", "查无", "not_found", "no relevant",
)

# Same gold documents as the --retmodes q1/q2 (cross-comparable), plus one
# out-of-corpus question borrowed from qa_quick10 QK10 (zero-fabrication).
QUESTIONS: dict[str, dict] = {
    "cm1": {
        "qid": "cm1",
        "expect": "found",
        "pin": KB_CS,
        "pin_name": "计算机与人工智能",
        "text": ("How does InstructDS generate high-quality query-based dialogue "
                 "summaries? (InstructDS dialogue summarization query-based "
                 "instruction tuning data synthesis)"),
        "answer_markers": ["instructds"],
        "gold_doc_substr": "instructive-dialogue-summarization",
        "gold_id": "2310.10981",
    },
    "cm2": {
        "qid": "cm2",
        "expect": "found",
        "pin": KB_LIFE,
        "pin_name": "生命科学与医学",
        "text": ("基于电子健康记录（EHR）数据用机器学习算法预测中风/卒中风险："
                 "关键风险因素及其影响分析 (stroke prediction electronic health "
                 "records machine learning risk factors)"),
        "answer_markers": ["stroke"],
        "gold_doc_substr": "stroke-from-electronic-health",
        "gold_id": "1904.11280",
    },
    "cm3": {
        "qid": "cm3",
        "expect": "refusal",
        "pin": KB_CS,
        "pin_name": "计算机与人工智能",
        "text": ("How does the Herbert-Moulton collider benchmark quantify "
                 "detector drift in particle physics experiments?"),
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
    # ---- cm4-cm9 (2026-10-13 honest-refusal battery; ground truth machine-verified
    # via kb_search metadata scan: 番茄炒蛋/红烧肉/电力变压器/LoRA/铁观音/Zephyr-7 have
    # NO dedicated doc in the library; LoRA metadata hits are chemistry false positives;
    # power-systems papers cover grid-integration & disturbance, NOT transformer selection) ----
    "cm4": {
        "qid": "cm4",
        "expect": "found",
        "pin": KB_CS,
        "pin_name": "计算机与人工智能",
        "text": "transformer是什么？",
        "answer_markers": ["attention", "vaswani"],
        "gold_doc_substr": "attention",
        "gold_id": "1706.03762",
    },
    "cm5": {
        "qid": "cm5",
        "expect": "refusal",
        "pin": "455137b4-a0be-46ed-acf5-d8b475dc5d70",  # demo-qa (random real-world content)
        "pin_name": "demo-qa-20260927",
        "text": "红烧肉怎么做？",
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
    "cm6": {
        "qid": "cm6",
        "expect": "refusal",
        "pin": "455137b4-a0be-46ed-acf5-d8b475dc5d70",
        "pin_name": "demo-qa-20260927",
        "text": "番茄炒蛋怎么做？",
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
    "cm7": {
        "qid": "cm7",
        "expect": "refusal",
        "pin": "8fa4db59-adde-4d6d-9fdb-2c375400e631",  # 工程与能源 (power-systems papers exist)
        "pin_name": "工程与能源",
        "text": "transformer 变压器在电力系统中如何选型？",
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
    "cm8": {
        "qid": "cm8",
        "expect": "refusal",
        "pin": KB_CS,
        "pin_name": "计算机与人工智能",
        "text": "如何用 LoRA 微调大语言模型？",
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
    "cm9": {
        "qid": "cm9",
        "expect": "refusal",
        "pin": "455137b4-a0be-46ed-acf5-d8b475dc5d70",
        "pin_name": "demo-qa-20260927",
        "text": "Zephyr-7 无线充电协议的帧结构是什么？",
        "answer_markers": [],
        "gold_doc_substr": "",
        "gold_id": "",
    },
}

TIMEOUT_S = 480


# 结论先行窗口 (2026-10-12): 拒答结论必在答案开头; 全文扫描会把正当 found
# 答案中段的讨论性字眼("无法从单一特征推断"等)误判成拒答。
REFUSAL_WINDOW = 500


def _is_refusal(answer: str) -> bool:
    low = (answer or "")[:REFUSAL_WINDOW].lower()
    return any(m in low for m in REFUSAL_MARKERS)


def run_chat_mode(mode: str, question: dict, max_turns: int = 18) -> dict:
    """One non-stream chat-API call in the given system mode. Never raises."""
    prompt = question["text"]
    kb_ids = [question["pin"]] if mode in ("A", "C") else []
    if mode == "C":
        prompt = f"{prompt} {HYBRID_SUFFIX}"
    body = {
        "prompt": prompt,
        "kbEnhanced": True,
        "kbIds": kb_ids,
        "engine": "claude",
        "permissionMode": "default",
        "maxTurns": max_turns,
    }
    t0 = time.time()
    http = 0
    payload: dict = {}
    err = ""
    try:
        guard_url(CHAT)
        req = urllib.request.Request(
            CHAT, method="POST",
            data=json.dumps(body).encode("utf-8"))
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {_token()}")
        with OPENER.open(req, timeout=TIMEOUT_S) as resp:
            http = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        http = e.code
        err = f"HTTP {e.code}: {e.read()[:200]}"
    except Exception as e:  # noqa: BLE001 — 记录后作为失败臂返回
        err = f"{type(e).__name__}: {str(e)[:200]}"
    wall = round(time.time() - t0, 1)
    answer = str(payload.get("answer") or "")
    ok_call = http == 200 and payload.get("success") is True and bool(answer.strip())
    markers = [m for m in question["answer_markers"] if m in answer.lower()]
    # 拒答优先判定 (2026-10-12): found 题的答案若构成如实拒答(拒答文本会复述
    # 问题关键词导致 marker 命中, 例: "未找到任何 InstructDS 相关内容"),
    # 必须判 FAIL 而非借问题回显假阳性通过。
    refused = _is_refusal(answer) if answer else False
    if question["expect"] == "found":
        passed = ok_call and bool(markers) and not refused
    else:
        passed = ok_call and refused
    return {
        "mode": mode, "qid": question["qid"], "expect": question["expect"],
        "kb_ids": kb_ids,
        "http": http, "success": payload.get("success"),
        "wall_s": wall, "duration_ms": payload.get("duration_ms"),
        "turns": payload.get("num_turns"), "cost_usd": payload.get("total_cost_usd"),
        "session_id": payload.get("sessionId"),
        "answer_chars": len(answer),
        "answer_markers_hit": markers,
        "refusal": _is_refusal(answer) if answer else None,
        "gate_passed": passed, "via": "chat-api-mode",
        "error": payload.get("error") or err,
        "answer_head": answer[:600],
    }


def verify_gate(arm: dict, question: dict) -> dict:
    checks = {
        "http_200": arm.get("http") == 200,
        "success": arm.get("success") is True,
        "answer_nonempty": (arm.get("answer_chars") or 0) > 0,
    }
    if question["expect"] == "found":
        checks["answer_marker_hit"] = bool(arm.get("answer_markers_hit"))
        checks["not_refusal"] = arm.get("refusal") is not True
    else:
        checks["honest_refusal"] = arm.get("refusal") is True
    return {"passed": all(checks.values()), "checks": checks}


def run_all(out_dir: Path, modes: tuple = ("A", "B", "C"),
            qids: tuple = ("cm1", "cm2", "cm3")) -> dict:
    """Run the full matrix, persist per-run JSON + chatmodes.json + report."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for mode in modes:
        for qid in qids:
            q = QUESTIONS[qid]
            print(f"[exp:chatmodes] mode {mode} × {qid} ({q['expect']}) …", flush=True)
            arm = run_chat_mode(mode, q)
            gate = verify_gate(arm, q)
            arm["gate"] = gate
            rows.append({k: arm[k] for k in (
                "mode", "qid", "expect", "http", "success", "wall_s", "turns",
                "cost_usd", "session_id", "answer_chars", "answer_markers_hit",
                "refusal", "gate_passed", "error")})
            out_dir.mkdir(parents=True, exist_ok=True)  # 外部清理护栏
            (out_dir / f"arm_{mode}-{qid}.json").write_text(
                json.dumps(arm, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[exp:chatmodes]   → {arm['wall_s']}s http={arm['http']} "
                  f"gate={'✅' if gate['passed'] else '❌'} "
                  f"turns={arm['turns']} sess={str(arm['session_id'])[:8]}", flush=True)
    (out_dir / "chatmodes.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "CHAT-MODES-COMPARE.md").write_text(
        render_report(rows, out_dir), encoding="utf-8")
    n_pass = sum(1 for r in rows if r["gate_passed"])
    print(f"[exp:chatmodes] gates {n_pass}/{len(rows)} → "
          f"{out_dir / 'CHAT-MODES-COMPARE.md'}", flush=True)
    return {"rows": rows, "n_pass": n_pass}


def render_report(rows: list[dict], out_dir: Path) -> str:
    L = ["# Chat-API 三模式系统臂对照（当前系统官方执行流）", "",
         f"- Run: `{out_dir.name}` · 生成: "
         f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
         "- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· "
         "`kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建",
         "- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; "
         "refusal=HTTP200∧success∧如实拒答标记", "",
         "| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |",
         "|---|---|---|---:|---:|:--:|---|"]
    for r in rows:
        L.append(f"| {r['mode']} | {r['qid']} | {r['expect']} | {r['wall_s']} "
                 f"| {r['turns']} | {'✅' if r['gate_passed'] else '❌'} "
                 f"| `{str(r['session_id'])[:8]}` |")
    L += ["", "## 逐臂回答摘录", ""]
    for qid in ("cm1", "cm2", "cm3"):
        for mode in ("A", "B", "C"):
            f = out_dir / f"arm_{mode}-{qid}.json"
            if not f.exists():
                continue
            arm = json.loads(f.read_text(encoding="utf-8"))
            head = (arm.get("answer_head") or arm.get("error") or "").replace("\n", " ")
            L += [f"### {mode} × {qid}", "",
                  f"> {head[:400]}", ""]
    return "\n".join(L) + "\n"
