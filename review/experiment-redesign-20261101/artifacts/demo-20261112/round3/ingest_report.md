# Round3 入库报告（死栈自愈 + skill 全链实测）

- 日期：2026-11-12
- 执行：入库 subagent（ingest skill 全链：Step 0 → A2 parse → A5 save → A6 index → 回查）
- MCP 调用方式：仓库根下 `python -X utf8 scripts/mcp_call.py <tool> '<json>' --raw`

## Step 0 — 栈连接硬约束（ensure_stack 自愈）

原始输出已存档：`ensure_stack_output.txt`（本目录）

```
[check] backend=False web=False mcp_kblist=False catalog=0
[backend] healthy=True
[web] healthy=True
[verify] e2e_vector_search=True
STACK-READY
```

- 初始检测：三端口全 False（backend / web / MCP kb_list 均不可达，catalog=0），确认死栈。
- 自愈：脚本按 SOP 自动拉起 backend → web；kb-mcp 通道由端到端真实向量检索验证兜底（`e2e_vector_search=True`，非仅端口探活）。
- 退出码 0 + `STACK-READY`，23:00:41 完成，允许进入后续步骤。

## 文献 1：distilbert.pdf（PDF → MinerU parse_doc 链）

| 项 | 结果 |
|---|---|
| 目标库 | 演示-DistilBERT-R3 `4aa38d9f-ef74-403d-9ece-a16ddef5fa13`（空库，docCount=0，A0 去重无对象） |
| 解析工具 | `parse_doc(use_ocr=true)` → task_id `af12a8ff1ca6`，23:01:00 → 23:01:23，**耗时 23s** |
| 解析质量（A2-Q） | 通过：标题/作者/摘要/公式（LaTeX）完整，无 OCR 乱码、无二进制残留、无空壳标题 |
| 文档名 | `distilbert.md`（path `演示-DistilBERT-R3\distilbert.md`） |
| 字数 | 解析 19,350 字符（落盘 19,360 字节）；5 页 PDF / 5 张图全部随入库复制进库 |
| 拆分（A2.5） | 不需要（19,350 < 60,000 单卷上限） |
| 入库 | `kb_doc_save_parsed(parent_id, task_id, description)` 23:01:57，savedCount=1 |
| 描述 | DistilBERT 论文全文（Sanh 等，Hugging Face，arXiv 1910.01108）：预训练阶段知识蒸馏，triple loss 压缩 BERT base 40%、推理快 60%、保留 97% 语言理解能力；含学生初始化与 GLUE 评测、on-device 实验。英文。 |
| 索引（A6-V） | auto-index task `9db466068df0`，1s 完成：collection=`kb_4aa38d9f-ef74-403d-9ece-a16ddef5fa13`（UUID 匹配，非孤儿），**chunks=47**，bge-m3 |
| 向量回查 | 命中：query "How does knowledge distillation compress BERT…?" → top3 全部 `演示-DistilBERT-R3/distilbert.md`，最高分 **0.711**，degraded=false |

## 文献 2：wiki_rag.md（MD 直入链）

| 项 | 结果 |
|---|---|
| 目标库 | 演示-WikiRAG-R3 `2e42b329-0ee1-43fa-a11d-d4e02fe701a2`（空库，docCount=0，A0 去重无对象） |
| 前置 | 读源文件确认内容干净（Wikipedia RAG 条目全文）；10865 字符 |
| 入库 | `kb_doc_create(kb_id, name, content, description, tags)` 23:03:33，success=true（payload 经 `@file` 传参规避单引号转义） |
| 文档名 | `wiki_rag.md`（path `演示-WikiRAG-R3\wiki_rag.md`） |
| 字数 | source_chars=10,865 |
| 描述 | Wikipedia《Retrieval-augmented generation》条目全文：RAG 让 LLM 先从向量库检索外部文档再生成回答以缓解幻觉，涵盖 embedding 与向量数据库、SPLADE/Late Interaction 检索优化、Retro 重设计语言模型与混合检索、RAG poisoning 风险。英文。 |
| 标签（3 个） | `retrieval-augmented-generation` / `向量检索` / `大语言模型`（`_tags_applied: true`） |
| 索引（A6-V） | auto-index task `63ba3f20758c`，1s 完成：collection=`kb_2e42b329-0ee1-43fa-a11d-d4e02fe701a2`（UUID 匹配），**chunks=25**，bge-m3 |
| 向量回查 | 命中：query "What is RAG and how does it reduce hallucinations…?" → top3 全部 `演示-WikiRAG-R3/wiki_rag.md`，最高分 **0.670**，degraded=false |

## 异常与处置

1. **死栈**：起步时三端口全 False —— 按 Step 0 由 ensure_stack 自动拉起并通过端到端向量检索验证，无需人工干预；输出原文已存档。
2. **bash 内联 JSON 引号风险**：wiki_rag.md 正文含大量单引号（"LLM's" 等），无法安全内联进单引号 JSON 参数 —— 改用 `mcp_call.py` 原生 `@file` 传参（脚本 68-70 行），payload 由临时脚本（系统临时目录）从源文件构造后删除使用，零转义损失。
3. **ensure_stack 输出无显式 "拉起 kb-mcp" 行**：仅见 [backend]/[web]/[verify] 三行 —— kb-mcp 通道以 `e2e_vector_search=True` 端到端验证兜底；后续全部 MCP 调用实际成功，通道无问题。
4. **环境旁观察（未触碰）**：kb_list 的 50 库中存在历史脏数据（`final-acceptance-standalone`/`r2-standalone` 描述乱码、部分库重复条目），与本任务无关。

## 结论

- 两文献均**入库成功且可检索**：chunks 47 / 25（均 ≥1），collection UUID 与库 UUID 匹配（无孤儿集合），向量回查双向命中。
- 全程无失败步骤、无谎报：Step 0 通过后方才作业，全部走 MCP 工具链，未绕过任何质量门。
