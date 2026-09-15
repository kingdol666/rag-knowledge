# 真实场景基准报告 — 用户上传文档 × 论文复现检索算法

- 运行: `2026-09-16 00:15:07` · 问题数: 6 (每文档 3, omp Agent 从文档内容生成)
- 文档: `ARCHITECTURE.md`, `SUBMISSION-MASTER-PLAN.md`
- 生产 KB: `KB-UserDemo`(kb_doc_create 平台用户路径, 指纹 `66b0f9f5ffc63e6f`); 基线 KB: `UserDemo-Chunks800`, `UserDemo-Struct`, `UserDemo-Paras`
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

## 主表(文档级检索命中 + 评审得分)

| 算法 | hit@1 | hit@3 | judge 均分 | 平均时延(s) | LLM 调用 |
|---|---|---|---|---|---|
| `qdcvr` | 4/6 | 6/6 | 3.00 | 32.2 | 0 |
| `dense_rag` | 6/6 | 6/6 | 6.17 | 41.0 | 0 |
| `dense_rag_rerank` | 6/6 | 6/6 | 3.50 | 56.8 | 6 |
| `raptor` | 6/6 | 6/6 | 9.17 | 29.9 | 0 |
| `itrg_refresh` | 6/6 | 6/6 | 5.83 | 19.5 | 18 |
| `itrg_refine` | 6/6 | 6/6 | 7.83 | 2.9 | 18 |
| `search_o1` | 6/6 | 6/6 | 6.67 | 105.9 | 26 |
| `deepread` | 5/6 | 5/6 | 6.50 | 66.4 | 14 |

## 逐题胜出

| qid | 文档 | judge 最佳 | 中间 Agent 排名第一 |
|---|---|---|---|
| U1 | ARCHITECTURE | dense_rag (9.0) | deepread |
| U2 | ARCHITECTURE | dense_rag (9.0) | dense_rag |
| U3 | ARCHITECTURE | dense_rag (10.0) | deepread |
| U4 | SUBMISSION-MASTER-PLAN | qdcvr (10.0) | deepread |
| U5 | SUBMISSION-MASTER-PLAN | raptor (9.0) | search_o1 |
| U6 | SUBMISSION-MASTER-PLAN | dense_rag_rerank (9.0) | deepread |

## 问答实录

全部问题×算法的完整问答见 [`REALSCENARIO-QA-LOG.log`](REALSCENARIO-QA-LOG.log); 机器可读结果见 `real_scenario.json`。

## 复现方式

```bash
cd benchmark-suite
python scripts/29_real_scenario_test.py            # 全量
python scripts/29_real_scenario_test.py --smoke    # 冒烟
```

前提: 后端 :8771 健康(embedding ready), `omp` 在 PATH,
`.env` 含 `MCP_AUTH_TOKEN`(以及 `HF_HUB_OFFLINE=1` 离线嵌入)。
