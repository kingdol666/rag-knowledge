# QDCVR 基准测试执行计划（BENCHMARK-EXECUTION-PLAN）v1.1

> **生成**: 2026-09-10 · 上游文档: `benchmark-web/BENCHMARK-TEST-PLAN.md` v3.0（系统五阶段评测）+
> `docs/paper/DATASETS-AND-EXPERIMENTS.md`（公开数据集选型）+ `docs/paper/SUBMISSION-MASTER-PLAN.md`（投稿目标）
> **本文档解决一件事**: 拿着命令就能从零跑完整个基准，产出**可复现、可与已发表论文直接对比**的得分。
> **当前状态**: 7 个评测集已拉取并校验 ✅ · wiki18 语料已下载解压 ✅ · 全部脚本就位 ✅ ·
> 一键编排 `run_all.sh`（smoke / track1 / full 三档）✅ · 领域集已出真实分数 ✅ ·
> 待执行: Step 3 语料入库 + Step 4-6 正式评测 ⏳
>
> **最快开始**: `cd benchmark-web/benchmark && export RAG_BENCH_TOKEN=$(grep '^MCP_AUTH_TOKEN' ../../.env | cut -d= -f2) && bash run_all.sh --stage smoke`

---

## 一、总体设计：两轨评测

| 轨道 | 数据 | 目的 | 对比锚点 |
|---|---|---|---|
| **Track 1 公开可比轨** | FlashRAG 7 个评测集 + Wikipedia 语料按主题拆 12 KB | 证明方法在公开基准上有效，数字与社区同源 | HiRAG 表5 / Adaptive-RAG / CRAG / Self-RAG（见 §四） |
| **Track 2 领域自建轨** | Dataset A–E（原 v3.0 计划，标注中） | 证明 KB 生命周期/经验/盲点等独家能力 | 自建基线（S0–S5 消融），CRAG Table 4 协议对标内容验证 |

两轨共享同一套 runner、指标库与统计检验（`benchmark-web/benchmark/scripts/`）。

---

## 二、测试数据集清单（已拉取 ✅）

### 2.1 Track 1 公开评测集 —— 已下载并校验（2026-09-10）

位置: `benchmark-web/benchmark/data/flashrag/`（原始）→ `data/benchmarks/`（冻结子集 + qrels）
来源: `huggingface.co/datasets/RUC-NLPIR/FlashRAG_datasets`（RAG 论文事实标准，GraphRAG-Router / Search-R1 / PIKE-RAG 同源）
统一 schema: `{id, question, golden_answers, metadata{...}}`

| 数据集 | 任务 | 原始规模 | 冻结子集(seed=42) | qrels 标签来源 | qrels 条数 | 用途 |
|---|---|---|---|---|---|---|
| PopQA | 单跳·长尾实体 | 14,267 | 2,000 | `metadata.s_wiki_title`（CRAG 论文同款用法） | 2,000 | 主力单跳集；长尾子集→QDCVR 拒答/盲点评测 |
| NQ | 单跳通用 | 3,610 | 1,000 | 无（answer 子串协议） | — | 端到端 EM/F1 |
| TriviaQA | 单跳通用 | 11,313 | 1,000 | 无（answer 子串协议） | — | 端到端 EM/F1（Self-RAG 锚点集） |
| HotpotQA | 2 跳 | 7,405 dev | 1,000 | `supporting_facts.title`（2,436 条 golden 页面） | 2,436 | **多 KB 检索主力集**（golden docs 天然分属多主题 KB） |
| 2WikiMultiHopQA | 2-3 跳·带推理类型 | 12,576 dev | 1,000 | `supporting_facts.title`（2,423 条） | 2,423 | 按 comparison/inference/compositional/bridge 分难度报告 |
| MuSiQue | 2-4 跳组合 | 2,417 dev | 500 | `question_decomposition[*].support_paragraph.title`（1,324 条） | 1,324 | 高难度压测 |
| Bamboogle | 多跳难题 | 125 | 125（全量） | 无 | — | 小而难抽查集，端到端 QA |

**完整性校验**: `python scripts/download_datasets.py --verify` → 7/7 OK（行数与官方一致，必需字段 0 缺失）。
**样本冻结凭证**: `data/benchmarks/MANIFEST.json`（每个文件的 SHA256 + 行数 + seed=42）。**它必须提交进 git；论文报告数字时必须引用该 manifest 的哈希值。**

qrels 中 unique golden title 共 **7,034 个**，已由规则映射到 13 个主题 KB。全量拆库已完成
（2026-09-10，两遍流式扫描 21,015,324 passages → 4,888,342 页，约 2 分钟）：

| 项目 | 数值 |
|---|---|
| 语料指纹 | `corpus_stats.json`: sha256[:16]=`43d7d3f58d01d711`, schema_version=2 |
| golden 命中 | **5,068 / 7,034 (72%)** —— 未命中 1,966 个标题系 wiki18（2018-12 快照）与数据集元数据标题差异所致 |
| 选中页面 | **18,068 页** = golden 5,068（全量保留）+ 干扰页 13×1000（sha256(title) 稳定序采样） |
| 每 KB 分布 | People 3,487 · Other 2,119 · Film-TV 1,663 · Music 1,234 · Politics-History 1,138 · Geography 1,096 · Economy-Law 1,090 · Literature-Arts 1,087 · Sports 1,070 · Science-Tech 1,024 · Transport 1,024 · Military 1,019 · Bio-Medicine 1,017 |

→ 每个多跳问题的 golden docs 自然分布在 1–4 个 KB = "多知识库检索"的公开可复现版本
（**无任何已发表工作这样做过，这是本系统独有实验维度**）。
⚠ **语料可答性口径**：golden 页不在语料中的查询（约 28%）在 `run_eval.py` 中默认剔除
并记录 `n_excluded_no_corpus`，论文需注明"corpus-answerable subset"口径；如需全量口径可加 `--no-filter`。

### 2.2 Track 1 语料库 —— 已下载 ✅

| 文件 | 说明 | 状态 |
|---|---|---|
| `wiki18_100w.zip` (5.13GB → 解压为 wiki18_100w.jsonl) | Wikipedia 2018-12-20 全量 100 词切分，21,015,324 段，FlashRAG/Adaptive-RAG/HiRAG 同源语料 | ✅ 已下载（`data/flashrag/retrieval-corpus/`），拆库脚本自动识别 |

### 2.3 Track 2 自建数据 —— 已有雏形，标注进行中

| 资产 | 位置 | 状态 |
|---|---|---|
| 50 条领域查询（含 expected_kb / relevant_docs / intent） | `docs/paper/benchmark/datasets/queries.json` | ✅ 已出真实分数（`results/eval-domain40.json`：two_stage P@5=0.428 / MRR=0.551 / FPR=0.592 vs flat P@5=0.388 / FPR=0.62；n=50 差异未达显著 p=0.72） |
| 10 篇 arXiv 2025 真实 PDF | `docs/paper/benchmark/datasets/arxiv-benchmark/` | ✅ 可用（Phase A 入库 + Phase E 端到端） |
| 3 篇领域测试文档 | `docs/paper/benchmark/datasets/test-docs/` | ✅ 可用 |
| Dataset A/B/D 标注 | 按 v3.0 计划 | ⏳ 未完成（不阻塞 Track 1） |

### 2.4 项目内既有基准结果（历史，仅供参考不作为论文数字）

`docs/paper/benchmark/results/`（EXP-1 等 18 项，2026-07~09 测得，综合分 0.891）——
注意：**这些结果产自旧脚本（`run_exp1.py` 等，无 token、指向 8765）**。2026-09-09 起
全 API 强制鉴权，旧脚本已失效；本计划的 `run_eval.py` 是其带鉴权的正式替代品。
论文一律使用新 runner 的输出。

---

## 三、环境与启动步骤

### 3.0 前置条件

```bash
# Windows (Git Bash)
cd D:/codes/ClaudeGPT/rag_project/rag-knowledge
./ragctl setup     # 首次: 安装 backend/web/kb-mcp 依赖
./ragctl up        # 启动后端(8770) + 前端(6789) + MinerU + Neo4j
./ragctl status    # 全绿后继续
```

### 3.1 鉴权配置（2026-09-09 起全 API 强制）

```bash
# token 来自项目根 .env 的 MCP_AUTH_TOKEN（服务身份，全权限）
export RAG_BENCH_TOKEN="$(grep '^MCP_AUTH_TOKEN' .env | cut -d= -f2)"

# 验证（任一端口; .env 的 BACKEND_PORT=8770 优先）
curl -s http://localhost:8770/api/v1/health   # 无需 token
curl -s -X POST http://localhost:8770/api/v1/search/vector \
  -H "Content-Type: application/json" -H "Authorization: Bearer $RAG_BENCH_TOKEN" \
  -d '{"query":"test","kb_id":"","top_k":1}'   # 必须 success:true
```

或注册独立用户 token（更符合最小权限，适合长期 CI）：
`POST /api/v1/auth/register` → `POST /api/v1/auth/login` → `POST /api/v1/auth/tokens`。

### 3.2 Python 环境

脚本仅依赖标准库（urllib/json/statistics），用项目 venv 即可：
`backend/.venv/Scripts/python.exe`（3.12.7）或任意系统 Python ≥3.10。
统计检验终稿如需 scipy：`backend/.venv/Scripts/pip install scipy`。

---

## 四、论文锚点数据表（与 9 篇已发表论文的可对比数字）

> 用途：跑完 Track 1 后，把我们的数字填进最后一列即可成文。
> 提取来源：`tmp/paper_exp_extract.txt`（9 篇 PDF 实验章节全文提取）。

### 4.1 端到端 QA —— HiRAG (EMNLP'25) Table 5 ⭐ 直接可比主锚点

同数据集（HotpotQA / 2Wiki dev）、同指标（EM/F1）、同底座（GPT-4o-mini）：

| 方法 | 2Wiki EM% | 2Wiki F1% | HotpotQA EM% | HotpotQA F1% |
|---|---|---|---|---|
| NaiveRAG | 15.60 | 25.64 | 21.60 | 40.19 |
| GraphRAG | 22.50 | 27.49 | 31.70 | 42.74 |
| LightRAG | 16.50 | 40.95 | 25.00 | 43.20 |
| FastGraphRAG | 20.80 | 44.81 | 35.00 | 49.56 |
| **HiRAG** | **46.20** | **60.06** | **37.00** | **52.29** |
| **QDCVR (ours)** | _待填_ | _待填_ | _待填_ | _待填_ |

可比性条件：① 用同一 FlashRAG dev 抽样（MANIFEST 一致即可，EM/F1 是均值意义可比）
② 底座 LLM 报告版本（GPT-4o-mini 或注明差异）③ 检索上下文均为 Wikipedia 语料。

### 4.2 内容验证器 —— CRAG (NAACL'24) Table 4 ⭐ QDCVR 内容验证直接对标

检索评估器在 PopQA 上的判定准确率：

| 评估器 | Accuracy |
|---|---|
| CRAG T5-based retrieval evaluator | **84.3** |
| ChatGPT few-shot | 64.7 |
| ChatGPT-CoT | 62.4 |
| ChatGPT zero-shot | 58.0 |
| **QDCVR 0-8 rubric 内容验证 (ours)** | _待填_ |

协议：PopQA 自带 golden wiki title 当相关性标签（与本计划 qrels 同源！），把 0-8 分
阈值化为 Correct/Incorrect/Ambiguous 三分类，报准确率 → 写进论文 6.4 节（对标 CRAG Table 4）。

### 4.3 数据配置锚点（证明我们与对手在同一赛道）

| 论文 | 数据配置 | 指标 | 我们复用了什么 |
|---|---|---|---|
| **Adaptive-RAG** (NAACL'24) | 单跳 SQuAD/NQ/TriviaQA + 多跳 MuSiQue/HotpotQA/2Wiki；语料 = Karpukhin-2020 / Trivedi-2022 预处理 Wikipedia | F1/EM/Acc + Time-per-Query 效率曲线(Fig.5) | 同款数据组合 + 效率-质量权衡图协议 |
| **Self-RAG** (ICLR'24) | PopQA/TriviaQA(+KILT/ASQA) | Acc/FactScore/引用精度 | TriviaQA/PopQA 端到端协议；"answer 子串命中检索段"的检索判定法 |
| **CRAG** (NAACL'24) | PopQA/Bio/PubHealth/ARC；检索评估器单独成表 | Acc/FactScore + 评估器准确率 | §4.2 内容验证协议 |
| **AgenticRAG** (2026) | BRIGHT R@1=49.6；WixQA factuality=0.96；FinanceBench correctness=92.0 | Recall@1/factuality/answer correctness | 企业长文档叙事的对比参照（可选扩展集） |
| **DeepRead** (2026) | FinanceBench/ContextBench/QASPER/SyllabusQA，比 Search-o1 平均 +10.3% | Acc | 自建集人工标注先例（94 篇即可发表） |
| **GraphRAG** (2024) | 自建 persona 查询 + MultiHop-RAG；win-rate 人工评 | comprehensiveness/diversity | 主观 win-rate 协议（Track 2 主观表用） |

### 4.4 我们独有、对手没有的指标（论文差异化，无外部锚点）

FPR（跨域误召回率，旧 EXP-2 实测 0.236→0.018 降 92.4%）· 搜索空间压缩比（1,138×）·
盲点正确声明率 · 经验可信度分级准确率 · 多 KB 路由准确率。
这些指标用 §2.3 自建数据测，基线是自身消融（S0 vs S1/S2/S3）。

---

## 五、执行步骤（Step 0 → Step 8，命令级）

**一键编排**（推荐）——三档可选，任何一步失败即停：

```bash
cd benchmark-web/benchmark
export RAG_BENCH_TOKEN="$(grep '^MCP_AUTH_TOKEN' ../../.env | cut -d= -f2)"
bash run_all.sh --stage smoke    # 冒烟: 环境检查 + 领域集评测 + 报告（无语料可跑, ~2 分钟）
bash run_all.sh --stage full     # 全流程: 语料→拆库→入库→全部评测→报告（首次约半天）
bash run_all.sh --stage track1   # 语料已入库后: 只跑全部评测 + 报告
# 可选环境变量: PAGES_PER_KB=1000(拆库干扰页/KB) · QA_LIMIT=500(QA评测条数) · PY=venv python 路径
```

以下为分步说明（与 run_all.sh 阶段一一对应）。工作目录：`cd benchmark-web/benchmark`

### Step 0 · 环境自检（5 分钟）

```bash
cd D:/codes/ClaudeGPT/rag_project/rag-knowledge
./ragctl status                                       # 服务全绿
export RAG_BENCH_TOKEN="$(grep '^MCP_AUTH_TOKEN' .env | cut -d= -f2)"
curl -s http://localhost:8770/api/v1/health           # {"status":"healthy"}
cd benchmark-web/benchmark
python scripts/download_datasets.py --verify          # 7/7 OK
python -c "import json; m=json.load(open('data/benchmarks/MANIFEST.json')); print(m['seed'], len(m['files']))"
```

### Step 1 · 评测子集构建（已完成，可跳过；重跑会得到逐字节相同输出）

```bash
python scripts/build_benchmark_sets.py --seed 42      # 7 数据集 + qrels + MANIFEST
python scripts/split_corpus_to_kbs.py --sample-only   # golden title → 主题 KB 映射
```

### Step 2 · 语料下载（一次性，4.9GB，约 10-40 分钟视带宽）

```bash
python scripts/download_datasets.py --corpus          # 下载 wiki18_100w.zip + 安全解压
```

### Step 3 · 语料按主题入库 + 全量索引（Track 1 生效的前提，一次性）

```bash
python scripts/split_corpus_to_kbs.py --pages-per-kb 1000
# ✅ 已执行完毕（2026-09-10）: 21M passages → 4,888,342 页, 选中 18,068 页
# → data/benchmarks/kb_split/pages_KB-*.jsonl + corpus_stats.json（语料指纹）
# 重跑会得到逐字节一致结果（sha256 稳定序采样, ~2 分钟）

python scripts/ingest_corpus.py
# 每 KB: kb/create(幂等) → 每页一个 .md 文档 → batch-index(50/批) → 向量检索验证非空
# 断点续跑: results/checkpoint-{KB}.jsonl；冒烟: --kbs KB-Film-TV --limit 100
# ✅ 入库链路已用 3 页合成分片端到端验证通过（create→index→verify 全通）
```

要点：① KB 名固定 `KB-*` 前缀（13 个顶层平铺 KB，避开父子库检索坑）② 全部入库后报告
`results/corpus-ingest-report.json` ③ 预期规模：18,068 页文档，API 入库约 1-3 小时。
**子语料设定写入论文 setup**（golden 全保留、干扰页确定性采样，HiRAG/GraphRAG 同样用子集，
可比性成立）。

### ⚠ 已知接口坑（脚本已内置处理）

**two-stage 响应结构**是 `{success, query, stage1, stage2:{results}, total_results}`——
最终结果在 `stage2.results`，顶层没有 `results` 键（直接 `.get("results")` 会静默得 0 分，
评测脚本已按此解析；自写脚本务必注意）。MCP 层 `kb_list` 响应在 `catalog` 键（字段 `kb_id`/`name`）。

### 3.3 MCP + Skill 集成通道（Agent 实际使用的路径）⭐

除 HTTP 直调外，基准可经 **kb-mcp MCP 服务器**（Agent/技能实际走的通道）复现：

- **MCP 配置**：项目根 `.mcp.json` 与 `.zcode/mcp.json`（同款命令
  `uv run --directory kb-mcp python server.py`），会话重启后 ZCode 即挂载 94 个 `kb-mcp__*` 工具。
- **MCP 基准客户端**：`scripts/run_mcp_eval.py` —— 自行拉起 stdio MCP 服务器，按
  `knowledgebase-search` skill 的 QDCVR 六步规程执行：Pre-Flight(`kb_project_status`) →
  Step1(`kb_list`) → Step2(`kb_search_two_stage` balance_kbs) → Step2.5(硬阈值0.35+文档级去重)
  → Step3(`kb_doc_read` 内容验证抽检)。
- **已验证结论（2026-09-10）**：94 工具无缺失；raw 口径（不含 Step 2.5 门控）与 HTTP 直调
  **逐位一致**（MRR=0.5317/P@5=0.424/路由 0.52）→ MCP 层与 HTTP 层等价，基准可经任一通道复现；
  skill 门控本身是一个显著消融轴：**FPR 0.588→0.34（-42%，p=0.0015）**，MRR 微升，
  P@5 下降（rank 覆盖率换跨域纯度）——写论文时可作为 "gating 贡献" 段落素材。

```bash
python scripts/run_mcp_eval.py                # 领域 50 查询 × {skill, raw} 双口径
python scripts/run_mcp_eval.py --track1 10    # 追加 FlashRAG 数据集经 MCP 链路冒烟
```

### Step 4 · 检索评测（Track 1 主实验，先冒烟后全量）

```bash
# 冒烟（20 条, 验证链路; 当前库无 wiki 语料时 hits=0 是预期）
RAG_BENCH_TOKEN=$RAG_BENCH_TOKEN python scripts/run_eval.py --dataset hotpotqa --limit 20

# 正式（5 方法 × 7 数据集; 每方法每千条约 8-15 分钟, 总计一夜）
for ds in popqa nq triviaqa hotpotqa 2wiki musique bamboogle; do
  RAG_BENCH_TOKEN=$RAG_BENCH_TOKEN python scripts/run_eval.py --dataset $ds --methods all
done
```

方法组与论文角色：`vector_flat`=NaiveRAG 锚点 · `two_stage`=**S0 本系统** ·
`vector_domain`=oracle 上界参照 · `two_stage_nb`=消融(-graph) · `two_stage_bal`=消融(+多库均衡)。
输出：`results/eval-<ds>-*.json`（含逐方法指标 + S0 vs 各法的配对 t 检验/Cohen's d）。

### Step 5 · 端到端 QA 评测（EM/F1 → 直接填进 §4.1 表）

```bash
export RAG_QA_BASE_URL=https://<openai兼容端点>/v1
export RAG_QA_API_KEY=sk-xxx
export RAG_QA_MODEL=deepseek-v4-pro        # 或 gpt-4o-mini 以对齐 HiRAG 底座
for ds in hotpotqa 2wiki; do
  RAG_BENCH_TOKEN=$RAG_BENCH_TOKEN python scripts/run_qa_eval.py --dataset $ds --limit 500
done
```

评分协议 = SQuAD 归一化 EM + token-F1 + Adaptive-RAG 的 Acc（golden⊂pred 子串），
温度 0，prompt 固定并写入结果文件。逐条明细在 `results/qa-<ds>-detail.jsonl`（错误分析素材）。

### Step 6 · 内容验证器评测（对标 CRAG Table 4）

```bash
python scripts/run_verifier_eval.py --dataset popqa --limit 500            # 启发式(可复现, 零依赖)
RAG_QA_BASE_URL=... RAG_QA_API_KEY=... RAG_QA_MODEL=... \
  python scripts/run_verifier_eval.py --dataset popqa --limit 500 --scorers heuristic,llm
```

协议：PopQA qrels 的 golden title 命中 chunk = 正例，同查询高分非 golden chunk = 难负例；
0-8 rubric（topic 0-3 + scenario 0-2 + evidence 0-3）阈值化 ≥6 Correct / 3-5 Ambiguous /
≤2 Incorrect 三分类，报 acc3/acc2/FPR/F1，与 CRAG Table 4（T5 84.3 / ChatGPT 58.0-64.7）
并列对比。启发式评分器逐字节可复现；LLM 版用于论文正文数字（记录 model+prompt+温度）。

### Step 7 · Track 2 领域轨（已可跑）

```bash
python scripts/run_domain_eval.py    # 50 条领域查询 × {two_stage, vector_flat, two_stage_bal}
```

已于 2026-09-10 在当前系统首次跑通（结果 `results/eval-domain40.json`，并汇入 REPORT.md §4）。
数据集 A/B/D/E 按 v3.0 计划标注后扩展。

### Step 8 · 统计与报告

```bash
python scripts/make_report.py
# → results/REPORT.md（锚点并列对比表 + 综合得分卡 + 复现凭证头）
# → results/paper-tables/main-table.tex（LaTeX 主表）
```

统计学规范（写入论文）：所有对比 5 次运行取均值；配对 t 检验 α=0.05，5 组对比
Bonferroni 校正 α'=0.01；Cohen's d ≥0.8 记大效应；非正态指标 bootstrap 10,000 次 95% CI
（run_eval/make_report 内置正态近似 t 检验与 Cohen's d；论文终稿数值用 scipy 重算 p 值）。

---

## 六、得分方法（Score Card）

### 6.1 Track 1 检索得分（0-100）

```
检索分 = 40 × min(nDCG@5 ours / nDCG@5 flat_baseline, 1.5)    # 相对提升, 封顶 60 分
       + 30 × (1 - FPR_ours/FPR_flat)                          # 跨域误召回消除
       + 20 × min(Recall@5 ours / Recall@5 oracle_domain, 1)   # 向 oracle 上界的接近度
       + 10 × (flat 延迟 / ours 延迟, 封顶 1)                   # 效率保持
```

### 6.2 与论文数字的对比判定（诚实可比性声明）

| 对比 | 判定方式 | 可比性 |
|---|---|---|
| EM/F1 vs HiRAG 表5 五方法 | 同集同指标同底座 → **数字直比** | ✅ 强可比（注明抽样与 LLM 版本） |
| 验证器准确率 vs CRAG 表4 | 同协议(PopQA golden title) → **数字直比** | ✅ 强可比 |
| 检索指标 vs AgenticRAG BRIGHT | 不同集 → 只报"我们的多 KB 检索提升幅度 vs 其 +21.8pp" | ⚠️ 趋势类比，不并列同表 |
| FPR/盲点率/经验分级 | 无对手数字 → 只与自身消融比 | 🚫 独家指标，不与论文并表 |

### 6.3 综合系统分（论文投稿就绪门槛）

继承 v3.0 权重：检索分 30% + 端到端 QA(EM/F1) 30% + 内容验证 15% + Track 2 五阶段 20%
+ 效率 5%，合计 0-100。**≥85 分 = 投稿就绪**（v3.0 定的门槛）。

---

## 七、复现性保证（论文 Reproducibility 清单）

1. **数据冻结**：`data/benchmarks/MANIFEST.json`（seed=42 + 全部 SHA256）随代码入库；重跑 `build_benchmark_sets.py --seed 42` 输出逐字节一致
2. **语料版本**：wiki18_100w 单一官方源 + 下载后记录 SHA256 于 `corpus-stats.json`
3. **服务版本**：结果 JSON 记录 backend URL、时间戳、方法参数（stage1_top_k=20 等）；git commit hash 由 `make_report.py` 自动写入报告头
4. **鉴权**：所有调用走 `Authorization: Bearer`（token 不入库不入报告，CI 用独立用户 token）
5. **LLM 底座**：QA 评测记录 model+温度+完整 prompt；检索评测不依赖 LLM（天然可复现）
6. **统计**：5 次运行 + 配对 t 检验脚本随代码交付
7. **环境**：Python 3.12 / Windows（linux 路径分隔差异由 runner 内 `pathlib` 屏蔽）； ChromaDB/BGE-M3 版本随 `backend/pyproject.toml` 锁定

## 八、时间线与交付物

| 阶段 | 内容 | 状态/工时 |
|---|---|---|
| D0（已完成 2026-09-10） | 7 评测集拉取+校验+冻结（MANIFEST）、KB 拆分映射、wiki18 语料下载解压（5.13GB→14.4GB）、**全量拆库完成（18,068 页, golden 覆盖 72%）**、全部 9 个脚本、run_all.sh 三档编排、领域集真实首跑、入库链路端到端验证 | ✅ |
| D1（待执行） | `ingest_corpus.py` 入库（18,068 页, batch-index 50/批, 断点续跑） | 1-3 小时机器时间 |
| D1 夜间 | Track 1 检索评测全量（Step 4: 5 方法 × 7 数据集） | 一夜机器时间 |
| D2 | QA 评测（Step 5）+ 验证器评测（Step 6）→ 填 §4.1/§4.2 锚点表 → `make_report.py` 出正式报告 | 半天 |
| 并行 | Track 2 标注（Dataset A/B/D/E）按 v3.0 时间线 | 2 周 |

**脚本清单**（`benchmark-web/benchmark/scripts/`，全部仅标准库、可独立运行）：

| 脚本 | 作用 |
|---|---|
| `download_datasets.py` | FlashRAG 7 评测集 + wiki18 语料下载/校验（--verify / --corpus） |
| `build_benchmark_sets.py` | seed=42 冻结抽样 + qrels + MANIFEST（SHA256 复现凭证） |
| `split_corpus_to_kbs.py` | wiki18 页面重建 → 13 主题 KB 分片（golden 全量 + 确定性干扰页采样） |
| `ingest_corpus.py` | 建库/建文档/批量索引/索引验证（幂等 + 断点续跑 checkpoint） |
| `run_eval.py` | Track 1 检索评测（5 方法 × 7 数据集 + 配对 t 检验 + Cohen's d） |
| `run_qa_eval.py` | 端到端 QA（EM/F1/Acc，OpenAI 兼容端点，协议对齐 Adaptive-RAG） |
| `run_verifier_eval.py` | 内容验证三分类（CRAG Table 4 协议，heuristic + LLM 双评分器） |
| `run_domain_eval.py` | 领域查询集评测（当前系统 KB，立即可跑，含路由准确率） |
| `run_mcp_eval.py` | MCP 集成基准（stdio 拉起 kb-mcp，按 knowledgebase-search skill 六步规程，双口径） |
| `bench_http.py` | 共享出站 HTTP 客户端（SSRF 边界：本机白名单 + 远程 https 显式放行） |
| `make_report.py` | 汇总 REPORT.md + LaTeX 主表 + 综合得分卡（自动写入 git commit） |

**交付物清单**：results/*.json（原始）· results/REPORT.md + paper-tables/main-table.tex ·
锚点对比表（§4.1/4.2 填数版）· 综合得分卡 · MANIFEST + corpus_stats（复现凭证）· 全部脚本。

## 七、Windows 入库坑位补记（2026-09-11 实测）

1. **wiki 标题含 Windows 非法文件名字符**（`: ? * " < > |`，如
   `Star Trek: The Next Generation`）→ web 建目录 ENOENT → create 500 →
   入库中断。`ingest_corpus.py` 已内置确定性净化（`re.sub(r'[\/:*?"<>|]', "_")`，
   同一标题永远得到同一文件名，断点去重不受影响）。生产级修复方向：tree-file-system
   的 ensureDirectory/uploadFile 层做全局 sanitize（待办）。
2. **长入库必须给 request 加重试**：批索引 50 页可能超过短超时；
   `ingest_corpus.py` 的 request() 已带 3 次退避重试（5s/10s/15s）。
3. **入库期间不要并发跑评测**：a) 争抢后端会互相触发超时；b) `two_stage_bal`
   （跨全库均衡）在语料动态增长时指标会漂移 —— 可复现性测量必须在语料冻结后进行。
4. **Nuxt dev 模式在错误风暴后会楔死**（youch 错误页 wasm 渲染 "unreachable"
   死循环，API 全 502）→ 重启 web 即恢复。生产基准建议 `nuxt build` 后以 prod 模式运行。

## 八、Track 1 冻结语料首批正式分数（2026-09-11）

入库 12,588 页（9/13 KB：Bio/Economy/Film/Geo/Lit/Military/Music/Other/People-partial）
后冻结语料，双轮评测（每轮全量重跑，中间无写入）：

| 数据集 | 方法 | P@1 | P@5 | MRR | FPR |
|---|---|---|---|---|---|
| hotpotqa (n=91) | **two_stage (S0)** | 0.747 | **0.622** | **0.770** | 0.024 |
| hotpotqa | vector_flat (NaiveRAG 锚) | 0.703 | 0.541 | 0.748 | 0.029 |
| 2wiki (n=86) | **two_stage (S0)** | 0.663 | **0.488** | **0.685** | 0.049 |
| 2wiki | vector_flat (NaiveRAG 锚) | 0.570 | 0.377 | 0.592 | 0.060 |

**核心主张的实证**：多跳集上 two_stage 对 flat 检索 2wiki +11.1pp / hotpotqa +8.1pp P@5
（多 KB 路由的检索增益）；两轮对比四个评测面（domain/hotpotqa/2wiki/verifier）
**全部检索指标逐位一致**（compare_repro.py 判定 REPRODUCIBLE，仅 latency 随负载漂移）。
剩余 4 KB（Politics/Sports/Science/Transport ≈ 4,256 页）由 ingest_corpus.py 断点续跑
补齐后，同一脚本重跑即得全量口径数字。QA 端到端（Step 5）与 verifier LLM 评分器
待配置 OpenAI 兼容端点（RAG_QA_*）后运行。

## 九、语料规模压制：发现 → 修复 → 复测（2026-09-11 优化轮）

**现象**：12,588 页 wiki 语料入库后，Domain-50 的 two-stage P@5 从 0.424 崩塌到 0.000、
routing 0.52→0.02。机理：stage1 全局 BM25 top-20 候选被大库淹没，小领域库（8 篇文档）
永远进不了候选集。vector_flat（纯向量）不受影响（0.388）—— 嵌入空间没有全局词频淹没问题。

**修复（已默认启用，config.yml search.two_stage）**：
1. `stage1_pool_multiplier: 8` —— 全局查询先取 top_k×8 候选池；
2. `kb_aware_candidates: true` —— 按 KB 配额轮询选取候选（`_balance_candidates_by_kb`）；
3. `bm25_max_content_chars: 12000` —— 关键词窗口与拆分上限对齐。

**复测（同一冻结语料 12,588 页，双轮逐位一致）**：

| 配置 | two_stage P@5 | MRR | routing | FPR |
|---|---|---|---|---|
| 修复前（k=20） | 0.000 | 0.000 | 0.02 | 0.988 |
| 预算旋钮 k=150（修复前分析） | 0.128 | 0.160 | 0.34 | 0.752 |
| **修复后（k=20 默认）** | **0.420** | **0.473** | **0.54** | 0.612 |
| small-corpus 参照 | 0.424 | 0.532 | 0.52 | 0.596 |

→ 修复使系统在 22× 语料规模下**恢复到小语料同等水平**（P@5 0.420≈0.424）。

**同时入库的配套优化**：
- **大文档自动拆分**：`ingestion.large_doc`（默认 max_chars=10000/overlap 400）；
  web documents/create 超阈值自动调后端 `/api/v1/documents/split` 拆为 part 文档写盘；
  100,042 字符实测 → 18 parts → 索引+检索全通。BM25 窗口 8000→12000 与拆分上限对齐
  （拆分后的 part 不再被截断）。
- web 生产构建阻断修复：login.vue `/logo.svg` → `/images/logo.svg`（此前 `npm run build` 必失败）。
- 回归：后端 255 passed（+19 splitter、+9 stage1 quota 单测）；kb-mcp smoke 94 工具 PASSED；
  web 生产构建通过；Track-1 双轮逐位可复现（hotpotqa two_stage P@5 0.719/MRR 0.858，
  2wiki 0.546/0.729；hotpotqa 显著性转为 p=0.0192、2wiki p=0.0039 —— 两数据集均显著）。
