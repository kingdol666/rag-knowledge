#!/usr/bin/env python3
"""Six-run orchestrator: 2 queries x 3 retrieval modes through the chat API."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_chat import run_chat  # noqa: E402

Q1 = "How does InstructDS generate high-quality query-based dialogue summaries?"
Q2 = "用机器学习从电子健康记录预测中风，哪些风险因素影响最大？"

PROMPTS = {
    # ── Mode A: optimized vector wide-net + Laya/Jev verify gate ──
    "q1-A": f"""检索任务（模式A：向量宽网 + Laya/Jev 核验门）。严格按以下步骤执行：
1. 运行命令：python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "{Q1} InstructDS dialogue summarization query-based instruction tuning" --top-k 30 --engine laya --require-real --output tmp/vector-jev-q1.json
2. 读取 tmp/vector-jev-q1.json，基于 result_list 与 evidence_pack 中全部幸存文档的内容回答问题（知识增强：引用具体文档名与数据）。若 evidence_pack 的头部窗口未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 补读幸存文档的相关部分再作答。
3. 按五段式输出：## Search Paths（含 kb_search_vector 与 jev/Laya 判决统计）/ ## Answer / ## Sources（列出 result_list 全部文档及分数）/ ## Confidence（含 "after Jev verification" 字样）/ ## Blind Spots (Cross-Library Perspective)。
问题：{Q1}""",
    "q2-A": f"""检索任务（模式A：向量宽网 + Laya/Jev 核验门）。严格按以下步骤执行：
1. 运行命令：python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "{Q2} stroke prediction electronic health records machine learning risk factors" --top-k 30 --engine laya --require-real --output tmp/vector-jev-q2.json
2. 读取 tmp/vector-jev-q2.json，基于 result_list 与 evidence_pack 中全部幸存文档的内容回答问题（知识增强：引用具体文档名与数据）。若 evidence_pack 的头部窗口未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 补读幸存文档的相关部分再作答。
3. 按五段式输出：## Search Paths（含 kb_search_vector 与 jev/Laya 判决统计）/ ## Answer / ## Sources（列出 result_list 全部文档及分数）/ ## Confidence（含 "after Jev verification" 字样）/ ## Blind Spots (Cross-Library Perspective)。
问题：{Q2}""",
    # ── Mode B: librarian complete recall, Jev yes-all ──
    "q1-B": f"""检索任务（模式B：图书管理员全量召回，Jev yes 全收）。按 skill://knowledgebase-librarian 执行：
L0 用 mcp__kb-mcp__kb_list(lightweight=true) 读全部知识库描述 → L1 标记每个库 relevant/possible/out_of_scope（保留 relevant+possible）→ L2 对每个保留库用 mcp__kb-mcp__kb_get_documents(lightweight=true) 读全部文档描述 → L3 描述可信度检查（样板/空洞/矛盾 → 读正文验证）→ L4 对描述匹配的候选文档用 kb_doc_read 分页读全正文并结构化分段，写成候选 JSON（含 kb_id/doc_path/part/section/start_line/end_line/text）→ L5 运行 python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py --engine laya --input tmp/candidates-q1.json --output tmp/judged-q1.json --require-real（yes=score>=threshold 的段全部保留，不再筛选）→ L6 从全部幸存段作答。
输出五段式：## Search Paths（L0-L5 各层计数 + Jev backend/criterion/threshold）/ ## Answer / ## Sources（文档名+行号+Jev分）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)（含未读文档数）。
问题：{Q1}""",
    "q2-B": f"""检索任务（模式B：图书管理员全量召回，Jev yes 全收）。按 skill://knowledgebase-librarian 执行：
L0 用 mcp__kb-mcp__kb_list(lightweight=true) 读全部知识库描述 → L1 标记每个库 relevant/possible/out_of_scope（保留 relevant+possible）→ L2 对每个保留库用 mcp__kb-mcp__kb_get_documents(lightweight=true) 读全部文档描述 → L3 描述可信度检查（样板/空洞/矛盾 → 读正文验证）→ L4 对描述匹配的候选文档用 kb_doc_read 分页读全正文并结构化分段，写成候选 JSON（含 kb_id/doc_path/part/section/start_line/end_line/text）→ L5 运行 python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py --engine laya --input tmp/candidates-q2.json --output tmp/judged-q2.json --require-real（yes=score>=threshold 的段全部保留，不再筛选）→ L6 从全部幸存段作答。
输出五段式：## Search Paths（L0-L5 各层计数 + Jev backend/criterion/threshold）/ ## Answer / ## Sources（文档名+行号+Jev分）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)（含未读文档数）。
问题：{Q2}""",
    # ── Mode C: parallel hybrid (trimmed budget to fit the turn window) ──
    "q1-C": f"""检索任务（模式C：并行混合双道）。严格按以下步骤执行：
1. 运行命令：python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py --query "{Q1}" --extra-terms "instructds 对话摘要 指令 查询 数据合成" --peek-heads --top-k-floor 5 --lane-agreement --doc-budget 12 --peek-limit 120 --require-real --output tmp/hybrid-q1.json
2. 读取 tmp/hybrid-q1.json，基于 result_list 与 evidence_pack 回答（知识增强，引用文档名与分数）。若 evidence_pack 未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 补读幸存文档。
3. 五段式输出：## Search Paths（双道统计 + Laya 判决数）/ ## Answer / ## Sources（文档名+lane+分数）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q1}""",
    "q2-C": f"""检索任务（模式C：并行混合双道）。严格按以下步骤执行：
1. 运行命令：python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py --query "{Q2}" --extra-terms "stroke EHR 中风 电子健康记录 机器学习 风险因素 PCA" --peek-heads --top-k-floor 5 --lane-agreement --doc-budget 12 --peek-limit 120 --require-real --output tmp/hybrid-q2.json
2. 读取 tmp/hybrid-q2.json，基于 result_list 与 evidence_pack 回答（知识增强，引用文档名与分数）。若 evidence_pack 未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 补读幸存文档。
3. 五段式输出：## Search Paths（双道统计 + Laya 判决数）/ ## Answer / ## Sources（文档名+lane+分数）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q2}""",
}

ORDER = ["q1-A", "q2-A", "q1-B", "q2-B", "q1-C", "q2-C"]
MAX_TURNS = {"q1-A": 30, "q2-A": 30, "q1-B": 80, "q2-B": 80, "q1-C": 30, "q2-C": 30}

if __name__ == "__main__":
    only = sys.argv[1:] or ORDER
    for tag in only:
        print(f"=== RUN {tag} start ===", flush=True)
        try:
            # engine=claude: the OMP provider key is over its 12h budget today
            # (429 ExceededBudget, $70.31/$70.00); the Claude Agent SDK engine
            # is the harness proven working by native-search E2E.
            run_chat(PROMPTS[tag], tag, engine="claude",
                     permission_mode="bypassPermissions",
                     max_turns=MAX_TURNS[tag], timeout_ms=900_000)
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"RUN_ERROR {tag}: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
