# 实验流程审计与重构方案

> 审计日期：2026-09-24 · 审计对象：`benchmark-suite/PIPELINE.md` + `experiments/*` +
> `scripts/107_exp_grade.py` + `results/R2-EXP-3TRACK-REPORT.md` + `results/ANALYSIS-20260923.md` +
> `results/r2_pipeline_100.json` + `results/honest_failure_probe.json`
> 一句话结论：**工程可信性是 A 级，统计证据力是 C 级。现在这套数字能证明"平台比裸 Agent 强"，
> 但不能证明"你的核心机制有效"——而论文要的是后者。**

---

## 0 · 先说做对了什么（这些不要动）

| 优点 | 位置 | 为什么值得保留 |
|---|---|---|
| **证据底线** `require_evidence=True`：未执行成功检索则拒答 | `experiments/README.md:20-25` | 杜绝参数化记忆作弊，这条比多数 RAG 论文严格 |
| **同一 harness、同一对外端点、同一语料**，只改检索协议 | `chat_tracks.py:2-18` | 控制变量做得干净，三轨差异确实可归因于协议 |
| **全程真实执行 + 严禁编造 + 失败即停 + 不挑轮次** | `PIPELINE.md:264-276` | 内部效度的护栏，罕见的严谨 |
| **完整监控**：逐工具调用、wall-clock、token 四类、cost | `chat_tracks.py:179-197` | 效率分析的数据已经齐了，只是没画出来 |
| **诚实探针 + 负面结果照实发表** | `honest_failure_probe.json` | 独家的差异化素材 |
| **确定性判分（不经 LLM）** | `107_exp_grade.py:28-40` | 可复现，这点必须保留——作为**回归层** |

问题不在态度，在**因变量定义**和**实验结构**。

---

## 1 · P0 级缺陷（不修则数字不能作为论文证据）

### P0-1 · 因变量不是"答案正确"，是"关键词宾果"

**现象**：`pass = gold_hit ∧ kw_ok`（`scripts/107_exp_grade.py:76`）。

- `gold_hit` = 金标 arXiv id 是否出现在 `answer + tool_calls JSON + texts_full` 拼成的大 blob 里（`:66-69`）。
  → **B 轨只要 Grep 到文件路径就算命中**。这就是 B 轨 gold 10/10 的真实含义：它碰到了文件，不代表答对了。
  事实印证：`ANALYSIS-20260923.md:27` 自己写了"裸 Agent 靠 Grep 总能定位正确文件"。
- `kw_ok` = ≥60% 金标关键词按词边界命中（`:71` need = ceil(0.6n)）。
  → 词表里混着通用词：`["order","decision"]`、`["dynamic","multilayer perceptron"]`、`["sequence"]`、`["queries","knowledge base"]`。
  `decision` 这个词在任何 RL/MAT 相关答案里都会出现。
- 判分不含语义等价 → A 轨唯一失败 BQ02 是"答案正确定义了 NISQ 但没用 `error correction` 原词"（`ANALYSIS:29`）。
  **指标把正确答案判错了**，这本身就证明指标无效。

**审稿人会怎么说**：*"This measures keyword bingo, not answer correctness."* —— 一句话击穿。

**修法（三层评分，不要替换要叠加）**：

| 层 | 做什么 | 用途 |
|---|---|---|
| **L1 确定性层（保留）** | 现有 `107_exp_grade.py`，gold 可追溯 + 词边界 | 回归测试、可复现性证明 |
| **L2 Judge 层（新增）** | 固定 judge prompt + 固定外部模型 + `temperature=0`，输入 = 问题 + 金标要点 + 候选答案，**输出 0/1 正确性 + 0–5 质量分**；judge 必须与被测系统解耦（不能用自己的平台当 judge） | 主表因变量 |
| **L3 人工层（新增）** | 3 标注者 × 全部题目，报 **Cohen's κ / Krippendorff α**；再报 **LLM-vs-human 一致率** | 校准层，直接对标 CRAG Table 4 |

**L2/L3 的一致率本身是一张表**——这是把"0–8 rubric 是未校准仪器"这个最大质疑（REVIEW-TODO TODO-11）变成贡献的机会。

### P0-2 · 实验结构无法分离机制：没有析因，且 A 轨带了"外挂"

**现象**：A/B/C 三轨至少混淆了三个因子：

| 因子 | A | B | C |
|---|---|---|---|
| 语料组织 | 平台五门类库（内容路由，322 docs） | 扁平目录 100 文件 | 扁平 Chunks800 |
| 检索方式 | QDCVR 全流程 | Grep/Read | 纯向量 |
| 文件工具 | **有（Read/Grep/Glob）** | 有 | 无 |

`chat_tracks.py:84-90` 里 `A_TOOLS` 末尾就是 `+ ["Read", "Grep", "Glob"]`。

**后果**：A 赢 C，可能是内容裁决有效，可能是内容路由组织有效，也可能是"A 还能 grep 文件"。
**三个解释都成立，你的核心 claim（跨域干扰下内容裁决有效）一个都没被单独证明。**

**修法（2×2 析因 + 一个对照轨）**：

```
                 裁决 ON            裁决 OFF
组织 ON   [org+adj] A 现在这个   [org+noadj]  ← 需平台支持关闭 gate
组织 OFF  [flat+adj]            [flat+noadj]
```

- **交互项（organization × adjudication）就是论文那个 claim**。有交互 → 机制成立；无交互 → 只有主效应，claim 必须改写。
- 加 **A2 轨 = 平台工具但禁用 Read/Grep/Glob**，证伪"增益来自文件工具"这一替代解释。
- 工程量前置条件：**平台需要提供一个关闭内容裁决的开关**（`?adjudicate=false` 或等效参数），
  否则 `[org+noadj]` 与 `[flat+noadj]` 两格跑不出来。这是要先做的需求。

### P0-3 · 没有真实 baseline，只有"弱化版自己"

**现象**：B 是被砍掉工具的 agent，C 是只给向量的 agent。两者都不是已发表方法。
`DATASETS-AND-EXPERIMENTS.md:76-77` 自己规划了 8 个 baseline，**一个都没跑**。

**修法**：至少跑这 6 个，且**全部架在同一个检索后端上**（同一个 Chroma 索引 + 同一个 BM25 索引），只换"召回→裁决"这一段：

| # | Baseline | 必备程度 |
|:--:|---|:--:|
| 1 | BM25 only | 必 |
| 2 | BGE-M3 向量 top-k | 必 |
| 3 | BM25 + 向量融合（RRF） | 必 |
| 4 | 向量 + Cross-Encoder rerank（bge-reranker-v2-m3） | **必**（最强的朴素对手） |
| 5 | **CRAG 式**：检索评估器三分类 + 纠正动作 | **必**（审稿人必查） |
| 6 | **Self-RAG 式**：LLM 自评 reflection + 按需检索 | **必**（审稿人必查） |

只有打赢第 4 项，你的"读正文裁决"才比"黑箱 reranker"有价值；只有打赢 5/6，才能说清与 CRAG/Self-RAG 的边界。

### P0-4 · 题集与主张不匹配，且规模不足以做统计

**现象（逐条核对过）**：

- **n = 10**（`qa_questions.json`，且 `meta` 字段是空 `{}`——无出处、无版本、无标注者，溯源断链）。
  一题翻转 = 10 个百分点；无法做显著性检验；没有 power。
- **全部是单跳、单文档、有答案的事实题**（BQ01–BQ10 逐条核过）。
  无多跳、无跨库对比、无干扰对抗、**无"应拒答"**。
- **措辞泄漏**：`qa_questions_r2.json` 的 meta 自述"基于 `r2_survey.json` 三窗口真实正文…
  gold_keywords 全部在论文正文中逐字出现"。出题者看了正文 → 题干措辞与语料措辞同源 →
  对 BM25/向量天然友好，且对"平台库"（其描述与标签也是同一批内容生成的）双重友好。
  `DATASETS-AND-EXPERIMENTS.md:108` 自己写了"禁止用 LLM 批量造题（审稿人会问 leakage）"——**当前题集正是这么造的**。

**修法（重建题集，六层分层）**：

| 层 | 题数 | 说明 | 支撑的指标 |
|---|:--:|---|---|
| 单跳事实 | 20 | 基线难度 | P@k、正确率 |
| 多跳（跨 2–4 篇） | 15 | 压测两阶段召回 | Recall@10、nDCG@10 |
| 跨库对比 | 10 | 测 KB 路由 + balance_kbs | 跨库熵、nDCG |
| **干扰对抗** | 15 | 同域近义不同实体（"battery thermal management" vs "data center thermal management"） | **FPR、这是核心机制的命脉** |
| **应拒答（库内无解）** | 12 | 库里有相似文档但答不了 | **not-found 正确率 + 误拒率** |
| 域外 | 8 | 完全不在语料 | not-found 正确率 |
| **合计** | **80** | | |

出题规程（防泄漏）：
1. 出题者**只看标题 + 摘要首句**，禁看正文；
2. `gold_keywords` 改为**答案要点 rubric**（3–5 条语义要点），不是逐字关键词；
3. 3 名人类各改写/复核 1/3，记录改写率；
4. 冻结后公开（Zenodo DOI）+ 写 Datasheets for Datasets。

### P0-5 · 无 qrels → 一个 IR 指标都算不出来

**现象**：每题只有 1 个金标文档。没有"部分相关"标注，没有候选池。
所以 **P@k / Recall@k / nDCG@k / MRR 全部无法计算**——而论文主表必须有这些。

**修法（池化标注）**：
1. 把所有 baseline + 平台的 **top-10 结果取并集**作为每题的标注池；
2. 3 标注者对池内文档打 **graded relevance 0/1/2/3**；
3. 未标注的默认 0（标准 TREC 假设）；
4. 报 κ / α。
这样 nDCG@10 对所有方法公平，且一次标注可复用给所有配置。

---

## 2 · P1 级缺陷

### P1-6 · 单轮运行，无方差与显著性（REVIEW-TODO TODO-7 / TODO-20）
每配置 **≥5 次**（LLM 通道），报 mean ± SD；逐题配对 → **Wilcoxon signed-rank**（n=80 时比 t 检验更稳，或用 paired t 但先查正态）；
Holm 多重比较校正；报 effect size 与 95% CI；正文写 power statement。

### P1-7 · 无消融（且历史消融与主表协议差 4–7×，TODO-9）
在同一题集、同一 qrels 上做 leave-one-out：
`−内容裁决` / `−KB 选择（全库盲搜）` / `−balance_kbs` / `−查询改写` / `−馆员兜底` / `−短块守卫`。
**消融必须与主表同 query set、同 qrels、同指标**——这是 TODO-9 的直接修法。

### P1-8 · 0–8 rubric 无人工一致性（TODO-11）
见 P0-1 的 L3 层。这是"最可能被拒"的单点，也是最容易变成贡献的一项。

### P1-9 · 效率只有一个均值，而 A 是 3× 成本 / 2.6× 时延
`ANALYSIS:26` 自己承认。现在这个数字是**负资产**。
修法：画 **quality–latency** 与 **quality–cost** 权衡曲线（Adaptive-RAG Fig.5 是范本），
并单独报"内容裁决的边际开销"：裁决 ON/OFF 的 Δ 时延、Δ 成本、Δ 质量。
把"贵 3 倍"改写成"每多花 1 美元买到多少正确率"——从负债变资产。

### P1-10 · 结果可覆盖、无 run id（TODO-10）
强制 `results/runs/<utc-ts>-<git-sha>/`，每个结果文件内嵌 git commit、config hash、seed、
**BGE-M3 HF revision**、**Chroma HNSW 参数（M / ef_construction / ef_search）**（TODO-8）。
`provenance_audit.py` 接进 CI（TODO-21）。

### P1-11 · 诚实探针只有 3 条，且自检自评
`honest_failure_probe.json` 的 `judgment` 字段自述 *"recorded protocol traces, not independent evaluations"*。
3 条撑不起"零编造"主张，且**只报了正确拒答，没报误拒**（TODO-2 要求两个方向都报）。
修法：并入主实验的"应拒答"层（12 条），用同一个外部 judge，报 **not-found 正确率 + 误拒率** 两个方向。

---

## 3 · P2 级（便宜但要修）

### P2-12 · 公平性缺陷：三轨输出长度约束不一致 ⚠️ 最便宜的一条

| 轨 | 输出约束 | 位置 |
|---|---|---|
| A | 无长度限制（可写五段式长答案） | `chat_tracks.py:42` |
| B | **"Answer in ENGLISH (2-6 sentences)"** | `chat_tracks.py:49` |
| C | **"Answer in ENGLISH (2-6 sentences)"** | `chat_tracks.py:64` |

`kw_hit` 对长答案天然有利 → **系统性偏袒 A 轨**。B/C 被人为限制在 2–6 句，还要跟 A 的长答案比关键词覆盖率。
**修法**：给 B/C 同样的表达自由度（把上限放宽到"最多 8 句、可列来源"），或改用不受长度影响的 judge 评分。
（已在本轮直接改掉，见 §5。）

### P2-13 · chunks 口径打架
`ANALYSIS:10` 报 `Corpus-Chunks800` 重建工件 = 4,528 chunks，而 live `/api/v1/search/stats` = 37,567。
论文里必须写明**哪一个是检索口径**，否则复现者会建出不一样的库。

### P2-14 · `qa_questions.json` 的 meta 为空
无 `designed_by` / 无版本 / 无标注者，与 `qa_questions_r2.json`（有完整 meta）不一致。溯源链断了一环。

---

## 4 · 重构后的实验总设计

```
语料（不变）  100 篇 arXiv / 26 领域 / 322 docs
                    │
        ┌───────────┴────────────┐
   组织 ON：五门类库        组织 OFF：单一扁平库（同 100 篇）
        │                        │
   ┌────┴────┐              ┌────┴────┐
 裁决 ON   裁决 OFF       裁决 ON   裁决 OFF      ← 2×2 析因（核心）
   │          │              │          │
   └── 6 个 baseline 在同一后端上对齐 ──┘
   └── A2 轨（禁用文件工具）证伪替代解释 ──┘
   └── 6 项消融（leave-one-out）──┘
        │
   80 题六层分层 × qrels graded 0–3 × 5 次运行
        │
   指标：P@5 · R@10 · nDCG@10 · MRR · FPR · not-found 正确率 · 误拒率
        答案正确率(judge) · κ(人工) · LLM-vs-human · 时延 · 成本
```

### 与论文表格的映射

| 表 | 内容 | 来源 |
|---|---|---|
| Table 1 | 数据集统计（题数/类型/文档数/KB 数/平均 token） | 题集 + 语料 |
| Table 2 | **主表**：8 方法 × P@5/R@10/nDCG@10/FPR/正确率 | 2×2 析因 + baseline |
| Table 3 | **交互项表**：organization × adjudication 的 2×2 与交互效应 | 析因 |
| Table 4 | **裁决器评测**：0–8 rubric 作分类器 vs ChatGPT zero-shot vs 人类（含 κ） | L2/L3 |
| Table 5 | 消融表（同协议同 qrels） | leave-one-out |
| Table 6 | 经验模块（含 no-synthesis / LLM-summary 两个 baseline） | 见 §6 |
| Fig | quality–latency / quality–cost 权衡曲线 | 监控数据 |
| Fig | 散点：向量分 vs 内容分（展示 content-overrides-vector 的实际发生频次） | 裁决日志 |

> **最后一张图是现在唯一缺、但最能一击说服人的**：把每次裁决的 `(s, c)` 打成散点，
> 标出"高 s 低 c 被丢弃"的样本占比。这就是论文中心论点的实证形态。

---

## 5 · 本轮已落地的改动

1. `experiments/chat_tracks.py`：三轨输出契约统一（取消 B/C 的 2–6 句上限），并新增
   **`a2` 轨** = 平台工具但禁用 `Read/Grep/Glob`，用于证伪"增益来自文件工具"。
   新增 `PROMPT_VERSION = "v2-fair"`，旧 run 保持 v1 可回溯。
2. `scripts/110_stratified_grade.py`：分层评分器——
   L1 确定性层（兼容旧口径）+ **分层指标**（按题目类型分桶报数）+ L2 judge 层（外部模型，env 可配）+ 一致性统计。

---

## 6 · 经验模块（E0–E12）当前不能作为贡献，差什么

REVIEW-TODO TODO-4/5/6 指出：五路召回无 leave-one-out、重跑不稳定、无 baseline。
补三个东西即可从"设计描述"升级为"贡献"：

1. **no-synthesis baseline**：同一批运维查询，直接检索原始文档、不建经验层；
2. **LLM-summary baseline**：把同一批文档一次性总结成"经验"再用；
   两者用**同一个 judge prompt** 打分，才是 like-for-like；
3. 五路召回的 **leave-one-out 消融**（vector / keyword / scenario / tag / quality-feedback 各去掉一路）+ 各单路单独跑。

---

## 7 · 执行顺序（按"证据价值 ÷ 工作量"排序）

| 序 | 任务 | 工作量 | 解锁什么 |
|:--:|---|:--:|---|
| 1 | 修输出契约公平性 | **1 h** | 消除系统性偏袒，立即生效 |
| 2 | 平台加"关闭裁决"开关 | 1–2 d | 解锁 2×2 析因的两格 |
| 3 | 题集重建（80 题六层，人工防泄漏） | 2–3 周（人力为主） | 解锁 FPR、not-found、统计功效 |
| 4 | qrels 池化标注（graded 0–3） | 与 3 并行 | 解锁 nDCG@10 / Recall@k |
| 5 | L2 judge 层 + L3 人工 κ | 1 周 | 解锁"答案正确性"+ 校准仪器 |
| 6 | 6 个 baseline 复现 | 1 周 | 解锁主表可比性 |
| 7 | 5 次重复 + 显著性 + CI | 脚本化后自动 | 解锁显著性声明 |
| 8 | 消融（同协议同 qrels） | 3 d | 归因到具体 stage |
| 9 | 效率权衡曲线 + 裁决边际开销 | 1 d | 把 3× 成本从负债变资产 |
| 10 | run id 化 + provenance 进 CI | 1 d | 可复现性 |

**最小可行版（若只剩 6 周）**：题集缩到 **40 题**（六层等比缩放）、baseline 保留 **1/2/4/5 四个**、
重复 **3 次**、去 CIKM **Applied Research** track 并在摘要/C1 把声明限定在自建语料。

**不要在数字没补齐前冲 Full Research**——REVIEW-TODO 的 5 个 🔴 里有 4 个是实验问题，不是写作问题。
