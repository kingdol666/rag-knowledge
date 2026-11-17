# 实机演示汇整：批量解析入库 · 直接入库 · 检索增强查询（2026-11-17）

环境：master@b8767fdf，三服务常驻（web 6789 / backend 8770 / kb-mcp 8000），MinerU 本地引擎热态。
演示库（保留供浏览）：**实机演示-多路入库-20261117-232320**（kb_id `19d9dc0c-6b63-4cae-b782-e0a2500ebc52`，5 文档 / 479 chunks）。
全部数字来自当次真实运行；工件：`batch_demo.py` + `batch_demo_results.json`。

## 1. 批量解析入库（真实批量 SSE 端点，3 篇并发）

`POST /api/v1/batch/parse/file/vt/stream` — MinerU 并发任务、SSE 进度流（start→progress→complete）：

| 论文 | 解析结果 | 入库后检索 rank1（独特探针查询） |
|---|---|---|
| attention_is_all_you_need.pdf | 42,545 字符 / 14 图 | 命中本篇 score **0.707**（"scaled dot-product attention multi-head"） |
| rag_lewis2020.pdf | 72,610 字符 / 16 图 | 命中本篇 score **0.702**（"non-parametric memory retrieval augmented generation"） |
| llama.pdf | 96,133 字符 / 20 图 | 命中本篇 score **0.652**（"LLaMA open foundation model training tokens"） |

**批量总耗时 38.7s（3/3 成功，5 个 SSE 事件）**；逐篇 save_parsed（A5 门）→ 逐篇独特查询 rank1 全部命中目标文档。

## 2. 不解析直接入库（kb_doc_create，真实仓库文档）

| 文档 | 大小 | 入库后检索 rank1 |
|---|---|---|
| docs/ARCHITECTURE.md → 平台架构说明-ARCHITECTURE.md | 15,329 字符 | 命中本篇 score **0.717**（"平台三服务架构 FastAPI Nuxt MCP"） |
| README.md → 平台总览-README.md | 28,692 字符 | 命中本篇 score **0.633**（"知识库 树索引 knowledge-base 配置"） |

直入路径无解析开销、同步自动索引（此前微测 0.7s 可检索），本轮两篇检索均即时命中。

## 3. 汇总

| 路径 | 文档数 | 处理耗时 | 产出 |
|---|---|---|---|
| 批量解析入库（MinerU OCR+结构化） | 3 篇 PDF（211K 字符 / 50 图） | 38.7s 并发 | Markdown+图片资产，逐篇可检索 |
| 直接入库（原文直存） | 2 篇 MD（44K 字符） | 秒级 | 原文直存，即时可检索 |
| **合计** | **5 文档 / 479 chunks** | — | 单库统一检索面 |

## 4. 检索增强查询（web chat SSE，claude 引擎，kbEnhanced + 指定演示库）

| 查询 | 耗时 | 工具调用 | 回答要点（真实输出摘要） |
|---|---|---|---|
| EN：RAG (Lewis 2020) 结合哪两种记忆？两种变体？ | 249.7s | 4 | 正确答出「参数化记忆（预训练 seq2seq，BART）+ 非参数化记忆（Wikipedia 检索）」，RAG-Sequence / RAG-Token |
| ZH：平台由哪些服务组成、端口与职责？ | 566.2s | 7 | 正确答出「3 个长驻服务 + 1 个 MCP 工具层：Nuxt 3 Web（UI+代理）/ FastAPI 后端（解析/向量/图谱/经验/SOUL）/ MinerU OCR（子进程临时端口）」 |
| CROSS：自注意力 vs 检索机制的作用对比 | 311.0s | 5 | 「自注意力解决序列内部任意距离依赖建模与并行计算的架构效率问题；RAG 检索解决参数内知识无法更新、无法溯源、易幻觉的知识供给问题」+ 双向给出依据文档 |

## 5. 判定

- **16/16 检查全过**（kb_create、批量解析 3/3、逐篇 save_parsed 3、逐篇检索 3、直入 2、直入检索 2、库统计、RAG 3）。
- 两条入库路径均真实走通且检索面统一；回答层对解析类与直入类内容都能给出带出处的增强回答。
- 演示库与批量解析产物保留在系统中，可直接在 Web UI 复现以上任何一次提问。
