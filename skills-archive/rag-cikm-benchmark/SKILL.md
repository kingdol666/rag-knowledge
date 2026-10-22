---
name: rag-cikm-benchmark
description: rag-knowledge 系统的 CIKM 论文级基准复现 pipeline。三模块评分（A 知识入库 / B 内容检索 Skill→MCP 真链路 / C 冥想经验自动总结）+ 跨语言（en/zh/ja）+ 传统向量 baseline 对比。从零跑通可复现相同数值（确定性通道逐位一致，Agent 通道 mean±std）。触发词：rag benchmark、跑基准、复现论文实验。
---

# RAG CIKM Benchmark Pipeline（可复现实验）

## 0. 前置（一次性）

```bash
cd <repo>                                   # rag-knowledge 仓库根
test -f .env && grep MCP_AUTH_TOKEN .env    # 鉴权 token 必须存在
ragctl start backend --port-backend 8771    # 后端(已起则跳过)
ragctl start web                            # 前端(已起则跳过)
```

环境变量（后续所有命令共享）：

```bash
export RAG_BENCH_TOKEN=$(grep MCP_AUTH_TOKEN .env | cut -d= -f2)
export RAG_BENCH_URL=http://localhost:8771
export RAG_BENCH_WEB_URL=http://localhost:6790
cd benchmark-web/benchmark
```

依赖：Python 3.11+（仅需标准库）；kb-mcp 走 `uv run`；嵌入模型 BAAI/bge-m3 本地 GPU（首次自动下载）。

## 1. 语料（冻结数据版本）

- 英文主语料：`data/benchmarks/kb_split/pages_KB-*.jsonl`（wiki18 冻结子集 18,068 页，
  指纹 `data/benchmarks/kb_split/corpus_stats.json`：sha256_16=43d7d3f58d01d711，seed=42）。
- 跨语言语料（MIRACL v1.0 dev + Wikipedia API 快照）：
  ```bash
  python scripts/fetch_crosslang_corpus.py --n-queries 40 --n-distractors 250
  # 产出: pages_KB-CrossLang-{ZH,JA}.jsonl + miracl-{zh,ja}-dev.jsonl + crosslang-manifest-*.json
  # 断点续拉: 重跑即只补缺页(pages-cache-{lang}.json)
  ```
- EN 对照库快照：`python scripts/benchmark_ingestion.py --build-en`。

## 2. 模块 A — 知识入库

```bash
python scripts/benchmark_ingestion.py --ingest --langs en,zh,ja
python scripts/benchmark_ingestion.py --measure --langs en,zh,ja --round 1
# 再跑一遍 --measure --round 2 → 双轮应逐位一致
```

指标：ingest_success_rate / membership_accuracy（指定库归属）/ storage_completeness_mean
（分块前存储完整率）/ self_retrieval_hit1（索引完整性）。

## 3. 模块 B — 内容检索（主线，全部经 kb-mcp MCP 真链路）

```bash
# B1 确定性 QDCVR 管线(逐级搜索+内容裁决, 逐位可复现) + vector baseline 同层对比
python scripts/benchmark_content_mcp.py --lang en --round 1   # --round 2 复现
python scripts/benchmark_content_mcp.py --lang zh --round 1
python scripts/benchmark_content_mcp.py --lang ja --round 1

# B2 Agent 真链路(harness omp + QDCVR Skill 提示 + MCP, LLM 非确定性 → mean±std)
python scripts/benchmark_content_agent.py --lang zh --n-queries 3 --runs 2
```

指标：staged Recall@k / nDCG@5 / MRR / staged_hit_dist（逐级命中率：stage1 候选命中、
stage2 排序命中、stage3 内容验证提升命中）/ verification_boost_delta / tool_calls_per_query。
baseline = `kb_search_vector`（Chroma + BAAI/bge-m3, top_k=10，同 MCP 层，参数内嵌结果 JSON）。
两阶段检索单独记录 `latency_total_s vs latency_search_s`（加速项，不进主结论）。

## 4. 模块 C — 冥想（经验自动总结）

```bash
python scripts/benchmark_meditation.py --kbs KB-CrossLang-EN,KB-CrossLang-ZH \
  --harness omp --round 1   # --round 2 复现
```

指标：run_success_rate / kb_coverage / structural_mean / grounded_ratio（经验正文检索接地）
/ ablation_exp_hit3（经验层 global-search 命中，QDCVR 消融）。

## 5. 报告

```bash
python scripts/make_benchmark_html.py   # → results/benchmark-report.html (Chart.js 单文件)
```

## 6. 复现容忍度

- 确定性通道（模块 A 全部、B1 管线指标）：**逐位一致**（延迟字段除外）。
- 共享库: scripts/mcp_client.py(MCP stdio 客户端) 与 scripts/bench_http.py(SSRF 边界+fresh-opener 重试)。
- Agent/LLM 通道（B2、C 的 harness 运行）：**同模型版本下指标偏差 ≤±0.1**（报 mean±std，
  transcript 存 `results/benchmark/agent-transcripts/` 供审计）。
- 语料指纹（sha256_16）与 MIRACL 版本固化在各 MANIFEST；跨语言重拉页面可能因
  Wikipedia 内容演进而有少量正文差异 → 以仓库内 manifest 记录的快照为准。

## 7. 产出物清单

```
results/benchmark/benchmark_ingestion_{en,zh,ja}_r{1,2}.json
results/benchmark/benchmark_content_mcp_{en,zh,ja}_r{1,2}.json
results/benchmark/benchmark_content_agent_{en,zh}_r1.json
results/benchmark/benchmark_meditation_en_r{1,2}.json
results/benchmark/benchmark_content_{lang}_{timestamp}.json   # 规范别名
results/benchmark-report.html
```
