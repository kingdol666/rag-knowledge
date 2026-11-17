# Build ladder-experiment reply viz bundle (READ-ONLY; prints HTML to stdout).
# Sources: review/experiment-redesign-20261101/artifacts/final_bench/
import json
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "artifacts", "final_bench")

REPLY_ARMS = ["A0h", "A0f", "A0", "PD"]
TRUNC = 1100
OUT_NAME = "ladder-experiment-replies.html"


def load(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    responses = {a: load("responses/" + a + ".json") for a in REPLY_ARMS}
    traces = load("s4_traces_final.json")
    attr = load("attribution_a0_misses.json")

    qids = list(responses["A0h"].keys())
    for a in REPLY_ARMS:
        assert set(responses[a].keys()) == set(qids), a + " qid mismatch"

    questions = {}
    for qid in qids:
        it = responses["A0h"][qid]
        questions[qid] = {
            "q": it["question"],
            "gold_doc": it.get("gold_doc"),
            "gold_evidence": it.get("gold_evidence"),
            "refusal": bool(it.get("is_refusal")),
        }

    replies = {}
    for a in REPLY_ARMS:
        arm_r = {}
        for qid in qids:
            it = responses[a][qid]
            tr = next(t for t in traces[a] if t["qid"] == qid)
            text = it.get("response_text") or ""
            n = len(text)
            arm_r[qid] = {
                "hit": bool(tr.get("gold_hit")),  # authoritative: final trace grading
                "refusal": bool(it.get("is_refusal")),
                "top1": it.get("top1"),
                "bytes": tr.get("bytes_ingested"),
                "tool_s": tr.get("tool_seconds"),
                "digest_s": tr.get("llm_digest_seconds"),
                "calls": tr.get("calls"),
                "route": tr.get("route_correct") if "route_correct" in tr else None,
                "note": it.get("response_note"),
                "text": text[:TRUNC],
                "cut": n > TRUNC,
                "len": n,
            }
        replies[a] = arm_r

    attr_rows = {}
    for r in attr["rows"]:
        short = "judge 未进包" if r["cls"] == "judge-miss" else "窗口截断"
        attr_rows[r["qid"]] = {"short": short}

    arms = [
        {"id": "A1-readall", "desc": "逐篇通读（上界）", "hits": 72, "n": 72, "rate": 1.0,
         "ci": [0.9493, 1.0], "p": "<0.0001 *", "bytes": 24313972, "tool_s": 253.7, "digest_s": 6078.5,
         "routing": "n/a", "gate": "n/a", "upper_bound": True},
        {"id": "A0h", "desc": "逐级+chunk窗口并集", "hits": 52, "n": 72, "rate": 0.722222,
         "ci": [0.609536, 0.812397], "p": "0.0001 *", "bytes": 309143, "tool_s": 13.8, "digest_s": 77.3,
         "routing": "72/72", "gate": "0/4", "recommended": True},
        {"id": "PD", "desc": "精确逐文档（无导航）", "hits": 46, "n": 72, "rate": 0.638889,
         "ci": [0.523525, 0.740183], "p": "0.0039 *", "bytes": 308166, "tool_s": 13.6, "digest_s": 77.0,
         "routing": "n/a", "gate": "0/4"},
        {"id": "A0f", "desc": "逐级+判卷全窗250K", "hits": 45, "n": 72, "rate": 0.625,
         "ci": [0.509529, 0.727808], "p": "0.0078 *", "bytes": 303449, "tool_s": 13.0, "digest_s": 75.9,
         "routing": "72/72", "gate": "0/4"},
        {"id": "A1b", "desc": "十库向量并集直搜", "hits": 39, "n": 72, "rate": 0.541667,
         "ci": [0.427399, 0.651714], "p": "0.6875 ns", "bytes": 38464, "tool_s": 10.8, "digest_s": 9.6,
         "routing": "n/a", "gate": "0/4"},
        {"id": "A0", "desc": "基线逐级（判卷窗40K）", "hits": 37, "n": 72, "rate": 0.513889,
         "ci": [0.400698, 0.625673], "p": "baseline", "bytes": 31409, "tool_s": 16.3, "digest_s": 7.9,
         "routing": "72/72", "gate": "2/4"},
        {"id": "A3", "desc": "无描述层", "hits": 33, "n": 72, "rate": 0.458333,
         "ci": [0.348286, 0.572601], "p": "只引定性", "bytes": 23461, "tool_s": 7.8, "digest_s": 5.9,
         "routing": "37/72", "gate": "0/4"},
        {"id": "A2", "desc": "无证据门", "hits": 25, "n": 72, "rate": 0.347222,
         "ci": [0.247527, 0.462387], "p": "0.0227 *（劣化）", "bytes": 1787, "tool_s": 0.8, "digest_s": 0.5,
         "routing": "n/a", "gate": "n/a"},
    ]

    data = {
        "meta": {
            "line": "2026-11-11 内容层优化轮（终版主总表）· 语料 10 库 MD语料-* 共 138 卷 · 72 gold + 4 拒答探针 · 判卷 = 本地 Laya 引擎 · 数据源 review/experiment-redesign-20261101/artifacts/final_bench/ · R3 复现（11-12）主结论可信",
            "stats": [
                {"label": "A0h 命中率（推荐主臂）", "value": "72.2%", "sub": "52/72 · vs A0 +20.8pp · p=0.0001"},
                {"label": "回归数", "value": "0", "sub": "A0f/A0h/PD 对 A0 零回归"},
                {"label": "A0h vs PD", "value": "7 : 1", "sub": "方向性优势 p=0.0703 · PD 多付 10× 搜索调用"},
                {"label": "R3 复现一致率", "value": "98.6%", "sub": "A0h 71/72 · A1b/A2 100% 零翻转"},
            ],
        },
        "floor": {"bm25": 0.60},
        "arms": arms,
        "attribution": {
            "a0": {"judge": 30, "window": 5},
            "fixes": {"A0f": {"total": 8, "window": 1, "judge": 7},
                      "A0h": {"total": 15, "window": 2, "judge": 13},
                      "PD": {"total": 9, "window": 1, "judge": 8}},
        },
        "replyArms": REPLY_ARMS,
        "qids": qids, "questions": questions, "replies": replies,
    }

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")  # JSON-equivalent escape; kills <html>/<script> lookalikes in reply text
    sk = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skeleton.html")
    with open(sk, encoding="utf-8") as f:
        html = f.read()
    assert "/*__DATA__*/" in html
    html = html.replace("/*__DATA__*/", "window.DATA_LADDER = " + payload + ";")
    sys.stdout.write(html)
    sys.stderr.write("BUILD OK qids=" + str(len(qids)) + "\n")


if __name__ == "__main__":
    main()
