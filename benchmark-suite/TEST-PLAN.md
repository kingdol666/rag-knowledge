# 测评计划（TEST-PLAN）— rag-knowledge 三模块基准

> 本套件自包含：测试文档资料（`data/`）+ 脚本（`scripts/`）+ 本计划。
> 任何人（或任何 Agent）按下面步骤执行，即可从零复现全部 benchmark 数值。
> 设计目标：**快**（全程约 50-60 分钟，其中约 40 分钟为自动化运行）、**完整**（覆盖
> 文档解析入库 / 基于内容检索 / 经验总结三大功能）、**可复现**（确定性管线双轮逐位一致）。

## 0. 前置条件（一次性，约 5 分钟）

```bash
# 仓库根目录
cd <repo-root>
# 后端 :8771 与前端 :6789 已启动（可用 ragctl start / start.bat；以实际监听端口为准）
curl -s http://localhost:8771/health          # 期望 {"status":"healthy"}
# 鉴权 token 在 .env 的 MCP_AUTH_TOKEN；环境变量可省略（脚本自动读取）
# 依赖：Python 3.11+（标准库）、uv（拉起 kb-mcp）、omp（仅模块 C 的冥想与评价 Agent）
# matplotlib（仅 data/make_pdf.py 生成 PDF 需要；仓库 data/ 内已附带生成好的 PDF）
```

环境变量（脚本也可自动从 .env 读取）：

```bash
export RAG_BENCH_TOKEN=$(grep MCP_AUTH_TOKEN .env | cut -d= -f2)
export RAG_BENCH_URL=http://localhost:8771
export RAG_BENCH_WEB_URL=http://localhost:6789  # 以实际 web 端口为准（netstat 校验）
```

## 1. Step 0 · 清空知识库（约 2 分钟）

```bash
python scripts/00_reset_env.py
```

删除系统中**全部**知识库（级联清理向量与图谱数据），输出剩余 KB 数量应为 0。
这是复现的起点：保证从同一空白状态开始。

## 2. Step 1 · 模块 A：文档解析与入库（约 6 分钟；冷启动首轮约 20+ 分钟）

> 若后端刚 `restart`（内存索引为空），首轮入库会触发模型/BM25 全量预热，Step 1 双轮
> 实测约 25 分钟；此后各步回到常规耗时。全程热启动约 50–60 分钟，冷启动约 70–80 分钟。

```bash
python data/make_pdf.py                # 生成演示 PDF（已附带，可跳过）
python scripts/01_ingestion.py 1       # 第一轮
python scripts/01_ingestion.py 2       # 第二轮（复现校验）
```

做了什么：创建 KB-Demo-EN/ZH/JA 三个库 → 15 篇 md（en 5 / zh 4 / ja 4，外加
wind-energy.md 供检索）走生产入库 API → 1 个 PDF 经 **MCP parse_doc（MinerU 真解析）**
转 markdown 后回写 KB → force 重索引。
产出：`results/module_a_ingestion_r{1,2}.json`（解析成功率 / 入库成功率 / 指定库归属
正确率 / 存储完整率 / 自检索 Hit@1，内嵌环境指纹）。
**预期**：所有指标 ≥ 0.95；双轮数值逐位一致。

### 2b. 标准语料库扩展入库（BEIR SciFact + SQuAD v1.1，约 12 分钟）

```bash
python scripts/20_standard_download.py     # 下载标准测试集并确定性子集化(约 1-2 分钟)
python scripts/21_std2_ingest.py 1         # 入库 KB-SciFact / KB-SQuAD + 模块A指标
```

**标准测试集来源（均为 CIKM/ACL/EMNLP 社区标准基准，被大量同行论文使用，引用见 §8）**：
- **BEIR SciFact**（检索基准标准集，带 qrels 相关性判定）：30 条标准查询、
  28 篇金标文献 + 120 篇干扰文献（sha256 稳定序采样）→ 共 148 个 md
- **SQuAD v1.1 dev**（抽取式问答标准集）：8 篇文章 + 16 条标准问题（含标准答案）

做了什么：下载官方原版数据 → 确定性子集化（每篇文献写为一个 md，文件名内嵌语料库
文档 id）→ 走与演示语料完全相同的**生产入库 API + force 重索引** → 输出模块 A 同款
指标（归属正确率 / 存储完整率 / 自检索）。
产出：`results/module_a_std2_r{1,2}.json`；语料指纹 `data/standard2/manifest-*.json`。
**预期**：归属正确率与存储完整率 ≥ 0.99（标准文献为叙述型文本，不触发拆分）。
复现校验：`python scripts/21_std2_ingest.py 2`（幂等重跑，双轮指标一致）。

### 2c. 标准语料库检索评测 — 四方法对比 + 答案级判定（约 8 分钟）

```bash
python scripts/22_std2_retrieval.py 1
python scripts/22_std2_retrieval.py 2       # 复现校验(逐位一致)
```

同一查询、同一 MCP 工具层，每查询抽出 **4 种检索方法** 的排序结果：

| 方法 | 来源 | 说明 |
|------|------|------|
| `bm25` | `kb_search_two_stage` stage1 候选 | 稀疏 BM25（Robertson & Zaragoza 2009；BEIR 基线同款） |
| `twostage` | stage2 精排 + Step2.5 | 混合检索，无内容验证 |
| `dense` | `kb_search_vector` top-10 | 稠密向量 BAAI/bge-m3（Chen et al. 2024） |
| `qdcvr` | 全规程 | 两阶段 → Step2.5 → `kb_doc_read`×3 内容验证重排 |

- **BEIR SciFact**（30 标准查询，官方 qrels 多相关文档金标）：
  **命中率 Hit@k · 召回率 Recall@k · nDCG@10 · Precision@5 · MRR**。
  实测：QDCVR Hit@1 0.77（四方法最高）· nDCG@10 0.81；dense Hit@3 0.90 领先
  （Step2.5 硬阈值会丢弃低分金标，属可调精度/召回权衡，报告中讨论）
- **SQuAD**（16 标准问题，文章级金标 + 标准答案）：qdcvr/twostage/dense
  Hit@3 = nDCG@10 = 1.0
- **答案级判定（检索内容能否真实回答问题，对四方法对称执行）**：
  - SQuAD `answer@k` = 金标答案串出现在 **top-k 检索文档正文**（`kb_doc_read` 全文，共享读取缓存）。
    实测：qdcvr answer@1 0.94 / answer@3 1.0，bm25 answer@1 仅 0.875
  - SciFact `claim_evidence` = top-1 文档正文对 claim 内容词（去停用词）覆盖率；
    `support@1` = 覆盖率 ≥ 0.5 的查询占比。实测：qdcvr 0.516/0.60，均高于 twostage/dense
- 产出：`results/module_b_std2_r{1,2}.json`；烟测 `BENCH_LIMIT=3 python scripts/22_std2_retrieval.py smoke`

## 3. Step 2 · 模块 B：基于内容的检索 vs 向量 baseline（约 10 分钟）

```bash
python scripts/02_retrieval.py 1
python scripts/02_retrieval.py 2       # 复现校验
```

做了什么：20 个查询（en 8 / zh 5 / ja 4 / 跨库 3，含金标页与答案，见
`data/queries.jsonl`），全部经 **kb-mcp MCP stdio 真链路**（与 Agent 同款工具层）：

- **内容检索**（QDCVR 规程确定性展开）：`kb_list` → `kb_search_two_stage`
  （两阶段召回，全局+balance）→ Step2.5 硬阈值 0.35+去重 → `kb_doc_read`×3
  **内容验证**并按验证得分重排（content-overrides-vector）
- **向量 baseline**：`kb_search_vector` top-10（Chroma + BAAI/bge-m3）

指标：**命中率 Hit@1/3/5**（金标进 top-k）· **召回率 Recall@3/5**（金标覆盖率）·
**准确率 Precision@5**（top-5 相关占比）· MRR · 逐级命中分布（stage1/2/3）· 时延。
产出：`results/module_b_retrieval_r{1,2}.json`。
**预期**：内容检索整体 Hit@3 / Recall@5 / MRR 高于向量 baseline；双轮逐位一致
（延迟除外）。首轮运行会触发 BM25 全量重建（脚本内置预热等待，属正常现象）。

## 4. Step 3 · 模块 C：冥想经验自动总结（约 15 分钟）

```bash
python scripts/03_experience.py 1
python scripts/03_experience.py 2
```

做了什么：对 KB-Demo-EN / KB-Demo-ZH 触发真实冥想（`POST /meditation/run`，
harness=omp Agent 从库内文档综合信号并撰写经验）→ **草稿审批**（系统设计的
人工确认环节，基准中自动化：`POST /experience/{kb}/drafts/{id}/approve`）→ 读取
经验区 → **创建子 Agent**（omp 一次性运行）按 0-10 rubric 逐条评价：有据性 4 分
（内容是否源自库内事实、无幻觉）+ 结构 3 分 + 可复用性 3 分。
产出：`results/module_c_experience_r{1,2}.json`（运行成功率 / 草稿数 / 经验产出 /
子 Agent 评分均值 / 有据比例；评价原文存 `results/judge-*.txt` 可审计）。
**预期（实测口径，见 REPRODUCTION-VERIFICATION.md）**：两库均运行成功（`run_success`）；
系统质量门对纯百科语料**正确拒绝**（这是机制按设计工作的证据，非缺陷）。**经验条目数
（0–10）取决于语料性质与模型判定，不作为复现判据**——实测中同一 demo 语料一次产出
8–10 条、另一次判定“无 problem→solution→verification 结构”而返回 0 条，两次均属正确
行为。判定稳定性看 `run_success`/草稿审批链路；若产出经验，子 Agent 严格评分均值
3.5–4.5/10、有据比例 0.2–0.75（LLM 评审方差 ±1.5）。

## 5. 标准语料赛道说明（XQuAD 扩展）

本计划的标准基准覆盖为 **BEIR SciFact（检索）+ SQuAD v1.1（QA）**（见 §2b/§2c）。
如需额外交叉语言 QA 赛道（XQuAD，ACL 2020，en/zh 对齐问答），其下载与评测脚本位于
`benchmark-web/benchmark/`（旧套件，git 历史可查）；当前套件的多语言覆盖由自建
zh/ja 语料（§2）与 XQuAD-zh 扩展共同支撑，非本计划必需步骤。

## 6. Step 4 · 生成报告

```bash
python scripts/04_report.py
# → results/benchmark-report.html（Chart.js 单文件，双击即看）
```

报告含：模块 A/B/C 各自得分图、**内容检索 vs 向量 baseline 对比图**、逐级命中率图、
时延对比（两阶段=工程加速项）、标准语料赛道图、每张图下方的解释文字（可直接改写进论文 experiments）。

## 6b. Step 5 · 复现核对（可选，约 1 分钟）

```bash
python scripts/compare_runs.py <基线结果目录> results
# 例: python scripts/compare_runs.py results/archive-20260913-214859 results
```

逐项对比两次运行的模块 JSON，忽略计时/时间戳字段；输出 `PASS`（逐位一致）/
`PASS*`（汇总层一致，仅逐查询明细差异）/`FAIL`（汇总层超差），并落盘
`results/_repro-compare.json`。完整验证过程与结论见 `REPRODUCTION-VERIFICATION.md`。

## 7. 复现容忍度与判读

| 通道 | 容忍度（实测） |
|---|---|
| 模块 A 全部 | **逐位一致**（时间戳除外）——已实测跨会话完全一致 |
| 模块 B · QDCVR 排序指标 | **逐位一致**（Hit@k/Recall@k/nDCG/P@5/MRR）——会话内双轮与跨会话均一致 |
| 模块 B · BM25 等基线 | 跨会话 ≤0.05（索引重建的并列分数 tie-break，源于每次会话文档 UUID 重生成） |
| 模块 B · 跨库查询（demo q-x-*） | 跨会话 ≤0.05（全局 balance 合并的次序依赖 KB UUID；单库查询不受影响） |
| 模块 C 冥想（LLM 生成） | `run_success`/流程稳定；**经验条目数不保证一致（0–10）**；若有产出，子 Agent 评分 ±1.5 |
| 判读 | 报告徽章 r1==r2 为 PASS，且 `compare_runs.py` 汇总层 PASS/PASS* 即复现成立 |

## 8. 标准数据集学术引用（同行基准可信度）

本套件使用的标准测试集均为信息检索/NLP 社区广泛采用的基准（多次用于 CIKM、SIGIR、
ACL、EMNLP 论文的实验环节）：

| 数据集 | 原始论文 | 发表处 | 被引量级 | 本套件用途 |
|---|---|---|---|---|
| BEIR（含 SciFact） | Thakur et al., 2021 — *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of IR Models* | **CIKM 2021**（引用 ~2400+） | 标准 | 检索金标 qrels → Recall@k / nDCG@10 |
| SciFact（原始） | Wadden et al., 2020 — *Fact or Fiction: Verifying Scientific Claims* | EMNLP 2020 | — | 同上（语料来源） |
| SQuAD v1.1 | Rajpurkar et al., 2016 — *SQuAD: 100,000+ Questions for Machine Comprehension of Text* | EMNLP 2016（引用 ~12000+） | 标准 | QA 查询 + 标准答案（answer_hit） |
| XQuAD（可选扩展） | Artetxe et al., 2020 — *On the Cross-lingual Transferability of Monolingual Representations* | ACL 2020（引用 ~1150） | 可选 | 跨语言 QA 扩展赛道 |

## 9. 语料与版本指纹

- 16 篇文档为自撰（`data/`，事实数字可核对）；标准语料 156 篇来自官方
  BEIR SciFact 与 SQuAD v1.1（`data/standard2/`，manifest 固化 sha256 与来源 URL）。
- 查询集 `data/queries.jsonl` 冻结（qid、金标页、答案）。
- 每个结果 JSON 内嵌 `env`：嵌入模型（BAAI/bge-m3）、向量库（ChromaDB）、
  关键词索引（jieba BM25）、检索参数（vector k=10；stage1=40/stage2=10；阈值 0.35）。
- 系统版本：仓库分支 feat/soul-persona-system；kb-mcp 通过 `uv run` 按仓库锁定环境启动。

## 双轨测试流水线（推荐入口）

测试已拆分为两条**完全独立**的流水线，各自产出 MD + HTML 报告：

| 轨道 | 脚本 | 回答的问题 | 报告产物 |
|---|---|---|---|
| **Track R 检索对比** | `pipelines/retrieval_track.sh` | \sys{} 的检索 vs BM25/Dense/Rerank/RAPTOR/ITRG/Search-o1/DeepRead 排序与答案质量如何 | `results/RETRIEVAL-BENCHMARK.md` + `retrieval-benchmark.html` |
| **Track F 平台功能** | `pipelines/functions_track.sh` | 平台自身功能（解析入库/经验生命周期/整理/Agent 面/规模）实测表现 | `results/FUNCTIONS-BENCHMARK.md` + `functions-benchmark.html` |

> 两份报告均为**英文 CIKM 测评风格**（编号章节、环境与可复现性表、表题在上的
> 三线表、每列最优值加粗、方法学注记），由 `scripts/71_track_reports.py` 从
> `results/` 真实执行产物生成——不手写任何数字。

```bash
bash pipelines/retrieval_track.sh    # 检索对比轨（含 E16 八系统矩阵 + API 流程）
bash pipelines/functions_track.sh    # 平台功能轨（A/C/E15/E17/端到端/规模）
# 两条轨道可独立运行、独立复现、互不依赖（仅共享语料入库与后端实例）
```

> 两条轨开头都会自动执行 `scripts/00_preflight.py`（健康检查 / token / omp /
> Track R 额外断言 KB-Hotpot-* 九库空态 + 实验残留 KB 探测）——**fail-loud，
> 不自动删除任何数据**；预检不通过时按输出里的处置指引处理后重跑。
> 也可以单独跑：`python scripts/00_preflight.py [R]`。
> 注意：两轨共享同一个后端/web 实例，**必须串行执行**（见 §7 双轨复现纪律）。

轨道划分原则：Track R 的每一项都**有外部算法对照**；Track F 的每一项都是
**平台独特能力**的功能测试（无外部对照，测自身质量与正确性）。§10 的
E16/E16b 归入 Track R，E17 归入 Track F。


## 10. Stage D · DeepRead 论文基线矩阵 + 平台整理功能评价（E16/E17）

> 目标: 在**同一语料**(KB-SciFact 148 篇)、**同一查询**(BEIR SciFact 30 条)
> 下, 将 QDCVR 真检索 skill 与 DeepRead 论文 (arXiv:2602.05014) Table 1 的
> 全部对比算法同台对比; 检索层指标 + 统一 omp Agent 作答 + 第三方 omp Agent
> 判分, 全部问答逐条落盘。算法忠实度与偏差见
> `algorithms/REPRODUCTION-NOTES.md`（6 项显式登记偏差: 嵌入模型/重排器代理/
> 聚类算法/假设生成模型/轮上限 8/结构来源; 未登记 = 忠实实现）。
>
> **回答内容质量评价（三层, 对全部 8 方法对称）**:
> 1. **统一作答** — 每方法的检索证据截断到同一 4000 字符预算, 交由同一
>    omp Agent 产出 `{verdict, answer, evidence_used}` JSON（隔离检索差异归因）;
> 2. **独立判分** — fresh 进程的第三方 omp Agent, 注入金标文档, 按 0–10 rubric
>    打分: 判定正确性 0–4 + 有据性(无幻觉) 0–4 + 清晰完整 0–2, 判分理由逐条落盘;
> 3. **匿名排名** — 中间 Agent 对去标识后的答案做排名(均位/首位), 排除
>    方法名先验偏差。判分稳定性另由 E15 措辞扰动一致性实验(66 号脚本)守护。

```bash
cd benchmark-suite/algorithms

# 冒烟(2 查询, 验证全链路)
BENCH_LIMIT=2 python run_matrix.py --stage ingest
BENCH_LIMIT=2 python run_matrix.py --stage raptor
BENCH_LIMIT=2 python run_matrix.py --stage retrieve --stage answer                                      --stage judge --stage report

# 全量(30 查询 × 8 方法; 各阶段幂等, LLM 调用按内容哈希缓存可断点续跑)
python run_matrix.py --stage retrieve --stage answer --stage judge --stage report
# → results/run-*/deepread_matrix.json + deepread_qa_transcripts.md

# E17 平台整理功能(去重/标签/图谱/目录完整性; 植入真值的确定性 KB)
cd .. && RAG_BENCH_WEB_URL=http://localhost:6789 python scripts/26_platform_ops_eval.py
# → results/run-*/platform_ops_eval.json
```

要点:
- **Agent 通道 = omp RPC 协议**: agentic 方法(search_o1/deepread)用
  `omp --mode=rpc` 常驻会话多回合; 独立调用(重排/ITRG 假设/作答/判分)用
  `omp -p --mode=json`(与平台 harness 同款)。判分 Agent 与作答 Agent 无共享
  上下文(fresh 进程), 判分注入金标文档。
- 复跑容差: 检索层(dense/raptor 检索/qdcvr/两阶段)确定性 → 逐位一致;
  LLM 通道(重排序、假设句、agentic 轨迹、作答、判分)按 §7 的 LLM 容差判读。
- 产物: `deepread_matrix.json`(汇总+逐查询行)、`deepread_qa_transcripts.md`
  (完整问答记录)、`platform_ops_eval.json`(E17)。
### 10b. E16b · API 模式 — 通过 HTTP 选择检索算法问答（集成在流程内）

```bash
cd benchmark-suite/algorithms
python api_server.py &                # 仅绑定 127.0.0.1:8790; 启动加载 148 金标全文
# 存活/注册表/冻结查询:
curl -s http://127.0.0.1:8790/health
# 单方法问答(检索指标 + 统一作答 + 第三方判分):
curl -s -X POST http://127.0.0.1:8790/ask -H "Content-Type: application/json"      -d '{"method":"qdcvr","qid":"sf-003","judge":true}'
# 同一问题 8 算法并答 + 中间 Agent 匿名排名打分:
curl -s -X POST http://127.0.0.1:8790/compare -H "Content-Type: application/json"      -d '{"qid":"sf-003","rank":true}'
# 全流程测试(30 查询 × 8 方法, 指标+判分+中间Agent排名, 并与 E16 缓存逐字核对):
cd .. && python scripts/27_api_flow_test.py   # BENCH_LIMIT=2 冒烟
# → results/run-*/api_matrix.json + api_side_by_side.md
```

API 与离线矩阵共用同一缓存与冻结 prompt ⇒ 结果逐字一致(27 号脚本内置
consistency 断言, checked/mismatches 落盘 api_matrix.json)。

## 7. 双轨复现纪律（2026-09-16 复现审计沉淀）

functions_track 与 retrieval_track 共享同一个后端/web 实例, **必须串行执行**
（并发实测后果: R0/R3 的 web 调用吃连接拒绝、F1 重入库给 KB-Demo 制造
"(1)" 改名副本使 R1b 数字下滑 0.25）。逐条纪律:

1. 先 F 后 R（或反之）, 上一轨 `exit=0` 再起下一轨。
2. R3 依赖 `RAG_BENCH_WEB_URL=http://localhost:6789`（已在 retrieval_track.sh
   内置导出）; web(6789) 在重负载下会间歇拒绝连接, 拒绝窗口过后重跑即可。
3. R3 前清理目录: 实验残留 KB（KB-Ops-Eval-*/KB-Exp-Ops/KB-UserDemo/UserDemo-*）
   会挤占全局 balance 的 stage1 候选池（per-KB 配额）, 使 HotpotQA 的
   two_stage/qdcvr 通道静默归零; 重复构建会让 Hotpot 库累积 "(1)" 改名副本
   —— 60 号脚本要求 9 个 KB-Hotpot-* 库为空态起步。
4. 复现判定用 `scripts/compare_runs.py <baseline> <candidate>`: module_* 缺失时
   自动回退比较双方共有顶层 JSON; 计时/时间戳/git_commit/run_id 不参与判定,
   LLM 判分容差 ±1.5, 其余逐位。
5. 文档删除不会失效后端内存 BM25 索引（只有 batch-index 与进程重启会触发
   重建）— 大批删改后重启后端再测检索。
