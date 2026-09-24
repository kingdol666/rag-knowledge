# KBQA PIPELINE — 文献入库·复刻入库·出题·三轨对照·分析（可复用全流程）

> **Agent 直启实验入口（2026-09-20 新增）**：`benchmark-suite/experiments/`——
> 同一份 50 篇外部语料上，三模式全部由 Agent 真实执行（A=当前系统对外 API 客户端 /
> B=裸 Agent 全文阅读+全文件搜索 / C=Agent 亲自执行稠密向量检索），带证据底线强制
> （未检索不得作答）。一键：`python -m experiments.runner --question "..." --tracks a,b,c`。
> 详见 `experiments/README.md`。

> **100 篇语料扩展（2026-09-22，当前论文口径）**：manifest 已含两轮共 **100 篇**
> （26 领域），五门类库 322 docs。追加下载 `scripts/97_fetch_papers_round2.py` →
> 解析+拆分门禁 `scripts/98_ingest_round2_phase1.py`（markdown_path 嵌 result、
> max_chars 用 28500 留表头余量）→ 判断件 `data/papers/classification_r2.json` →
> 路由入库 `scripts/99_ingest_round2_phase2.py` → oversized part 重做
> `scripts/102_fix_oversize_parts.py` → A7 终检 `scripts/103_final_check.py` →
> 整理审计 `scripts/100_organize_audit.py` + 应用 `scripts/105_organize_apply.py` →
> 语料导出+Chunks800 重建 `scripts/106_exp_corpus_r2.py` → 三轨检索
> `python -m experiments.runner --questions data/papers/qa_questions_r2.json --tracks a,b,c`
> → 审计 `experiments/audit_paper_numbers.py <run> data/papers/qa_questions_r2.json`
> → 全管线证据汇总 `scripts/108_pipeline_evidence.py`（results/r2_pipeline_100.json）。

> **一句话**：从下载真实文献到三轨对照回答再到分析评价的**完整可复现测试流水线**。
> 执行者 = 一个 Agent（读本文档后按 Stage 0→9 顺序执行）；判断性步骤由 Agent
> 亲自完成并落盘为**判断工件**，脚本只消费工件——**全程真实执行，严禁编造结果
> 或用固定脚本生成假数据（这是本 PIPELINE 的第一红线）**。
>
> 产物目录约定：语料 `data/papers/`、导出 md `data/corpus_md/`、
> 全部结果 `results/`（只增不改）。所有命令在 `benchmark-suite/` 下执行。

## Stage 总览（预计总耗时 ~2.5-3 小时，其中脚本约 100 分钟）

| Stage | 内容 | 执行体 | 脚本/工件 | 预计 |
|---|---|---|---|---|
| 0 | 服务预检 | Agent | `ragctl status` + `/health` | 1 min |
| 1 | 清空知识库 | 脚本 | `scripts/90_reset.py` | 3 min |
| 2 | 下载 50 篇跨领域论文 | 脚本 | `scripts/91_fetch_papers.py`（幂等） | 1-20 min |
| 3a | 解析 50 篇入中转库 + 导出摘要 | 脚本 | `scripts/60_ingest_phase1_parse.py` | 15-20 min |
| 3b | **A1/A3d 内容分类（Agent 判断件）** | **Agent** | 读 `results/ingest_survey.json` → 写 `data/papers/classification.json` | 15-30 min |
| 3c | 按分类路由建 5 门类库 + 索引 + A6-V | 脚本 | `scripts/61_ingest_phase2_classify.py` | 15-20 min |
| 4 | 全部 part 打内容标签（A3b） | 脚本 | `scripts/62_apply_tags.py` | 7 min |
| 5 | 复现项目：导出 md → 清库 → 三套分块建库 | 脚本 | `scripts/70_repro_ingest.py` + `71_repro_smoke.py` | 45-50 min |
| 5b | **重启后端**（BM25 陈旧索引处置） | Agent | `ragctl restart backend` | 1 min |
| 6/7 | **三轨检索实验（experiments 平台，harness=claude）**：A=当前系统对外 chat API / B=裸 Agent / C=Agent 执行稠密 RAG；全监控（时延/token/成本） | 平台 | `python -m experiments.runner --questions data/papers/qa_questions.json --tracks a,b,c` | 40-70 min |
| 8 | 报告生成 | 平台+脚本 | `experiments` 输出 `SUMMARY.md`（监控表+逐题全文）；`78`/`81` 消费旧通道存档 | 1 min |
| 9 | **结果分析评价（Agent 判断件）** | **Agent** | 读 experiments JSON/SUMMARY + 存档工件 → 写 `results/ANALYSIS.md` | 15 min |

> **归档通道（2026-09-18/19 历史运行史，新轮次不再执行）**：`72_bench10_verify.py`
> （two_stage 时代回归）、`75/76_skill_track_*`（MCP 采集 + Agent 五段式）、
> `77_tracks_bc.py`（omp 版 B/C）、`78/81`（消费旧通道工件的报告）。仅在需要
> 复现历史报告时按原说明运行。

```bash
# 脚本段一键串行参考（Agent 判断段见各 Stage 说明, 不可跳过）
python scripts/90_reset.py && python scripts/91_fetch_papers.py && \
python scripts/60_ingest_phase1_parse.py &&   # → Agent 写 classification.json
python scripts/61_ingest_phase2_classify.py && python scripts/62_apply_tags.py && \
python scripts/70_repro_ingest.py && python scripts/71_repro_smoke.py && \
# → Agent: ragctl restart backend
python scripts/72_bench10_verify.py && \
python scripts/75_skill_track_phase1.py       # → Agent 写 skill_track_answers.json
python scripts/76_skill_track_phase2.py       # 仅有门控<6 的题目时执行
python scripts/77_tracks_bc.py && \
python scripts/74_threeway_report.py && python scripts/78_replication_report.py
# → Agent 写 results/ANALYSIS.md
```

---

## Stage 0 — 服务预检

```bash
cd <repo-root> && ragctl status        # Backend:8771 / Web:6789 / Neo4j / MinerU 全部 healthy
curl -s http://localhost:8771/health   # {"status":"healthy"}
```
不健康 → `ragctl up --mode dev`（冷启动 ~20s）后再查。依赖：Python 3.11+、curl、
uv、omp（Stage 7）。

## Stage 1 — 清空知识库

```bash
python scripts/90_reset.py
```
通过判据：输出 `ok: true`（catalog=0，幽灵目录兜底清理）。

## Stage 2 — 下载真实文献（幂等）

```bash
python scripts/91_fetch_papers.py
```
- `scripts/91` 内 `SPECS` 定义领域×数量（当前 26 领域 50 篇；8 领域×3、4 领域×2、
  14 领域×1）。Agent 可按需修改 SPECS，但必须重算总数与 TARGET 一致。
- 护栏：https + arXiv host 白名单 + DNS 解析逐 IP 公网校验 + XML 拒绝
  DOCTYPE/ENTITY；传输层 curl（urllib TLS 指纹在本机网络会间歇 406）。
- 通过判据：`data/papers/manifest.json` papers 数 = 50，全部含 sha256。

## Stage 3a — 解析入库到中转库（官方链路）

```bash
python scripts/60_ingest_phase1_parse.py
```
每篇 PDF：`parse_doc`(MinerU) → `kb_doc_save_parsed` 入中转库 `Papers-Inbox`
（A0 同 arxiv_id 去重）。完成后导出 `results/ingest_survey.json`：每篇标题+
正文前 1400 字（**这是 Stage 3b 的唯一分类依据**）。
通过判据：50/50 parsed；全部探针可检索。

## Stage 3b — 内容驱动分类（Agent 判断件 ⭐ 严禁跳过或机械生成）

1. Agent 生成摘要清单并**逐篇研读**：
   ```bash
   python - <<'PY'
   import json, re
   d = json.load(open('results/ingest_survey.json', encoding='utf-8'))
   for i, p in enumerate(d['papers'], 1):
       ex = re.sub(r'\s+', ' ', p['excerpt'])
       print(f"[{i}] {p['field']} | {p['arxiv_id']} | {p['title'][:70]}")
       print(f"    {ex[:330]}")
   PY
   ```
2. 按论文**实际正文内容**把每篇分配到门类库并给 2-3 个内容标签，写入
   `data/papers/classification.json`（schema 见文件内 `classified_by` 说明）。
   - 门类集合由 Agent 依语料构成判定（当前 5 类）。
   - **禁止只看文件名/领域前缀分类**：必须读摘要；与文件名先验相反时以内容为准
     （历史实例：neuroscience 文件名的 SNN 算法论文 → 计算机；agriculture 文件名
     的人口遗传学论文 → 生命科学），并在该条目加 `note` 说明理由。
3. 通过判据：`assign` 键数 = 论文数，无遗漏。

## Stage 3c — 按分类路由入库

```bash
python scripts/61_ingest_phase2_classify.py
```
脚本消费 `classification.json`：建门类库 → 逐篇读 Inbox 全文 → `kb_doc_create`
路由入库 → 删中转库 → batch-index force → A6-V 逐篇在自己门类库内探针 → 门类图谱。
通过判据：`verified == total`（当前=50/50）；`graph` 全 true。

## Stage 4 — 内容标签（A3b）

```bash
python scripts/62_apply_tags.py
```
对每个文档 part 打所属论文的内容标签（大文档自动拆分为 `(part k of N)`）。
通过判据：`tagged ok=N fail=0`。

## Stage 5 — 复现项目入库（RAG 复刻算法的库）

```bash
python scripts/70_repro_ingest.py
python scripts/71_repro_smoke.py
```
- 70：从 5 门类库按篇读回 → `data/corpus_md/*.md`（50 篇）→ 清理
  `LitQA-*`/`Corpus-*` 旧库 → 复现项目自有分块方案建
  `Corpus-Chunks800/Struct/Paras`（Paras 约 11k chunks，最慢 ~35 min）。
- 71：dense 检索冒烟（**必须先 activate_profile 重绑 methods 模块 KB 常量**，
  否则静默检索不存在的库）**+ 向量库全覆盖校验（2026-09-19 新增 ⭐）**：
  本地用同一分块函数重算期望 chunk 清单 → 与库内清单总数/逐篇双向对账 →
  Corpus-Chunks800 逐篇尾块探针（尾块最易丢失，50/50 可检索才允许放行）。
- 通过判据：`exported=50`、三库 probe 全过、smoke `chunks>0`、
  `repro_coverage.json` 全部 pass（missing=0 且 cid 对账一致且尾块探针 50/50）。

## Stage 5b — 重启后端（必做 ⭐）

```bash
cd <repo-root> && ragctl restart backend && curl -s http://localhost:8771/health
```
大批删建后端内存 BM25 索引会陈旧（实测两次：删库重建后检索答案错库），
不重启则 Stage 6/7 的 two_stage 结果不可信。

## Stage 6/7 — 检索任务测试（2026-09-20 改版：统一走 experiments 实验平台 ⭐）

检索类测试**全部**使用 `benchmark-suite/experiments/` 平台执行（`python -m experiments.runner ...`），
harness 统一为 **claude**，同一份 50 篇外部语料，三模式定义：

| 轨道 | 入口 | 协议 |
|---|---|---|
| **A · 当前系统** | **对外暴露的正式接口** `POST /api/claude/chat` + `engine:"claude"`（外部调用方获取系统回答的唯一入口），无工具限制 | 系统自带 QDCVR 全流程 |
| **B · 裸 Agent** | 同一 chat API，`cwd=corpus_md`，`allowedTools=["Read","Grep","Glob"]` | 全文阅读 + 全文件搜索 |
| **C · RAG 向量** | 同一 chat API，`allowedTools=["mcp__kb-mcp__kb_search_vector"]` | **Agent 亲自执行**稠密向量检索（Corpus-Chunks800），仅凭检索块作答 |

**监控（已内建，逐 run 落盘）**：完整事件时间线、每次工具调用、助手全文、
墙钟时延、SDK duration_ms/num_turns、**token 消耗（input/output/cache_read/cache_creation）**、
total_cost_usd；权限请求自动拒绝并计数（实验只读）。证据底线（C 轨 toolloop 模式）与
allowedTools 白名单（chat 模式）双通道保证"答案必须来自真实检索"。

```bash
cd benchmark-suite
python -m experiments.runner --questions data/papers/qa_questions.json --tracks a,b,c   # 10 题全量
python -m experiments.runner --question "..." --tracks a                                 # 单题单轨
```

结果：`results/experiment_chat_<ts>/`（逐轨 JSON 轨迹 + `SUMMARY.md` 监控表与逐题全文）。
历史 Stage 6（two_stage/bench10 脚本回归）与 75/76（MCP 采集 Track A）保留为归档路径；
**新检索测试一律走本平台，不再新增 two_stage 通道**。

## Stage 7a/7b — 【归档】MCP 采集版三轨（2026-09-18/19 历史运行史）

> ⚠️ 新轮次检索测试**不再执行本节**——一律走 Stage 6/7 的 experiments 平台。
> 本节保留用于复现历史报告（skill_threeway_replication.md 旧版）。

1. 脚本采集（Phase 0/1 工具调用段，全程计时）：
   ```bash
   python scripts/75_skill_track_phase1.py
   ```
   Phase 0 改写表 `REWRITES` 由 Agent 按语料更新（旧语料复跑可沿用）。
   **注意**：检索范围是 5 门类库——整库 `kb_id=""` 会把复现项目的 Corpus-* 索引
   库也搜进来污染结果（实测）。
2. **Agent 研读证据并产出 `results/skill_track_answers.json`**：
   - 导出证据摘要（每题 top-3 的 chunk_text+head_excerpt）逐题研读；
   - 按 0-8 评分细则（主题 0-3 / 场景 0-3 / 证据 0-2）给最高分文档打分：
     **≥6 快速退出；=5 留后备并触发兜底；≤4 立即兜底**；
   - 长文条款：头窗不含答案时按 chunk 锚定 + 续读（`76` 号的定向再检索）；
   - 每题按 skill Phase 3 格式撰写五段式回答（Search Paths / Answer / Sources /
     Confidence / Blind Spots）——**回答只能引用读到的正文，读不到就如实写进
     Blind Spots**。
3. 若存在门控 <6 的题目：
   ```bash
   python scripts/76_skill_track_phase2.py   # PHASE2 表由 Agent 按题填写
   ```
通过判据：10/10 题在 `skill_track_answers.json` 有门控分数与五段式回答；
兜底题在 evidence JSON 里有 phase2 记录。

## Stage 7b — 【归档】Track B/C（omp 版）

> ⚠️ 归档说明同 Stage 7a。新轮次走 experiments 平台（chat API + claude harness）。

```bash
python scripts/77_tracks_bc.py
```
- B：裸 Agent（omp 保留文件工具，cwd=`data/corpus_md/`，每题独立会话）；
- C：`methods.dense`（Corpus-Chunks800）→ 4000 字符证据包 → 统一作答 prompt。
通过判据：20 条回答（10 题 × 2 轨）全部落盘 `results/track_bc.json`。

## Stage 8 — 报告

**当前流程（experiments 平台）**：runner 自动生成
`results/experiment_chat_<ts>/SUMMARY.md` —— 监控表（逐题时延/工具调用/
tokens in-out/cache/成本）+ 逐题三轨回答**原文全文**，即检索报告本体；
Agent 在 Stage 9 基于它写 ANALYSIS.md。

**归档报告器（仅旧通道复现用）**：
```bash
python scripts/78_replication_report.py  # results/skill_threeway_replication.md
python scripts/81_visual_report.py       # results/benchmark_visual_report.html
```
- 78 = 旧通道全文记录 MD（管线统计 + 覆盖率 + 检索回归 + 三轨逐题原文）。
- 81 = 可视化 HTML（漏斗卡片/覆盖率/回归/三轨时延/逐题原文折叠面板；
  teal=平台/gray=baseline/橙红=警示）。
- `74_threeway_qa.json` 通道（two_stage 版 Track A）已废弃，仅存档。
报告只做汇整，**不做任何评价性改写**；回答一律原文引用。
**语言红线：提问一律英文，三轨回答一律英文**（当前流程由 chat_tracks 的
B/C prompt 硬约束 + 各轨系统提示；ToolAgent 遗留模式由 BARE_PROMPT /
SCEN_ANSWER_PROMPT 硬约束）。

## Stage 9 — 结果分析评价（Agent 判断件 ⭐）

Agent 通读 Stage 6/7/8 的全部 JSON 与 MD，写 `results/ANALYSIS.md`，必须包含：
1. **语料与入库统计**（真实数字取自 upload_parse/repro_ingest/ingest_report）；
2. **检索回归结果**（pass_rate 与失败题逐题归因）；
3. **三轨对照**（时延对比、金标词命中率、弃答/兜底行为）；
4. **诚实披露**（证据预算截断、分块窗口效应、单 LLM 判读的局限、不可复现项）；
5. **结论与改进方向**。
评价只允许引用落盘数字；没有的数字写"未测量"。

---

# V2 实验流程（2026-09-24 新增 · 论文级证据链）

> **为什么加这一段**：Stage 0–9 证明了"工程可信"（真实执行、不编造、可追溯），
> 但它的因变量是关键词命中、题集只有 10 题单跳、对照组是被砍掉工具的自己、
> 且 A 轨的 cwd 是仓库根目录（可读到答案键）。**这些数字能当工程辅证，不能当
> 机制主证。** V2 把实验升级为「2×2 析因 + 真实 baseline + 分层题集 + 外部 judge
> + 池化 qrels + 显著性」，让最终报告能严谨证明核心机制（内容裁决）有效。
>
> 设计依据见 [`EXPERIMENT-DESIGN-V2.md`](./EXPERIMENT-DESIGN-V2.md)。
> 全部问答**必须真实经过被测系统的对外 API**：`POST /api/claude/chat`
> （harness=claude），或 baseline 的检索 + 同一 chat API 作答。
>
> **前置**：Stage 0–5 已完成（100 篇语料 · 五门类库 · Corpus-Chunks800 已建）。

## V2 Stage 总览

| Stage | 内容 | 执行体 | 脚本/入口 | 通过判据 |
|---|---|---|---|---|
| V0 | 服务与索引预检 | Agent | `ragctl status` + `/health` + 向量探针 | 后端/Web healthy，探针命中 |
| V1 | **答案键隔离**（内部效度） | 脚本 | `experiments/chat_tracks.py` 内置断言 | 导入不抛 AssertionError |
| V2 | 题集构建与校验（80 题六层） | Agent+脚本 | `scripts/112_question_set.py` | `--validate` 退出 0 |
| V3 | **基线复现**（6 个，同一后端） | 脚本 | `scripts/113_baselines.py` | 全部 row 无 error |
| V4 | **主实验执行**（A/A2/B/C + baselines） | 平台 | **`python exp.py`**（一键对照）或 `python -m experiments.runner` | 每 (qid,track) 落盘 JSON + `COMPARE.md` 自检全绿 |
| V5 | 池化标注 qrels | 人工+脚本 | `scripts/114_pool_qrels.py` | 池覆盖全部方法 top-10 |
| V6 | 评分（L1 确定性 + L2 外部 judge） | 脚本 | `scripts/110_stratified_grade.py --judge` | 产出 `judge.json` |
| V7 | 显著性统计 | 脚本 | `scripts/115_stats.py` | Wilcoxon/Holm/CI 全部落盘 |
| V8 | 报告生成 | 脚本 | `scripts/116_experiment_report.py` | `REPORT.md` 生成 |
| V9 | provenance 审计 | 脚本 | `scripts/115`+`116` 内嵌 + `provenance_audit.py` | manifest 含 git/config/seed |
| V10 | **管线自检**（离线可跑） | 脚本 | `scripts/117_pipeline_selfcheck.py` | 39 项检查 0 fail |

---

## V2-Quick10 — 10 题全功能快速测试（首次运行走这条）⭐

> **目的**：用最小题量（10 题）把系统的关键功能测完整，一条命令拿到可直接看的结果报告。
> 题集已出好并校验通过：`data/papers/qa_quick10.json`。**不需要先出 80 题。**

### 题目与覆盖功能

| QID | 层 | 覆盖的系统功能 | gold |
|---|---|---|---|
| QK01 | single | 检索召回 + 端到端作答 + **引用溯源** | 1706.03762 |
| QK02 | single | 检索召回（跨库：基因组学） | 1602.01876 |
| QK03 | single | 检索召回（材料/机理类） | 1606.00335 |
| QK04 | single · numeric | **数值抽取**（94%） | 2209.15032 |
| QK05 | single · numeric | **数值抽取**（7–10%） | 2508.05896 |
| QK06 | single · chunk-window | **长文档分块窗口**（历史失败模式） | 1503.07557 |
| QK07 | distractor | **同域干扰对抗**（多篇 LM 抢召回） | 2608.05850 |
| QK08 | crosskb | **跨库路由**（GAN/气候降尺度） | 2409.13934 |
| QK09 | unanswerable | **显式拒答**（库内有相邻文档但答不了） | —（无解） |
| QK10 | outofcorpus | **零编造**（完全域外） | —（无解） |

### Agent Harness 执行步骤（逐步照做）

```bash
cd benchmark-suite

# 0) 管线自检（离线，~3 秒；确认脚本/工件/契约都在）
python scripts/117_pipeline_selfcheck.py

# 1) 平台预检（token 过期会自动重新登录）
python exp.py --check

# 2) 10 题 × 5 方法 真实对照（项目 a2 + 4 baseline）
#    约 20 分钟（a2 单题 ~97s 占大头）
python exp.py --questions data/papers/qa_quick10.json --baselines bm25,vector,rrf,rerank

# 3) L2 外部 judge（主因变量；需先配置 JUDGE_ENDPOINT/MODEL/KEY）
python scripts/110_stratified_grade.py --run <上一步打印的 run_id> \
    --qfile data/papers/qa_quick10.json --judge

# 4) 汇总报告（主表 + 分层 + 显著性）
python scripts/116_experiment_report.py --run <run_id>
```

> 第 2 步的 run 目录会打印为 `results/runs/run-<utc>-<sha>/`；把它作为 `<run_id>`
> 传给第 3/4 步。若只想重生成对照报告：`python exp.py --report <run_id> --questions data/papers/qa_quick10.json`。

### 产出（`results/runs/<run_id>/`）

| 文件 | 内容 |
|---|---|
| `COMPARE.html` | **可视化仪表盘**（资源监控 / 功能验证 / 逐题并列 / 自检，可排序、可切深色） |
| `COMPARE.md` | 同上的 Markdown 版（含逐字答案全文） |
| `monitor.json` | 机读版（供二次分析） |
| `SUMMARY.md` | 逐题监控表 + 逐字答案 |
| `run_manifest.json` | provenance（git / config / prompt_version / seed / 成本合计） |
| `judge.json` | L2 逐题正确性（配了 judge 才有） |
| `REPORT.md` | 主表 + 分层 + 显著性 + 未测量项 |

### 通过判据（决定"这次测试是否有效"）

| 判据 | 期望 |
|---|---|
| `COMPARE.md` 一致性自检 | **全部 ✅**（无缺失/重复/error；成本合计自洽；单元数 = 10×方法数） |
| QK01–QK08 检索金标命中 | ≥ 7/8（历史实测 8/8；未达标要逐题归因） |
| QK09 / QK10 | **必须弃答**（not-found 报告），且答案中不得出现编造的剂量/方法 |
| error 单元 | 0 |
| 弃答（QK01–QK08） | 越低越好（误拒率）；与 QK09/QK10 的拒答率**必须同时报** |

> **能证明什么**：系统的检索/路由/裁决/拒答/引用/长文/干扰八项功能**均被这 10 题触达**，
> 报告可作"功能可用性 + 效率"的证据（n=10，属快速验证，非统计结论）。
> **不能证明什么**：内容裁决的**因果贡献**（需 2×2 析因，见下）；跨语料泛化。

---

## V2 数据流契约（工件 → 生产者 → 消费者）

> 全管线只认一个 run 目录：**`results/runs/<run_id>/`**（`run_id = run-<utc-ts>-<gitsha>`，
> 由 `lib.new_run_dir()` 生成，**不可原地覆盖**）。生产者与消费者必须同名，否则下游静默读空。

| 工件 | 生产者 | 消费者 | 说明 |
|---|---|---|---|
| `data/papers/qa_v2.json` | 112 `--skeleton` + 人工/Agent 填写 | 113 / runner / 110 / 114 / compare | 80 题六层题集 |
| `track_<method>_<qid>.json` | runner / exp | compare_report / 114 / 116 | 每个 (题×方法) 一个单元 |
| `baselines.json` | 113 | 114 / 116 / compare_report | 6 baseline 逐题结果 |
| `run_manifest.json` | runner / exp | compare_report（自检对账）/ 116 | provenance + n_rows + total_cost |
| `SUMMARY.md` | runner | 人工 | 监控表 + 逐字答案 |
| `COMPARE.md` / `monitor.json` | compare_report | exp / 人工 | 并列对照 + 资源监控 |
| `COMPARE.html` | compare_html | 人工 | 可视化仪表盘 |
| `qrels_pool.json` | 114 `--build` | 标注者 | 池化标注模板 |
| `qrels_scores.json` | 114 `--score` | 116 | P@5/R@10/nDCG@10/MRR |
| `judge.json` | 110 `--judge` | 115 / 116 | L2 主因变量逐题结果 |
| `stats.json` | 115 | 116 | 显著性 + CI + power |
| `REPORT.md` / `report.json` | 116 | 人工 / 论文 | 主表 + 分层 + 显著性 |

**不变量**（V10 自检会逐条验证）：
1. 生产者写出的文件名 = 消费者读取的文件名；
2. 生产者与消费者都用规范 run 目录；
3. `compare_report` 的 6 项一致性自检全绿（单元数 = 题数 × 方法数；成本合计 = 各方法之和；无缺失/重复/error；provenance 完整）。

---

## V2 功能 ↔ 实验 ↔ 指标 对应表（杜绝"实验与功能无关"）

> 每一行 = 系统的一个真实功能 → 验证它的实验 → 直接对应的指标 → 报告位置。
> **没有对应行的功能不得在论文里声称"已验证"；没有功能对应的实验不得进主表。**

| # | 系统真实功能（可核验的实现） | 验证实验 | 指标（直接对应） | 报告位置 |
|:--:|---|---|---|---|
| F1 | 内容裁决（读正文打 0–8 分，低分丢弃） | 2×2 析因：裁决 ON/OFF | 主效应 Δ正确率 / ΔFPR；交互项 | Table 3 + 裁决散点图 |
| F2 | 内容路由组织（按内容分门类库） | 2×2 析因：组织 ON/OFF | 交互项（organization × adjudication） | Table 3 |
| F3 | 向量召回（BGE-M3 / ChromaDB） | C 轨 + `vector` baseline | P@5 / R@10 / nDCG@10 / MRR | Table 2 |
| F4 | 显式 not-found 契约（不编造） | 应拒答层 12 题 + 域外 8 题 | not-found 正确率 **+ 误拒率**（双向） | Table 5 / 诚实性表 |
| F5 | 跨域干扰鲁棒性（核心卖点） | 干扰对抗层 15 题 | **FPR**（coverage-aware） | Table 2 / Fig |
| F6 | 引用可溯源（到 part/section） | 全方法引用金标命中率 | citation gold rate | COMPARE.md 功能验证表 |
| F7 | 检索后按需读取（librarian 兜底） | 消融 −馆员兜底 | Δ正确率（同题集同 qrels） | Table 5 |
| F8 | 分块/索引方案 | 分块匹配臂（同 800-char 单元） | ΔP@5（排除分块混淆） | Table 5 |
| F9 | 多 KB 路由 + balance_kbs | 跨库对比层 10 题 | 跨库熵 / nDCG@10 | Table 2 分层 |
| F10 | 效率（时延/成本） | 全方法监控 | 时延 median+IQR · 成本 · 等预算质量 | quality–latency/cost 曲线 |
| F11 | 平台工程可用性（94 MCP 工具 / API） | Stage 0–9 + V10 自检 | 端到端 73 检查 / 自检 39 项 | 工程附录 |

**边界声明（防止结论越界）**：
- 若未跑 2×2 析因（需平台"关闭内容裁决"开关），**F1/F2 不得声称已验证**，只能写"架构动机"。
- 若未做人工 κ（L3），**0–8 rubric 不得声称已校准**。
- 若干扰对抗层未跑（F5），跨域干扰结论必须限定为"机制性论证"。
- 若公开多域轨（FlashRAG/HotpotQA 拆库）未跑，结论必须**限定在自建语料**。

---

## V2 真实验证记录（管线已实测跑通）

> 本节记录一次**真实**的端到端运行，用于证明管线可执行、产物可复现、自检自洽。
> 它不是实验结果（n=1），只是"管线可用"的证据。

| 项 | 值 |
|---|---|
| 命令 | `python exp.py --questions data/papers/qa_questions_r2.json --limit 1 --baselines bm25,vector,rrf,rerank` |
| run 目录 | `results/runs/run-20260924T052520Z-0968033/` |
| 方法 | 项目 `a2` + baseline `bm25,vector,rrf,rerank` |
| 真实调用 | `a2` 经 `POST /api/claude/chat`，实际调用 `kb_search_vector` / `kb_search` / `kb_search_two_stage` / `kb_doc_read`（6 次工具调用） |
| 结果 | a2 96.8s · 106 691 tok in · $0.6149；baseline 11.5–32.4s · $0.022–$0.194 |
| 功能验证 | 全部方法 检索金标命中 1.0 · 引用金标命中 1.0 · 0 弃答 · 0 error |
| 自检 | **6/6 ✅**（单元数=5=1×5；成本合计自洽 1.0498 vs 1.0497；provenance 完整） |
| 产物 | `COMPARE.md` · `COMPARE.html` · `monitor.json` · `SUMMARY.md` · `run_manifest.json` |

**本次真实运行暴露并修掉的 4 个缺陷**（这类问题只有真跑才会出现）：
1. **token 过期导致全轨 401** → 新增 `lib.check_token()` + `login_refresh()`，预检验证 token 并对过期**自动重新登录**（`chat_tracks` 401 时同样自愈重试）。
2. **`runner.summary` KeyError: 'track'** → baseline 行用 `method` 而非 `track`，已统一取值。
3. **launcher 丢弃题集 gold 字段** → `exp._load_questions` 保留完整题目 dict，金标核对才生效。
4. **三套 run 目录约定不一致**（数据流转断裂）→ 统一为 `results/runs/<run_id>/`。

> **未闭环项（不得越界声明）**：① L2 外部 judge 未配置（`JUDGE_ENDPOINT/MODEL/KEY`），
> 当前主因变量仍是 L1 金标/关键词；② 平台尚无"关闭内容裁决"开关 → 2×2 析因跑不了；
> ③ `qa_v2.json` 80 题未出题；④ qrels 池化标注与人工 κ 属人力步骤。

---

## Stage V0 — 服务与索引预检

```bash
cd <repo-root> && ragctl status
curl -s http://localhost:8771/api/v1/health
cd benchmark-suite && python - <<'PY'
import sys; sys.path.insert(0,"scripts")
from lib import http_post
r = http_post("http://localhost:8771/api/v1/search/vector",
              {"query":"precipitation extremes climate change",
               "kb_id":"Corpus-Chunks800","top_k":3,"score_threshold":0.0})
print("vector hits:", len(r.get("results") or []))
PY
```
通过判据：服务 healthy，且向量探针 `hits >= 1`。不通过 → `ragctl up`（冷启动 ~20s）。

## Stage V1 — 答案键隔离（内部效度红线 ⭐）

**问题**：金标答案在仓库内（`data/papers/qa_questions*.json`、
`results/experiment_chat_*/SUMMARY.md`）。若被测轨（A）的 cwd = 仓库根且带
`Read/Grep/Glob`，它就能读答案键——这是内部效度缺陷，不是统计问题。

**已落地的修法**（无需额外操作，导入即生效）：
- 带文件工具的轨（`a`/`b`）cwd 一律钉在语料目录 `data/corpus_md/`；
- 平台主轨 `a2` 只有 `kb_*` 工具、无文件工具（cwd=仓库根也无害）；
- `chat_tracks.py` 在 import 时断言：**任何"有文件工具 ∧ cwd=仓库根"的轨都拒绝构造**。

```bash
cd benchmark-suite && python -c "
import sys; sys.path.insert(0,'experiments')
import chat_tracks as ct
print('prompt_version:', ct.PROMPT_VERSION)
for t,s in ct.TRACKS.items(): print(' ', t, s['cwd'], len(s['allowed_tools']),'tools')
print('leak-guard OK')"
```
通过判据：输出 `leak-guard OK`（未抛 AssertionError）。
**若新增轨，必须同时满足该断言，否则实验作废。**

## Stage V2 — 题集构建与校验（80 题六层）

分层配额：`single 20 · multihop 15 · crosskb 10 · distractor 15 · unanswerable 12 · outofcorpus 8`。

```bash
# 1) 生成骨架（只含标题+摘要首句，防泄漏：出题者禁看正文）
python scripts/112_question_set.py --skeleton --out data/papers/qa_v2.json

# 2) Agent/人工按骨架填写 question 与 3-5 条 gold_points（语义要点，非逐字关键词）
#    出题规程：只看 candidate_title + abstract_first_sentence；3 人各复核 1/3

# 3) 校验
python scripts/112_question_set.py --validate data/papers/qa_v2.json --strict-quota
python scripts/112_question_set.py --stats data/papers/qa_v2.json
```
通过判据：`--validate` 退出 0（`--strict-quota` 下六层数量精确相等）。
**红线**：`gold_points` 必须是语义要点；`gold_keywords` 仅作 L1 回归层，尽量少用。

## Stage V3 — 基线复现（6 个，同一后端）

全部 baseline 在**同一 Chroma 索引 + 本地 BM25** 上检索，再用**同一 chat API**
（`answer_closed_book`，无工具）作答——生成步完全一致，差异只归因于检索。

```bash
python scripts/113_baselines.py --questions data/papers/qa_v2.json \
    --methods bm25,vector,rrf,rerank,crag,selfrag --limit 80
# 冒烟：单题单方法
python scripts/113_baselines.py --question "What is MultiMedQA?" --methods bm25,vector
```
- `bm25` 文档级 Okapi BM25；`vector` 走 `POST /api/v1/search/vector`（Corpus-Chunks800）；
  `rrf` 融合两者；`rerank` = 向量 top-30 → LLM listwise 重排 top-10；
  `crag`/`selfrag` = 简化版纠正/自反思（**报告须声明非原论文代码**）。
- 输出：`results/runs/<run_id>/baselines.json`（含 env 指纹）。
通过判据：所有 row `error` 缺省（`n_ok == n_rows`）。

## Stage V4 — 主实验执行（析因 + 公平三轨）

### V4a — 一键对照启动（推荐入口 · exp.py）⭐

**直接启动实验平台**，输入同一问题，一次跑「项目 + baseline」并输出并列对照 + 资源监控：

```bash
python exp.py "Which three ontologies subdivide the Gene Ontology?"   # 单题对照
python exp.py --questions data/papers/qa_v2.json --limit 10           # 多题对照
python exp.py --fast                                                  # 1 题快速冒烟
python exp.py --full                                                  # a,a2,b,c + 6 baseline
python exp.py --monitor-system                                        # 加采样 CPU/RSS/GPU（需 psutil）
python exp.py --check                                                 # 只做平台预检
python exp.py --report results/experiment_chat_<ts>                   # 只重生成对照报告
```
- 默认对照集：项目 `a2` + baseline `bm25,vector,rrf,rerank`（5 方法/题）。
- **同一问题、同一 chat API**：项目与 baseline 的回答都经 `POST /api/claude/chat`。
- 产出 `COMPARE.md`（逐题并列 + 资源监控 + 功能验证 + 一致性自检）与 `monitor.json`。
- 控制台直接打印对照表（时延 / tokens / 成本 / 工具数 / 检索命中 / 引用命中 / 弃答）。

### V4b — 精细控制（runner CLI）

```bash
# 快速冒烟（3 题 · a2,b,c · 关闭自愈重启）
python -m experiments.runner --fast

# 完整公平集（平台主轨 a2 + 裸 Agent b + 稠密 RAG c）
python -m experiments.runner --questions data/papers/qa_v2.json --tracks a2,b,c

# 文件工具证伪臂（a − a2 = 文件工具的边际价值）
python -m experiments.runner --questions data/papers/qa_v2.json --tracks a,a2

# 析因：组织 × 裁决（需平台提供"关闭内容裁决"开关，见 EXPERIMENT-DESIGN-V2 §3）
python -m experiments.runner --questions data/papers/qa_v2.json --tracks a2,b,c
```
- 轨序**逐题随机化**（`--seed`，`--no-shuffle` 可关）；`--max-turns` 对所有轨统一。
- 每次回答都经 `POST /api/claude/chat`（真实系统 API）。
- 输出：`results/runs/<run_id>/track_*.json` + `SUMMARY.md` + `run_manifest.json`（规范 run 目录）。
通过判据：每个 (qid, track) 都有 JSON 落盘；`run_manifest.json` 含 git/config/prompt_version/seed；
`COMPARE.md` 的「一致性自检」全部 ✅（无缺失单元、无重复、无 error、成本合计自洽、provenance 完整）。

## Stage V5 — 池化标注 qrels

```bash
python scripts/114_pool_qrels.py --build --run results/runs/<run_id>
# → qrels_pool.json：所有方法每题 top-10 的并集，3 标注者 × graded 0/1/2/3
# 人工/Agent 标注后：
python scripts/114_pool_qrels.py --score --run results/runs/<run_id> \
    --questions data/papers/qa_v2.json
```
通过判据：`qrels_scores.json` 产出，且 P@5/R@10/nDCG@10/MRR 逐方法有值。
未标注默认 0（TREC 假设）——**必须在报告里声明**。

## Stage V6 — 评分（L1 + L2）

```bash
# L1 确定性层 + L2 外部 judge（judge 必须与被测系统解耦）
export JUDGE_ENDPOINT=https://api.deepseek.com/v1/chat/completions
export JUDGE_MODEL=deepseek-chat
export JUDGE_API_KEY=...
python scripts/110_stratified_grade.py \
    --run experiment_chat_<ts> --qfile data/papers/qa_v2.json --judge
```
- L1（`pass`）= 金标可追溯 ∧ ≥60% 关键词，**仅作回归层**；
- **主因变量 = L2 judge correctness**（0/1 + quality 0-5），外部模型、temperature=0；
- 拒绝用被测平台自身当 judge（脚本已硬约束）。
通过判据：`<run>/judge.json` 生成（逐题 `correct`/`quality`）。

## Stage V7 — 显著性统计

```bash
# ≥5 次重复后：把 5 个 run 目录一起传入
python scripts/115_stats.py --runs results/runs/run-A,results/runs/run-B,results/runs/run-C \
    --file judge.json --metric correct --ref bm25 --out stats.json
```
产出：mean±SD、Wilcoxon signed-rank（含并列+连续性校正）、Holm 校正、
bootstrap 95% CI、rank-biserial 效应量、power statement。
通过判据：`stats.json` 含 `descriptives`/`comparisons`/`power`。
**红线**：每个 LLM 通道配置 **≥5 次**运行；正文写 power statement。

## Stage V8 — 报告生成

**对照报告（逐题并列 + 资源监控，回答"项目比 baseline 好在哪"）**：

```bash
# 实验执行时已自动生成；也可对已有 run 单独重生成
python exp.py --report results/experiment_chat_<ts> --questions data/papers/qa_v2.json
# 等价：
python -m experiments.compare_report --run results/experiment_chat_<ts> \
    --questions data/papers/qa_v2.json
```
产出 `COMPARE.md` + `monitor.json`：资源监控总表、功能验证（检索/引用金标命中率、弃答数）、
逐题并列对照（含逐字答案全文）、**一致性自检**。

**汇总报告（主表 + 分层 + 显著性）**：

```bash
python scripts/116_experiment_report.py --run results/runs/<run_id>
```
产出 `REPORT.md`（主表 + 分层 + 显著性 + 未测量项）与 `report.json`。

通过判据：`COMPARE.md` 生成且自检全绿；`REPORT.md` 生成；缺项以"未测量"如实标注，**禁止编造**。

## Stage V9 — provenance 审计

```bash
python docs/paper/cikm/provenance_audit.py      # 若已接入 CI
```
每个结果文件须内嵌：git commit · config hash · seed · prompt_version ·
BGE-M3 HF revision · Chroma HNSW 参数（M / ef_construction / ef_search）。
通过判据：`run_manifest.json` 字段齐全；结果目录为 `results/runs/<utc-ts>-<sha>/`，**不可原地覆盖**。

## Stage V10 — 管线自检（离线可跑，不调用 API）

```bash
python scripts/117_pipeline_selfcheck.py
python scripts/117_pipeline_selfcheck.py --no-chain      # 只做静态检查
```
检查 5 类共 39 项：① 文件齐全 ② 模块可导入（含**答案键隔离断言**）③ 题集合法
④ 阶段契约（生产者文件名 ↔ 消费者）⑤ **端到端 dry-run 链**
（runner → compare_report → compare_html → 116，全程不调 API）。
通过判据：**0 fail**（题集未就绪允许 1 个 warn）。

> **运行前必跑 V10**：它能在几秒内发现"脚本改名 / 工件改名 / 题集缺字段 / run 目录不规范"
> 这类会让实验白跑一整天的错误。

---

## V2 一键参考命令（脚本段）

> 推荐直接用统一入口 `python exp.py`（见 V4a），它把 V4 + V8 串起来并产出
> `COMPARE.md` / `COMPARE.html`。下面的脚本段用于需要精细控制时逐段执行。

```bash
cd benchmark-suite
python scripts/117_pipeline_selfcheck.py && \
python scripts/112_question_set.py --validate data/papers/qa_v2.json --strict-quota && \
python scripts/113_baselines.py --questions data/papers/qa_v2.json \
    --methods bm25,vector,rrf,rerank,crag,selfrag && \
python -m experiments.runner --questions data/papers/qa_v2.json --tracks a2,b,c && \
python scripts/114_pool_qrels.py --build --run <run_id> && \
#   → 人工/Agent 标注 qrels_pool.json（graded 0-3）
python scripts/114_pool_qrels.py --score --run <run_id> \
    --questions data/papers/qa_v2.json && \
python scripts/110_stratified_grade.py --run <run_id> \
    --qfile data/papers/qa_v2.json --judge && \
python scripts/115_stats.py --runs <5 个 run 目录> --metric correct --out stats.json && \
python scripts/116_experiment_report.py --run results/runs/<run_id>
```

> **V2 与 Stage 0–9 的关系**：Stage 0–9 是"工程可复现性"证据（语料怎么来、
> 怎么入库、怎么路由）；V2 是"机制有效性"证据（方法对不对、赢多少、显不显著）。
> 论文主表用 V2，工程附录引 Stage 0–9。两者**共用同一份语料与同一套脚本风格**。

---

## 真实执行护栏（红线 ⭐）

1. **禁止编造**：任何 JSON/MD 里的数字与回答必须来自真实工具调用输出；
   Agent 判断件必须基于脚本导出的证据文件，禁止凭空撰写。
2. **判断工件可追溯**：classification.json / skill_track_answers.json 必须能在
   ingest_survey.json / skill_track_evidence.json 中找到对应证据。
3. **产物只增不改**：results/ 下本轮产物不覆盖上一轮（带时间戳的目录），
   脚本级 JSON 允许被新一轮覆盖但 git 可追溯。
4. **失败即停**：任一 Stage 退出码非 0 停止流水线并报告，禁止带病继续。
5. **不挑轮次**：LLM 通道结果有方差，报告完整运行史，禁止重跑挑好结果。
6. **语言红线（2026-09-19）**：10 题与三轨全部回答一律英文；作答 prompt
   内置英文硬约束（BARE_PROMPT / SCEN_ANSWER_PROMPT），Track A 由执行
   agent 以英文撰写五段式回答。

## 故障速查（实测沉淀）

| 症状 | 根因 | 处置 |
|---|---|---|
| two_stage/检索答案错库 | 大批删建后 BM25 内存索引陈旧 | Stage 5b 重启后端 |
| kb_doc_read 按篇名为空 | save_parsed 会再补 `.md`（实际名 `xxx.md.md`） | 用 kb_get_documents 返回的真实名 |
| 按篇名打标签 404 | 大文档 create 时拆 part，整篇名不存在 | 对每个 part 打标（62 号已处理） |
| kb_doc_update_tags 挂死 30s | kb_id 传了中文名（web 层只认 UUID） | kb_list 取 UUID 传入 |
| catalog 瞬时为空 | web 鉴权 60s 负缓存毒化；lightweight 分支上游缺 success 标志时 MCP 原样透传（无 catalog 键） | 等 60s 重试；脚本做双形状回退（catalog → knowledgeBases/kbId，62 号已内置） |
| curl rc=63 | PDF 超 --max-filesize | 已放宽 60MB |
| arXiv API 406 | 3s/请求限流 + urllib 指纹 | 退避重试 + curl 传输（91 已内置） |
| two_stage 按库限定结果错库/整库被 Corpus-* 挤占 | 多代删建后 BM25 内存索引脏化 + 同文重复分块挤占配额（实测 3-7/10） | 回归与 Track A 一律用 `kb_search_vector`（skill Phase 1 规定工具，实测 9-10/10）；two_stage 仅限未建 Corpus-* 时的整库查询 |
