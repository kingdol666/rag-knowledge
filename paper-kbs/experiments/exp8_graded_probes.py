#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 8 — graded abstention probes (review R3 MAJOR: the hazardous middle
between covered and out-of-corpus was sampled at n=1).

Tiers:
  PA1-PA3  partial coverage -- the corpus holds adjacent mechanisms
           (背板/交联度/醋酸 appear in corpus docs) but not the asked object
           (rework decision, aluminum frames, backsheet bonding);
  AB1-AB3  absent -- factory fire acceptance, dormitory rules, hydraulic-oil
           service: nothing in the corpus relates.

Tool layer: one kb_hybrid_search(enable_judge=true) per probe (verdict/kept
behavior). Agent layer: the three partial probes through the deployed chat
API, hybrid arm, pinned to the two knowledge bases that hold the adjacent
content -- then a manual audit of whether the answer discloses the gap or
speculates. Transcripts saved for release.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import CHAT_URL, OPENER, RESULTS, McpClient, get_token

KB = json.loads((RESULTS / "kb_id_map.json").read_text(encoding="utf-8"))

PROBES = [
    {"qid": "PA1", "tier": "partial",
     "query": "背板与EVA的层压粘结界面发生脱层，是什么原因造成的？",
     "pins": [KB["光伏组件失效分析库"], KB["薄膜工艺知识库"]]},
    {"qid": "PA2", "tier": "partial",
     "query": "检测发现EVA交联度不足，可以把组件拆开重新层压返工吗？",
     "pins": [KB["光伏组件失效分析库"], KB["薄膜工艺知识库"]]},
    {"qid": "PA3", "tier": "partial",
     "query": "EVA老化产生的醋酸会腐蚀组件的铝边框吗？",
     "pins": [KB["光伏组件失效分析库"], KB["薄膜工艺知识库"]]},
    {"qid": "AB1", "tier": "absent",
     "query": "工厂消防验收的流程和所需材料有哪些？",
     "pins": []},
    {"qid": "AB2", "tier": "absent",
     "query": "员工宿舍的管理规定是怎样的？",
     "pins": []},
    {"qid": "AB3", "tier": "absent",
     "query": "注塑机液压油多久需要更换一次？",
     "pins": []},
]

HYBRID_SUFFIX = ("【混合检索模式】先用 kb_hybrid_search 混合检索（单次调用，服务端完成"
                 "合并、判卷与切割），然后读取判卷存活的文档作答。")


def tool_layer(mc: McpClient, probe: dict) -> dict:
    r = mc.call("kb_hybrid_search",
                {"query": probe["query"], "candidate_cap": 12,
                 "enable_judge": True}, timeout=300)
    kept = (r.get("cut", {}) or {}).get("kept", []) or []
    return {
        "qid": probe["qid"], "tier": probe["tier"],
        "merged_n": len((r.get("merge", {}) or {}).get("judged_candidates", []) or []),
        "kept_n": len(kept),
        "kept_scores": [round(float(k.get("score") or 0), 3) for k in kept],
        "read_top5": [k["doc_path"].replace("\\", "/") for k in kept[:5]],
        "elapsed_s": r.get("elapsed_s"),
    }


def agent_layer(probe: dict) -> dict:
    body = {"prompt": f"{probe['query']} {HYBRID_SUFFIX}",
            "kbEnhanced": True, "kbIds": probe["pins"],
            "engine": "omp", "permissionMode": "default", "maxTurns": 20}
    import urllib.request
    token = get_token()
    for attempt in (1, 2):
        t0 = time.time()
        try:
            req = urllib.request.Request(CHAT_URL, method="POST",
                                         data=json.dumps(body).encode("utf-8"))
            req.add_header("Content-Type", "application/json")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with OPENER.open(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            answer = payload.get("answer") or payload.get("content") or ""
            return {"qid": probe["qid"], "tier": probe["tier"],
                    "wall_s": round(time.time() - t0, 1),
                    "turns": payload.get("turns"),
                    "answer_head": answer[:1500],
                    "answer_len": len(answer)}
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"qid": probe["qid"], "tier": probe["tier"],
                        "error": str(e)[:300]}
            time.sleep(3)
    return {}


def main() -> int:
    mc = McpClient()
    out = {"tool_layer": [], "agent_layer": []}
    for probe in PROBES:
        t = tool_layer(mc, probe)
        out["tool_layer"].append(t)
        print(f"[tool] {t['qid']} ({t['tier']}): merged={t['merged_n']} "
              f"kept={t['kept_n']} scores={t['kept_scores'][:4]}", flush=True)
    for probe in PROBES:
        if probe["tier"] != "partial":
            continue
        a = agent_layer(probe)
        out["agent_layer"].append(a)
        head = (a.get("answer_head") or a.get("error", ""))[:150]
        print(f"[agent] {a['qid']}: {a.get('wall_s')}s turns={a.get('turns')} "
              f"head={head}", flush=True)
    outp = RESULTS / "exp8_graded_probes.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print("wrote", outp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
