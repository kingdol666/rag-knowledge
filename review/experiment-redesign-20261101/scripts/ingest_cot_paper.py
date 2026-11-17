# -*- coding: utf-8 -*-
"""Chain-of-Thought 论文入库（A5 入库 + A3b 标签 + A6 索引图谱 + A3c-R 双通道自检）。
描述按 A3c 五要素、由各卷实际正文标题与摘要归纳（见 DESCRIPTIONS 注释）。"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
KB = "b1199132-e4d4-4305-8c2e-82dc1753b0ba"  # 计算机与人工智能
OUT = ROOT / "backend" / "output" / "1095bf3be7c2"
ART = ROOT / "review" / "experiment-redesign-20261101" / "artifacts" / "single-doc-e2e"

# A3c 五要素描述：范围标签 + 内容归纳（基于各卷真实标题结构与摘要正文，非来源标签）
DESCRIPTIONS = {
    1: "【Part 1/6 · Title–§6】Chain-of-Thought Prompting（Wei et al., Google Brain）正文主体："
       "提出思维链提示——在 few-shot 示范中给出中间推理步骤， solely attention 之外的纯 prompting 方法；"
       "在 PaLM 540B/GPT-3/LaMDA 三大模型上测算术（GSM8K/SVAMP/MAWPS/ASDiv）、常识（CSQA/StrategyQA）与"
       "符号推理（末字母/硬币翻转）；含算术消融（去公式/去变量/去思维链）、标注者与示例顺序鲁棒性、"
       "涌现性讨论（性能增益仅在大模型出现）。可答：方法定义、三任务主结果数字、消融结论、鲁棒性与讨论。",
    2: "【Part 2/6 · §7–A.1】同论文相关工作与结论：思维链与 prompting/中间步骤现线的关系脉络、结论章；"
       "附录 FAQ 首则 A.1（为何增大模型规模才让思维链有效——小模型给出流畅但不正确的推理链）。",
    3: "【Part 3/6 · A.2–C.3】同论文附录：FAQ（A.2 prompt 工程的作用、A.3 适配什么任务、A.4 为何仅给公式不够）、"
       "附录 B 全部实验结果表（三模型×全任务逐点数字）、附录 C 扩展相关工作（C.1 prompting、C.2 自然语言解释、"
       "C.3 思维链与验证）。可答：完整结果数值检索、FAQ 级问题。",
    4: "【Part 4/6 · C.4–E】同论文附录：C.4 数值与逻辑推理相关工作、C.5 中间语言步骤；附录 D 附加分析"
       "（D.1 正确思维链分析、D.2 错误思维链分析、D.3 鲁棒性附加分析——exemplar 数量/顺序/格式）、附录 E 复现细节。",
    5: "【Part 5/6 · F】同论文附录 F：全部任务的输入/输出示例——各算术/常识/符号任务的完整 few-shot prompt"
       "（含思维链示范全文）与模型输出样例。可答：prompt 具体写法、示范格式、各任务示例。",
    6: "【Part 6/6 · G–H】同论文附录尾部：附录 H 备选标注者（Alternate Annotators for MWP）实验——"
       "不同标注者撰写思维链对结果的影响。可答：标注者敏感性实验细节。",
}
TAGS = ["chain-of-thought", "few-shot-prompting", "emergent-abilities",
        "arithmetic-reasoning", "language-model-evaluation"]


def mc(tool, args, timeout=300):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", str(ROOT / "backend"), "python",
         str(ROOT / "scripts" / "mcp_call.py"), tool, json.dumps(args), "--raw"],
        capture_output=True, text=True, timeout=timeout)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:200]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    docs = []
    for i in range(1, 7):
        f = OUT / f"cot_paper (part {i} of 6).md"
        content = f.read_text(encoding="utf-8")
        name = f"Chain-of-Thought Prompting (part {i} of 6).md"
        r = mc("kb_doc_create", {"kb_id": KB, "name": name, "content": content,
                                 "description": DESCRIPTIONS[i]})
        ok = bool(r.get("success") or r.get("files"))
        path = (r.get("files") or [{}])[0].get("path") or f"计算机与人工智能/{name}"
        print(f"create part{i}: ok={ok} path={path[:70]}", flush=True)
        docs.append((i, path))
        time.sleep(1)
    for i, path in docs:
        r = mc("kb_doc_update_tags", {"kb_id": KB, "doc_path": path, "tags": TAGS})
        print(f"tags part{i}: {r.get('success')}", flush=True)
    for i, path in docs:
        r = mc("kb_index_document", {"kb_id": KB, "doc_path": path})
        vi = r.get("vector_index") or {}
        print(f"index part{i}: chunks={vi.get('total_chunks')} coll={str(vi.get('collection'))[:24]}", flush=True)
    r = mc("kb_graph_build", {"kb_id": KB, "force": True})
    tid = r.get("task_id")
    print("graph task:", tid, flush=True)
    if tid:
        for _ in range(40):
            time.sleep(5)
            ts = mc("kb_task_status", {"task_id": tid})
            if str(ts.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                print("graph done", flush=True)
                break
    # A3c-R 双通道自检：描述维度措辞 + 改写问句
    for label, tool, q in (
            ("kw通道", "kb_search", "思维链提示 中间推理步骤 涌现 模型规模"),
            ("vec通道", "kb_search_vector", "Why does chain-of-thought prompting only work for large models?")):
        if tool == "kb_search":
            d = mc(tool, {"query": q, "top_k": 5})
            hits = d.get("hits") or []
        else:
            d = mc(tool, {"query": q, "top_k": 5, "kb_ids": [KB], "threshold": 0.3})
            hits = d.get("results") or []
        cot = [h for h in hits if "Chain-of-Thought" in str(h.get("doc_path") or h.get("docName") or "")]
        print(f"A3c-R {label}: hits={len(hits)} cot_rank={[n for n,h in enumerate(hits,1) if 'Chain-of-Thought' in str(h.get('doc_path') or h.get('docName') or '')]}", flush=True)
    (ART / "ingest_result.json").write_text(
        json.dumps({"docs": [{"part": i, "path": p} for i, p in docs]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("ingest complete -> ingest_result.json", flush=True)


if __name__ == "__main__":
    main()
