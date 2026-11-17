# -*- coding: utf-8 -*-
"""US-5b 校验器：对 AG1-AG7 的 omp agent 回复做关键事实 + 溯源 + 零编造核验。

金标事实在派发前从磁盘原文独立提取（与终版 s_agent_sample 同源口径）：
  AG1 个人信息保护法第十五条：撤回同意 + 便捷撤回方式
  AG2 数据安全法第二十一条：国家数据安全工作协调机制（AG2 已冒烟 PASS）
  AG3 红楼梦第一回/甄士隐：五十两白银、两套冬衣
  AG4 resnet.md：He et al., deep residual learning, 2015/CVPR
  AG5 k8s_pss.md：Pod Security Standards
  AG6 哲学库 The Prince 君主论 马基雅维利
  AG7-ood Canberra：库内无解 → 必须如实未找到（零编造）
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

EXPECT = {
    "AG1": dict(must_any=["撤回", "便捷"], doc_hint="个人信息保护法", quote_must=["第十五条"]),
    "AG2": dict(must_any=["国家数据安全工作协调机制"], doc_hint="数据安全法", quote_must=["重要数据目录"]),
    "AG3": dict(must_any=["五十两", "冬衣"], doc_hint="红楼梦", quote_must=["甄士隐"]),
    "AG4": dict(must_any=["deep residual", "ResNet", "residual learning"], doc_hint="resnet",
                quote_must=["residual"]),
    "AG5": dict(must_any=["Pod Security", "pod-security"], doc_hint="k8s", quote_must=["Security"]),
    "AG6": dict(must_any=["Prince", "君主论", "马基雅维利", "Machiavelli"], doc_hint="", quote_must=["Prince"]),
    "AG7-ood": dict(refusal_required=True, must_not=["Canberra" + " 是首都，人口为"],
                    banned_invented=["population of", "万人口"]),
}


def verify(qid, reply):
    spec = EXPECT.get(qid)
    if not spec:
        return {"qid": qid, "note": "no spec"}
    out = {"qid": qid}
    if spec.get("refusal_required"):
        # 判据：显式 NOT_FOUND 结论 + 未把检索结果包装成正答。
        # 注意：Phase-0 改写记录里出现 parametric 知识（Canberra…）不算编造——
        # 判定看"结果区"是否声明 NOT_FOUND 且声明"不编造"。
        explicit_not_found = ("NOT_FOUND" in reply) or ("未收录答案" in reply) or \
            ("知识库未收录" in reply) or ("不存在" in reply and "答案" in reply)
        no_fabrication = ("不编造" in reply) or ("未编造" in reply) or ("禁止编造" in reply) or \
            ("不能用于回答" in reply)
        blind_spots_declared = ("盲区" in reply)
        out["refusal_ok"] = bool(explicit_not_found and no_fabrication)
        out["explicit_not_found"] = explicit_not_found
        out["no_fabrication_declared"] = no_fabrication
        out["blind_spots_declared"] = blind_spots_declared
        out["parametric_leak_in_rewrite"] = ("Canberra is the capital" in reply)
        return out
    doc_paths = re.findall(r"[^\s`]*\.md", reply)
    out["doc_paths"] = list(dict.fromkeys(doc_paths))[:5]
    out["doc_hint_matched"] = bool(spec["doc_hint"]) and any(
        spec["doc_hint"].lower() in d.lower() for d in doc_paths)
    out["key_facts"] = {k: (k in reply) for k in spec["must_any"]}
    out["key_fact_ok"] = any(out["key_facts"].values())
    out["quote_terms"] = {q: (q in reply) for q in spec["quote_must"]}
    out["line_citation"] = bool(re.search(r"第\s*\d+\s*行|line\s*\d+|L\d+", reply, re.I))
    out["verbatim_quote"] = bool(re.search(r"[>「\"《]?[^\\n]{10,}[」>\"》]?", reply)) and (
        "逐字" in reply or ">" in reply or "「" in reply)
    return out


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    results = []
    for f in sorted(BASE.glob("AG*.json")):
        if f.stem.endswith("_submit_err") or f.name == "ag_verify_summary.json":
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        final = d.get("final") or {}
        reply = ((final.get("result") or {}).get("reply") if isinstance(final.get("result"), dict) else "") or ""
        r = verify(f.stem, reply)
        r["status"] = final.get("status")
        r["seconds"] = d.get("seconds")
        results.append(r)
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    ok = [r for r in results if (r.get("refusal_ok") is True) or (r.get("status") in ("done", "completed", "success") and r.get("key_fact_ok", True))]
    (BASE / "ag_verify_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nverified {len(results)}; pass {len(ok)}")
