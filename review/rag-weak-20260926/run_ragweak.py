#!/usr/bin/env python3
"""RAG-weak three-mode test runner (2026-09-26).

Query designed to hit vector-RAG failure modes: enumeration over 26 parts,
Chinese question vs English prose, deep-scene beyond the single-read window,
empty-body doc at part 22, nested splits. Gold (corpus-grounded):
  G1 Collins->Elizabeth (ch19, part 8, rejected)
  G2 Darcy->Elizabeth 1st (ch34, part 13 DEEP ~L234+, "In vain have I struggled")
  G3 Darcy->Elizabeth 2nd (ch58, part 24, accepted)
  G4 (edge) Bingley->Jane (part 23, description-level)
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# reuse the SSRF-guarded SSE runner; its OUT dir is bound to the copied module's
# location, so import the file content by exec to rebind OUT here — simpler: copy
# the module's functions but keep its guard_url/load_token.
sys.path.insert(0, str(HERE.parent / "three-mode-chat-20260926"))
import run_chat as rc  # noqa: E402
rc.OUT = HERE  # artifacts land beside THIS script

Q = "列出《傲慢与偏见》小说中所有发生求婚的情节场景（谁向谁求婚、结果如何），按故事顺序排列"
KW = "pride and prejudice proposal marriage propose Collins Darcy Elizabeth chapter"

PROMPTS = {
    "rw-A": f"""检索任务（模式A：向量宽网 + Laya/Jev 核验门）。严格按 skill://knowledgebase-search 的流程执行：
1. 运行命令：python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "{Q} {KW}" --top-k 30 --engine laya --require-real --output tmp/vector-jev-ragweak.json
2. 读取 tmp/vector-jev-ragweak.json，基于 result_list 与 evidence_pack 回答。若 evidence_pack 的头部窗口未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 分页补读幸存文档（单次读取可能 truncated=true，深部内容必须用 offset/totalLines 续读）。
3. 按五段式输出：## Search Paths（含 kb_search_vector 与 jev/Laya 判决统计）/ ## Answer（列出所有求婚场景：谁向谁、结果、按故事顺序）/ ## Sources（result_list 全部文档及分数）/ ## Confidence（含 "after Jev verification" 字样）/ ## Blind Spots (Cross-Library Perspective)。
问题：{Q}""",
    "rw-B": f"""检索任务（模式B：图书管理员全量召回，Jev yes 全收）。严格按 skill://knowledgebase-librarian 的 L0→L6 流程执行：
L0 用 mcp__kb-mcp__kb_list(lightweight=true) 读全部知识库描述 → L1 标记每个库 relevant/possible/out_of_scope（保留 relevant+possible；本题与小说《傲慢与偏见》相关）→ L2 对每个保留库用 mcp__kb-mcp__kb_get_documents(lightweight=true) 读全部文档描述（⚠️ part 1 与 part 22 被嵌套拆分为 (part k of 2) 子文档，注意识别）→ L3 描述信任检查（样板/空洞/矛盾 → 读正文验证）→ L4 对候选文档用 kb_doc_read 分页读全正文（⚠️ 单次读取可能 truncated=true——答案证据可能位于文档深处，必须用 offset/totalLines 续读直到覆盖全文档），结构化分段写成候选 JSON（kb_id/doc_path/part/section/start_line/end_line/text）→ L5 运行 python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py --engine laya --input tmp/candidates-ragweak.json --output tmp/judged-ragweak.json --require-real（yes=score>=threshold 的段全部保留，不再筛选）→ L6 从全部幸存段作答（这是枚举题，不要遗漏任何场景）。
输出五段式：## Search Paths（L0-L5 各层计数 + Jev backend/criterion/threshold）/ ## Answer（全部求婚场景按序：谁向谁、结果）/ ## Sources（文档名+行号+Jev分）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)（含未读/空正文文档）。
问题：{Q}""",
    "rw-C": f"""检索任务（模式C：并行混合双道）。严格按 skill://knowledgebase-hybrid 执行：
1. 运行命令：python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py --query "列出《傲慢与偏见》中所有求婚情节 谁向谁求婚 结果 按故事顺序" --extra-terms "pride and prejudice proposal propose marriage Collins Darcy Elizabeth Charlotte Jane Bingley 求婚 傲慢与偏见 达西 吉英" --peek-heads --top-k-floor 5 --lane-agreement --doc-budget 20 --stem-max-parts 26 --peek-limit 100 --require-real --output tmp/hybrid-ragweak.json
2. 读取 tmp/hybrid-ragweak.json，基于 result_list 与 evidence_pack 回答；证据不足时用 mcp__kb-mcp__kb_doc_read 分页补读幸存文档（truncated 时用 offset 续读）。
3. 五段式输出：## Search Paths（双道统计 + Laya 判决数）/ ## Answer（全部求婚场景按序）/ ## Sources（文档名+lane+分数）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q}""",
}

if __name__ == "__main__":
    only = sys.argv[1:] or ["rw-A", "rw-B", "rw-C"]
    for tag in only:
        print(f"=== RUN {tag} start ===", flush=True)
        try:
            rc.run_chat(PROMPTS[tag], tag, engine="claude",
                        permission_mode="bypassPermissions",
                        max_turns=80, timeout_ms=900_000)
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"RUN_ERROR {tag}: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
