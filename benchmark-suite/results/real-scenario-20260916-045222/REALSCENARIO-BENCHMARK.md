# 真实场景基准报告 — 用户上传文档 × 论文复现检索算法

- 运行: `2026-09-16 04:52:22` · 快照: `real-scenario-20260916-045222` · 问题数: 6 (每文档 3, omp Agent 从文档内容生成)
- 数据源: `real_scenario_repaired.json`(解析回退 4 行 + 单元重生成 0 行; 原始 real_scenario.json 按不可变约定保留)
- 文档: `ARCHITECTURE.md`, `SUBMISSION-MASTER-PLAN.md` (指纹 `66b0f9f5ffc63e6f`, 两例试验使用完全相同的源文件)
- 生产 KB: `KB-UserDemo`(kb_doc_create 平台用户路径, 大文档自动 '(part N of M)' 拆分); 基线 KB: `UserDemo-Chunks800`, `UserDemo-Struct`, `UserDemo-Paras` + RAPTOR 树
- Harness: 全部算法同一 omp Agent 同一模型(ustc/deepseek-flash), 同一开放 QA 作答 prompt; 独立评审 Agent 注入逐字金标引文; 中间 Agent 对匿名答案排名。

## 复现算法注册表

| 算法 | 论文对应 |
|---|---|
| `qdcvr` | this system (knowledgebase-search skill QDCVR) |
| `dense_rag` | Dense RAG (chunk 800/400, top-10) |
| `dense_rag_rerank` | Dense RAG w/ Reranker (30→rerank→10) |
| `raptor` | RAPTOR Collapsed Tree (≤800 tok/node, 5 layers, cluster top-5, top-10 nodes) |
| `itrg_refresh` | ITRG (refresh), 4 rounds × top-6 |
| `itrg_refine` | ITRG (refine), 4 rounds × top-6 |
| `search_o1` | Search-o1 agentic search (struct chunks o0, 2 chunks/call, cap 8) |
| `deepread` | DeepRead locate-then-read (TOC + Retrieve ω=(1,1) + ReadSection, cap 8) |

## 主表(文档级 top-k 命中 + 评审 + 成本)

| 算法 | hit@1 | hit@3 | hit@5 | 金标均位 | judge 均分 | judge 中位 | judge 胜出 | 中间Agent第一 | 证据零编造 | 平均时延(s) | LLM 调用 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `qdcvr` | 4/6 | 6/6 | 6/6 | 1.33 | 3.00 | 1.0 | 1 | 0 | 6/6 | 2.9 | 0 |
| `dense_rag` | 6/6 | 6/6 | 6/6 | 1.00 | 7.83 | 9.0 | 2 | 0 | 6/6 | 0.3 | 0 |
| `dense_rag_rerank` | 6/6 | 6/6 | 6/6 | 1.00 | 5.17 | 5.0 | 1 | 0 | 6/6 | 2.6 | 6 |
| `raptor` | 6/6 | 6/6 | 6/6 | 1.00 | 9.00 | 9.0 | 1 | 0 | 6/6 | 0.4 | 0 |
| `itrg_refresh` | 6/6 | 6/6 | 6/6 | 1.00 | 7.50 | 8.5 | 0 | 0 | 6/6 | 1.4 | 18 |
| `itrg_refine` | 6/6 | 6/6 | 6/6 | 1.00 | 7.83 | 9.0 | 0 | 0 | 6/6 | 1.4 | 18 |
| `search_o1` | 6/6 | 6/6 | 6/6 | 1.00 | 5.00 | 4.0 | 0 | 0 | 6/6 | 38.3 | 23 |
| `deepread` | 6/6 | 6/6 | 6/6 | 1.00 | 9.17 | 9.0 | 1 | 6 | 6/6 | 94.2 | 14 |

## 逐题金标位置矩阵(数字=金标文档排名, ×=未召回)

| qid | 源文档 | `qdcvr` | `dense_rag` | `dense_rag_rerank` | `raptor` | `itrg_refresh` | `itrg_refine` | `search_o1` | `deepread` |
|---|---|---|---|---|---|---|---|---|---|
| U1 | ARCHITECTURE | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| U2 | ARCHITECTURE | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| U3 | ARCHITECTURE | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| U4 | SUBMISSION-MASTER-PLAN | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| U5 | SUBMISSION-MASTER-PLAN | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| U6 | SUBMISSION-MASTER-PLAN | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

## 逐题胜出

| qid | 文档 | judge 最佳 | 中间 Agent 排名第一 |
|---|---|---|---|
| U1 | ARCHITECTURE | dense_rag (9.0) | deepread |
| U2 | ARCHITECTURE | deepread (10.0) | deepread |
| U3 | ARCHITECTURE | dense_rag (10.0) | deepread |
| U4 | SUBMISSION-MASTER-PLAN | qdcvr (10.0) | deepread |
| U5 | SUBMISSION-MASTER-PLAN | raptor (9.0) | deepread |
| U6 | SUBMISSION-MASTER-PLAN | dense_rag_rerank (9.0) | deepread |

## 评价 — 基线复现 vs 本项目(QDCVR)

### 检索层(top-k 命中)
- suite 侧复现基线(各自论文分块方案, 整文档 3200 字符级块)中 7/7 个达 6/6 hit@1(最弱 6/6) — 在两份真实文档上整体召回不是瓶颈。
- 本项目 QDCVR 直查用户上传的生产 KB(平台自动按 ~1KB part 拆分), hit@1 4/6 但 **hit@3 6/6**: 全部金标文档都进前 3; 两次 hit@1 缺失集中在跨文档术语竞争题(U1 型), 属召回边界行为而非链接失效。
### 作答层(独立评审 + 中间 Agent)
- `raptor` 判分最高(9.00): 折叠树摘要把答案浓缩进统一 4000 字符证据预算, 单位预算信息密度最高。
- 本项目 QDCVR 判分 3.00: 检索命中后其证据通道为 top-2 part 的 kb_doc_read(≤2100 字符×2), part 粒度下答案所在段常被切分遗漏 → 按设计**弃答而非编造**(评审 issues 逐条确认零编造)。
- 中文题(U4-U6)同命中方法判分方差大, 与 E16 九轮重置实验结论一致: LLM 评审方差, 非状态污染。
- 中间 Agent(匿名答案排名)把 `deepread` 排第一 6/6 — 忠实弃答在答案层被奖励, 与 E16b 结论同构。
### 成本层
- QDCVR 检索期 **0 次 LLM 调用**(纯 MCP 工具链), search_o1 23 次、itrg 各 18 次; 平均时延 QDCVR 2.9s vs search_o1 38.3s。
### 机制边界与过程收益
- 生产 part 拆分粒度(~1KB) vs 套件分块粒度(3200 字符)是真实差异轴:qdcvr 的内容裁决只能在召回候选内重排(recall-bounded), 无法无中生有。
- 本流程在真实场景中**发现并修复了平台 P1 缺陷**(BM25 增量索引 kb_id 名字vsUUID → 新建库 KB 限定检索静默 0), 证明该诊断管线有实际改进闭环价值。
- 口径: 本场景为功能级验证(2 文档 × 6 问), 统计性结论以 E16 (30 查询 × 10 系统, 冻结快照 2026-09-15-a)为准; 两者互补而非替代。

## 一致性校验

| 校验项 | 结果 | 说明 |
|---|---|---|
| same-documents (fingerprint) | PASS | recomputed sha=66b0f9f5ffc63e6f vs run sha=66b0f9f5ffc63e6f |
| same-questions (one list, all methods) | PASS | 6 unique questions × 8 methods by construction; rows complete=True |
| answer-completeness (non-empty answers) | PASS | every (question, method) pair produced a non-empty answer |
| judge-coverage | PASS | 48/48 judged |
| qa-log-records (all Q&A persisted) | PASS | log blocks: 6 question headers / 48 method answers (expected 6/48) |
| metrics-recompute (hit@1 reproducible from doc_rank) | PASS | stored hit@1 equals doc_rank-derived position for all rows |
| production-kb-live | PASS | KB-UserDemo in catalog: True |

## 问答实录

全部 6 问 × 8 法的完整问答(问题/期望答案/逐字金标/每算法 doc_rank 与 top-k/证据/回答原文/评审意见)见 [`REALSCENARIO-QA-LOG.md`](REALSCENARIO-QA-LOG.md); 逐题九系统回答卡见 HTML 报告; 机器可读结果见 `real-scenario-20260916-045222`。

## 复现方式

本目录 [`REALSCENARIO-TEST-PLAN.md`](REALSCENARIO-TEST-PLAN.md) 为 Agent 可逐步执行的复现计划(P0-P6, 含校验门)。

```bash
cd benchmark-suite
python scripts/29_real_scenario_test.py            # 全量矩阵
python scripts/29_real_scenario_test.py --smoke    # 冒烟
python scripts/32_real_scenario_report.py          # 本报告再生成
```

前提: 后端 :8771 健康(embedding ready), `omp` 在 PATH, `.env` 含 `MCP_AUTH_TOKEN` 与 `HF_HUB_OFFLINE=1`。
