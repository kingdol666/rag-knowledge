# -*- coding: utf-8 -*-
"""Weicheng 3-mode test prompts (2026-09-26). Data only.

Q1 enumeration over 4 women (parts 1-8, full-recall test).
Q2 pinpoint: the fortress-besieged proverb — who quoted it, what occasion,
what saying; must filter the frontmatter doc and must NOT leak P&P KB.
"""

Q1 = "按出场顺序列出小说《围城》中方鸿渐先后与哪几位女性有过感情纠葛，每个阶段的关键情节与结局分别是什么"
KW1 = "方鸿渐 鲍小姐 苏文纨 唐晓芙 孙柔嘉 赵辛楣 感情 求婚 结婚 围城"
Q2 = "围城这个比喻在小说《围城》中出自哪里？是谁在什么场合说的？引用的是什么谚语？这个比喻在小说结尾是否再次出现？"
KW2 = "围城 比喻 谚语 法国 苏文纨 褚慎明 罗素 鸟笼 城里的人 城外的人 老钟 结尾"

A1 = f"""检索任务（模式A：向量宽网 + Laya/Jev 核验门）。严格按 skill://knowledgebase-search 的流程执行：
1. 运行命令：python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "{Q1} {KW1}" --top-k 30 --engine laya --require-real --output tmp/vector-jev-wc1.json
2. 读取 tmp/vector-jev-wc1.json，基于 result_list 与 evidence_pack 回答。若 evidence_pack 的头部窗口未覆盖答案细节，用 mcp__kb-mcp__kb_doc_read 分页补读幸存文档（单次读取可能 truncated=true，深部内容必须用 offset/totalLines 续读）。
3. 按五段式输出：## Search Paths（含 kb_search_vector 与 jev/Laya 判决统计）/ ## Answer（按出场顺序列出方鸿渐的每段感情：对象、关键情节、结局）/ ## Sources（result_list 全部文档及分数）/ ## Confidence（含 "after Jev verification" 字样）/ ## Blind Spots (Cross-Library Perspective)。
问题：{Q1}"""

A2 = f"""检索任务（模式A：向量宽网 + Laya/Jev 核验门）。严格按 skill://knowledgebase-search 的流程执行：
1. 运行命令：python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "{Q2} {KW2}" --top-k 30 --engine laya --require-real --output tmp/vector-jev-wc2.json
2. 读取 tmp/vector-jev-wc2.json，基于 result_list 与 evidence_pack 回答；引用原文需逐字核对时用 mcp__kb-mcp__kb_doc_read 分页续读（truncated=true 时用 offset/totalLines 续读）。
3. 按五段式输出：## Search Paths（kb_search_vector 与 jev/Laya 判决统计）/ ## Answer（比喻出处：谁、什么场合、什么谚语、结尾是否再现）/ ## Sources（result_list 全部文档及分数）/ ## Confidence（含 "after Jev verification" 字样）/ ## Blind Spots (Cross-Library Perspective)。
问题：{Q2}"""

B1 = f"""检索任务（模式B：图书管理员全量召回，Jev yes 全收）。严格按 skill://knowledgebase-librarian 的 L0→L6 流程执行：
L0 用 mcp__kb-mcp__kb_list(lightweight=true) 读全部知识库描述 → L1 标记每个库 relevant/possible/out_of_scope（保留 relevant+possible；本题与小说《围城》相关）→ L2 对每个保留库用 mcp__kb-mcp__kb_get_documents(lightweight=true) 读全部文档描述（按 ICD 多维描述定位相关 part，排除无关文档如出版说明）→ L3 描述信任检查（样板/空洞/矛盾 → 读正文验证）→ L4 对候选文档用 kb_doc_read 分页读全正文（⚠️ 单次读取可能 truncated=true——枚举证据可能位于文档深处，必须用 offset/totalLines 续读直到覆盖全文档），结构化分段写成候选 JSON（kb_id/doc_path/part/section/start_line/end_line/text）→ L5 运行 python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py --engine laya --input tmp/candidates-wc1.json --output tmp/judged-wc1.json --require-real（yes=score>=threshold 的段全部保留，不再筛选）→ L6 从全部幸存段作答（这是枚举题，不要遗漏任何一位女性）。
输出五段式：## Search Paths（L0-L5 各层计数 + Jev backend/criterion/threshold）/ ## Answer（方鸿渐每段感情按出场顺序：对象、关键情节、结局）/ ## Sources（文档名+行号+Jev分）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)（含未读/被排除文档）。
问题：{Q1}"""

B2 = f"""检索任务（模式B：图书管理员全量召回，Jev yes 全收）。严格按 skill://knowledgebase-librarian 的 L0→L6 流程执行：
L0 用 mcp__kb-mcp__kb_list(lightweight=true) 读全部知识库描述 → L1 标记 relevant/possible/out_of_scope（保留 relevant+possible；本题关于《围城》中"围城"比喻的出处）→ L2 对保留库用 mcp__kb-mcp__kb_get_documents(lightweight=true) 读全部文档描述（按 ICD 描述定位，排除出版说明等无关文档）→ L3 描述信任检查 → L4 对候选文档用 kb_doc_read 分页读全正文（truncated=true 时用 offset/totalLines 续读到全覆盖），分段写候选 JSON（kb_id/doc_path/part/section/start_line/end_line/text）→ L5 运行 python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py --engine laya --input tmp/candidates-wc2.json --output tmp/judged-wc2.json --require-real（yes 段全收）→ L6 从全部幸存段作答。
输出五段式：## Search Paths（L0-L5 计数 + Jev backend/criterion/threshold）/ ## Answer（"围城"比喻：谁说的、什么场合、什么谚语、结尾是否再现，附短引文）/ ## Sources（文档名+行号+Jev分）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q2}"""

C1 = f"""检索任务（模式C：并行混合双道）。严格按 skill://knowledgebase-hybrid 执行：
1. 运行命令：python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py --query "{Q1}" --extra-terms "{KW1} 感情线 出场顺序 结局 求婚 订婚" --peek-heads --top-k-floor 5 --lane-agreement --doc-budget 20 --stem-max-parts 8 --peek-limit 100 --require-real --output tmp/hybrid-wc1.json
2. 读取 tmp/hybrid-wc1.json，基于 result_list 与 evidence_pack 回答；证据不足时用 mcp__kb-mcp__kb_doc_read 分页补读幸存文档（truncated 时用 offset 续读）。
3. 五段式输出：## Search Paths（双道统计 + Laya 判决数）/ ## Answer（方鸿渐每段感情按出场顺序：对象、关键情节、结局）/ ## Sources（文档名+lane+分数）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q1}"""

C2 = f"""检索任务（模式C：并行混合双道）。严格按 skill://knowledgebase-hybrid 执行：
1. 运行命令：python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py --query "{Q2}" --extra-terms "{KW2} 比喻出处 场合 谚语 结尾再现 围城 比喻 谚语 法国 苏文纨 褚慎明 罗素 鸟笼 城里的人 城外的人 老钟 结尾" --peek-heads --top-k-floor 5 --lane-agreement --doc-budget 20 --stem-max-parts 8 --peek-limit 100 --require-real --output tmp/hybrid-wc2.json
2. 读取 tmp/hybrid-wc2.json，基于 result_list 与 evidence_pack 回答；需要逐字核对原文时用 mcp__kb-mcp__kb_doc_read 分页补读（truncated 时用 offset 续读）。
3. 五段式输出：## Search Paths（双道统计 + Laya 判决数）/ ## Answer（比喻出处：谁、什么场合、什么谚语、结尾是否再现）/ ## Sources（文档名+lane+分数）/ ## Confidence / ## Blind Spots (Cross-Library Perspective)。
问题：{Q2}"""

PROMPTS = {"wc-A1": A1, "wc-A2": A2, "wc-B1": B1, "wc-B2": B2, "wc-C1": C1, "wc-C2": C2}
