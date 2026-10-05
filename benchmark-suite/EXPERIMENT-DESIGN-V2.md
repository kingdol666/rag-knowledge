# 实验设计 V2 —— 从「能证明平台比裸 Agent 强」到「能证明核心机制有效」

> 撰写日期：2026-09-24 · 对象：`benchmark-suite/PIPELINE.md` + `experiments/*` + `scripts/107_exp_grade.py` +
> `results/R2-EXP-3TRACK-REPORT.md` + `results/ANALYSIS-20260923.md` + `docs/paper/cikm/*`
> 本文在 `EXPERIMENT-REDESIGN.md`（同日审计）基础上：**逐条回源码复核**其结论，并补上它**未覆盖的一类致命缺陷——环境与变量控制**。
> 一句话结论：**当前这套数字既不能证明"平台比裸 Agent 强"，更不能证明"你的核心机制有效"；后者需要一个 2×2 析因设计，而当前设计连这个析因都跑不出来。**

---

## 0 · 结论摘要

| 维度 | 现状评级 | 一句话诊断 |
|---|:--:|---|
| 工程可信性（真实执行 / 不编造 / 可追溯） | **A** | 护栏罕见地严谨，**不要动** |
| 测试用例覆盖度 | **D** | n=10、全单跳单文档、无应拒答、无对抗干扰、措辞泄漏 |
| 评估指标充分性 | **D** | 因变量是"关键词宾果"，非答案正确性；无 qrels → 一个 IR 指标都算不出 |
| 对照组科学性 | **D** | 没有真实 baseline，只有"被砍掉工具的自己"；且**被测系统带文件工具外挂** |
| **环境与变量控制** | **F（新发现）** | **被测系统（A 轨）的 cwd = 仓库根目录，可直接读到答案键与历史 run 的逐字答案** |

**三个必须立刻做的事（按优先级）**：

1. **隔离答案键 + 预算对齐**（1–2 天，纯工程，不改任何结论方向）—— 否则 A 轨的 9/10 有作弊嫌疑，审稿人一句话击穿。
2. **平台加"关闭内容裁决"开关 → 跑 2×2 析因**（1–2 天）—— 交互项就是你论文的中心 claim。
3. **题集重建（80 题六层）+ 外部 judge + 池化 qrels**（2–3 周，人力为主）—— 解锁 FPR / not-found / 显著性 / nDCG。

> 在 1–3 完成前，**不要**把当前 9/10 vs 6/10 vs 5/10 当作论文主表证据。它可以作为"工程可复现性"的辅证，但不能作为"机制有效"的主证。

---

## 1 · 本次逐条复核（file:line 证据锚点）

### 1.1 复核确认的缺陷（与 EXPERIMENT-REDESIGN.md 一致）

| # | 缺陷 | 证据锚点（本次实读） | 状态 |
|:--:|---|---|:--:|
| P0-1 | 因变量 = 关键词宾果 | `scripts/107_exp_grade.py:66-76`：`blob = answer + tool_calls + texts_full`，`pass = gold_hit ∧ kw_ok`；`need = ceil(0.6n)` | ✅ 确认 |
| P0-1b | B 轨 gold 10/10 是假象 | 同上：`gold_hit` 扫的是**工具调用轨迹**，B 轨 Grep 到文件路径即命中 | ✅ 确认 |
| P0-2 | 无析因 + A 轨带外挂 | `experiments/chat_tracks.py:103-108`：`A_TOOLS = _kb_read_tools(...) + ["Read","Grep","Glob"]` | ✅ 确认 |
| P0-3 | 无真实 baseline | 只有 B（砍工具的 agent）/ C（只给向量的 agent），无 CRAG / Self-RAG / CE-rerank | ✅ 确认 |
| P0-4 | 题集与主张不匹配 | `data/papers/qa_questions.json`：10 题、`meta` 为空、全单跳；`qa_questions_r2.json` meta 自述"gold_keywords 全部在正文逐字出现" | ✅ 确认 |
| P0-5 | 无 qrels | 每题仅 1 个 `arxiv_id`，无 graded relevance、无候选池 | ✅ 确认 |
| P1-9 | 效率是负资产 | `R2-EXP-3TRACK-REPORT.md`：A $0.4911/题 · 113.0s vs B $0.1631 · 42.7s | ✅ 确认 |

### 1.2 本次新增发现（EXPERIMENT-REDESIGN.md 未覆盖）⭐

> 这一类缺陷比统计问题更致命：它们属于**内部效度**——即使把统计做得再漂亮，结论也不能归因于机制。

#### F1 🔴 答案键泄漏：被测系统可读答案（环境控制）

- **事实**：`chat_tracks.py:118` A 轨 `"cwd": str(REPO)`（仓库根）；`A_TOOLS`（:103-108）含 `Read/Grep/Glob`。
- **泄漏面**（均在 repo 内、可被 A 轨读取）：
  - `benchmark-suite/data/papers/qa_questions.json` —— **金标 arXiv id + gold_keywords 原文**；
  - `benchmark-suite/data/papers/qa_questions_r2.json` —— 同上；
  - `benchmark-suite/results/experiment_chat_*/SUMMARY.md` —— **历次 run 的逐字答案**（同 10 题）；
  - `benchmark-suite/results/exp_r2_grade.json` —— 逐题判分。
- **为什么致命**：treatment arm（被测系统）拥有对 ground truth 的读权限。审稿人无需证明它读了，只要指出**设计允许它读**，A 轨的 9/10 就不可采信。
- **修法**：A 轨 cwd 改到**隔离工作目录**（仅含语料/工具可及范围），答案键与 results 移出该目录；或**彻底移除 A 轨的 `Read/Grep/Glob`**（即把现在的 `a2` 轨扶正为唯一 A 轨，见 3.4）。

#### F2 🔴 计算预算混淆（treatment 与其成本未解耦）

- **事实**：A 轨 3× 成本 / 2.6× 时延 / 约 5× input tokens（`ANALYSIS-20260923.md:21-23`）。
- **为什么致命**：QDCVR 的"内容裁决"= 多轮检索 + 读正文 + LLM 打分，**本身就是额外算力**。当前设计无法区分"裁决机制有效"与"多花 3 倍算力有效"。一个朴素方法给同等预算（多次检索 / 多轮自检）可能追平差距。
- **修法**（新增强制项）：**预算匹配臂**——把所有对照轨的 maxTurns / token 预算 / 墙钟上限对齐到同一水平；主表同时报告"等预算"与"等协议"两栏。

#### F3 🟠 提示词框架混淆（不止工具集不同）

- **事实**：`chat_tracks.py:57-85` 三轨 prompt 角色框架不同——A 是命令式（"Execute the retrieval yourself… do NOT delegate"），B 是人格式（"You are a BARE research agent"），C 是管线式（"You are a DENSE-RAG pipeline"）。文件头注释声称 "Only the retrieval protocol differs"，**不成立**。
- **修法**：统一为一个中性模板，只留一个"可用工具/检索接口"插槽；`PROMPT_VERSION` 升 `v3-neutral`。

#### F4 🟠 检索单元混淆（"同一语料"只在文档层成立）

- **事实**：A 检索**门类库 part 级文档**（322 docs，单 part ≤28500 字符）；B 读**整篇文件**（100 个 .md）；C 检索**固定 800 字符 chunk**（4528 chunks）。三者的**检索粒度不同**。
- **后果**：A vs C 同时差异于 路由 + 裁决 + 分块，三个因子纠缠。
- **修法**：把分块作为一个**显式因子**（或让平台索引也建在 Chunks800 之上做匹配对照）。

#### F5 🟠 同模型自评（仪器效度）

- **事实**：A 轨 0–8 内容裁决由 LLM 执行；`results/honest_failure_probe.json:6` 自述 "recorded protocol traces, **not independent evaluations**"；Stage 9 分析件同为执行 Agent。
- **修法**：外部、版本锁定的 judge（`110_stratified_grade.py` 已实现 `JUDGE_ENDPOINT` 且拒绝用被测平台当 judge）+ 3 人人工 κ。

#### F6 🟡 抽样与顺序未控

- **事实**：`chat_tracks.py:146-150` payload 无 `temperature`/`seed`；`runner.py:102-106` 固定按 a→b→c 顺序、每题串行；`runner.py:41-66` 失败时**自愈重启 web 并重试一次**（非均匀环境）。
- **修法**：固定温度/种子（harness 允许时）；**逐题随机化轨序**；计分 run 期间关闭自愈（或把重启记为协变量）。

#### F7 🟡 README 与已提交报告数字不一致

- **事实**：`README.md:487` 称 A "**10/10** on-target · top-1 gold recall 10/10"；而 `results/R2-EXP-3TRACK-REPORT.md:9` 记 A **9/10**。前者来自旧的 50 篇轮次，口径未统一（项目记忆 `2026-09-24` 已自认此点）。
- **修法**：一个 run → 一个数字；README 数字由冻结 run 自动重生成。

#### F8 🟡 忠实性/引用正确性未测

- **事实**：`r2_pipeline_100.json` 只统计 `citations` **条数**（a:7 / b:4 / c:1），**不判对错**。而系统中心卖点正是"provenance down to part and section"。
- **修法**：新增 attribution/faithfulness 指标（引用来源是否真的支撑该句）。

---

## 2 · 四个维度的诊断（用户指定的分析框架）

### 2.1 测试用例的覆盖度与合理性 —— **不充分（D）**

| 问题 | 证据 | 后果 |
|---|---|---|
| 规模 n=10 | `qa_questions.json` 共 10 题 | 一题翻转 = 10pp；无统计功效 |
| 全单跳单文档 | BQ01–BQ10 逐条核过，gold 均单一 `arxiv_id` | 测不出两阶段召回、跨库路由 |
| 无"应拒答"层 | 主 run 无 unanswerable/out-of-corpus 题 | not-found 契约只在 3 条自评探针里测过 |
| 无对抗干扰层 | 无同域近义不同实体题 | **中心 claim（跨域干扰下裁决有效）无 ground truth** |
| 措辞泄漏 | `qa_questions_r2.json:4` meta 自述 | 题干与语料同源 → 对 BM25/向量天然友好，对平台库双重友好 |
| 溯源断链 | `qa_questions.json` 无 `meta` | 无出题人 / 版本 / 标注者 |

### 2.2 评估指标的选择是否充分 —— **不充分（D）**

- **主因变量错位**：`pass` 测的是"金标 id 出现 ∧ ≥60% 关键词出现"，且 `gold_hit` 扫工具轨迹 → B 轨"碰到文件"即得分。这是 keyword bingo，不是 answer correctness。
- **指标把正确答案判错**：A 轨唯一失败 BQ02 是"答案正确定义 NISQ 但未用 `error correction` 原词"（`ANALYSIS-20260923.md:29`）——指标自身反例。
- **IR 指标全缺**：无 qrels → P@k / R@k / nDCG@k / MRR 均不可算。
- **缺诚实性双向指标**：只可能报"拒答正确率"，**不报误拒率**——只报前者等价于"永远拒答"。
- **缺忠实性指标**：引用只计条数，不判对错（F8）。
- **缺效率-质量权衡**：只有单点均值（F2）。

### 2.3 对照组设置是否科学 —— **不科学（D）**

- **没有真实 baseline**：B/C 都是"被削弱的自己"，不是已发表方法；`DATASETS-AND-EXPERIMENTS.md:76-77` 自己规划了 8 个 baseline，**一个都没跑**。
- **对照组退化**：C = top_k 10 / threshold 0 / 单轮 / 无 rerank 的**稻草人**稠密 RAG。
- **被测组带外挂**：A 含 `Read/Grep/Glob`（P0-2）→ "A 赢"有三种等价解释。
- **无 oracle / 上界**：不知道天花板在哪。
- **无预算匹配对照**（F2）。

### 2.4 测试环境与变量控制是否严谨 —— **不严谨（F，本次新发现）**

| 控制项 | 现状 | 风险 |
|---|:--:|---|
| 答案键隔离 | ❌ **A 轨可读答案键与历史答案**（F1） | 内部效度致命 |
| 计算预算对齐 | ❌ 3× 成本差（F2） | treatment 与算力混淆 |
| 提示词框架恒定 | ❌ 三轨角色不同（F3） | 框架效应混淆 |
| 检索单元匹配 | ❌ part / 整篇 / 800chunk（F4） | 分块效应混淆 |
| judge 与被测解耦 | ❌ 同模型自评（F5） | 仪器效度 |
| 温度 / 种子 | ❌ 未设（F6） | 不可复现 |
| 运行顺序 | ❌ 固定 a→b→c（F6） | 顺序/缓存效应 |
| 自愈重启 | ⚠️ 计分期间可能重启 web（F6） | 非均匀环境 |
| 索引新鲜度 | ⚠️ 依赖人工 Stage 5b 重启（PIPELINE:159-165） | BM25 陈旧 → 结果不可信 |
| 版本 provenance | ❌ 无 git sha / config hash / BGE-M3 revision / HNSW 参数 | 不可复现 |
| 唯一 run id | ⚠️ 有 `experiment_chat_<ts>/`，但脚本级 JSON 原地覆盖 | TODO-10 未闭环 |

---

## 3 · 优化后的最佳实验设计方案

### 3.0 从 claim 到可证伪假设

论文的中心 claim 是：**"在跨域干扰下，内容裁决（content adjudication）能降低假阳性、提升答案正确性；且它与内容路由组织是互补的（两者单独都不够）。"**

拆成三个可证伪假设：

- **H1（主效应）**：`裁决 ON > 裁决 OFF`，在**对抗干扰层**上 FPR 显著下降、正确率显著上升。
- **H2（交互项）**：`组织 × 裁决` 的**交互效应显著**——即裁决的收益在"组织 ON"与"组织 OFF"下不同。**交互项就是 claim 本身。**
- **H3（归因）**：收益不能由①文件工具、②额外算力、③更大分块解释。→ 需要 A2 轨 + 预算匹配臂 + 分块匹配。

### 3.1 总体结构

```
语料（100 篇 arXiv / 26 领域 / 322 docs；可选加 FlashRAG 公开集）
                    │
   ┌────────────────┴─────────────────┐
   组织 ON：五门类库            组织 OFF：单一扁平库（同 100 篇）
   │                                  │
 ┌─┴─┐                            ┌─┴─┐
裁决ON  裁决OFF                   裁决ON  裁决OFF     ← 2×2 析因（核心，需平台开关）
 └─┬─┘   └─┬─┘                    └─┬─┘   └─┬─┘
   └───────┴── 8 个 baseline 架在同一检索后端（同 Chroma + 同 BM25）────────┘
   └── A2 轨（平台工具、禁 Read/Grep/Glob）── 证伪"增益来自文件工具"
   └── 预算匹配臂（token/turn 对齐）────────── 证伪"增益来自算力"
   └── 6 项 leave-one-out 消融 ────────────── 归因到具体 stage
                    │
   80 题六层分层 × 池化 graded qrels(0-3) × 5 次运行 × 随机化轨序
                    │
   指标：P@5 · R@10 · nDCG@10 · MRR · FPR · not-found 正确率 · 误拒率
        答案正确率(外部judge) · 忠实性 · κ(人工) · LLM-vs-human
        时延(median+IQR) · 成本 · **等预算质量**
```

### 3.2 语料与检索单元

- **主轨（自建领域轨）**：维持 100 篇 / 322 docs，但**必须把"检索单元"作为显式因子**：
  - 组织 ON = 五门类库（part 级）；
  - 组织 OFF = 单一扁平库；
  - **分块匹配对照** = 平台索引也建在 `Corpus-Chunks800` 之上 → 使 A vs C 只在"裁决"上不同。
- **公开可比轨（强烈建议，解决 TODO-12）**：按 `DATASETS-AND-EXPERIMENTS.md:48-51` 的路线——
  取 FlashRAG 版 **HotpotQA / 2WikiMultiHopQA / MuSiQue / PopQA**，把 Wikipedia 语料按主题聚成 **8–12 个 KB**，
  golden docs 分布在 1–4 个 KB。**这是唯一能证明"跨域干扰"claim 不依赖自建语料的路径**。

### 3.3 题集（重建为 80 题六层）

| 层 | 题数 | 支撑指标 |
|---|:--:|---|
| 单跳事实 | 20 | P@5 / 正确率 |
| 多跳（跨 2–4 篇） | 15 | R@10 / nDCG@10 |
| 跨库对比 | 10 | 跨库熵 / nDCG |
| **干扰对抗**（同域近义不同实体） | 15 | **FPR（核心机制的命脉）** |
| **应拒答**（库内有相似文档但答不了） | 12 | not-found 正确率 + **误拒率** |
| 域外（完全不在语料） | 8 | not-found 正确率 |
| **合计** | **80** | |

**防泄漏规程**：① 出题者只看标题 + 摘要首句，禁看正文；② `gold_keywords` 改为**答案要点 rubric（3–5 条语义要点）**，不再要求逐字；③ 3 名人类各改写/复核 1/3，记录改写率；④ 冻结后公开（Zenodo DOI）+ 写 Datasheets for Datasets。

### 3.4 对照组（8 baseline + 2 证伪臂，全部架在同一检索后端）

| # | 对照 | 必备度 | 作用 |
|:--:|---|:--:|---|
| 1 | BM25 only | 必 | 稀疏基线 |
| 2 | BGE-M3 向量 top-k | 必 | 稠密基线 |
| 3 | BM25 + 向量 RRF | 必 | 混合基线 |
| 4 | 向量 + Cross-Encoder rerank（bge-reranker-v2-m3） | **必** | **最强的朴素对手** |
| 5 | CRAG 式（检索评估器三分类 + 纠正动作） | **必** | 审稿人必查 |
| 6 | Self-RAG 式（LLM 自评 reflection + 按需检索） | **必** | 审稿人必查 |
| 7 | 平台（QDCVR 全流程） | — | 被测 |
| 8 | 平台 − 裁决（需开关） | — | 主效应 |
| **A2** | 平台工具、**禁 Read/Grep/Glob** | **必** | 证伪"文件工具"解释 |
| **BUD** | 任一强 baseline **等预算**（对齐 token/turn） | **必** | 证伪"算力"解释 |

> 只有打赢 #4，"读正文裁决"才比"黑箱 reranker"有价值；只有打赢 #5/#6，才能说清与 CRAG/Self-RAG 的边界。

### 3.5 指标矩阵

| 类别 | 指标 | 定义要点 |
|---|---|---|
| **主（正确性）** | judge correctness（0/1）+ quality(0–5) | 外部模型、`temperature=0`、版本锁定、与被测解耦 |
| **检索** | P@5 · R@10 · nDCG@10 · MRR | 需**池化 graded qrels(0–3)**：所有方法 top-10 并集为标注池，未标注默认 0（TREC 假设） |
| **鲁棒性** | FPR（对抗层） | 必须**coverage-aware**：同时报"返回零文档的题目占比"，否则弃答天然 FPR=0 |
| **诚实性（双向）** | not-found 正确率（应拒答层）**+ 误拒率（可答层）** | 两个方向必须同时报 |
| **忠实性** | 引用支撑率 / attribution | 引用的来源是否真的支撑该句（F8） |
| **效率** | 时延 median+IQR · 成本 · **等预算质量** | 画 quality–latency / quality–cost 曲线（Adaptive-RAG Fig.5 范本） |
| **校准** | Cohen's κ / Krippendorff α · LLM-vs-human | 3 标注者 × ≥40 题 |

### 3.6 环境与变量控制协议（本轮新增，解决 F1–F7）

| 控制项 | 强制做法 |
|---|---|
| **答案键隔离** | 计分 run 的 cwd 必须**不含**答案键 / 历史 run / 判分文件；或 A 轨移除 `Read/Grep/Glob` |
| **预算对齐** | 所有轨统一 `maxTurns` + token 上限；主表同时给"等协议"与"等预算"两栏 |
| **提示词恒定** | 单一中性模板 + 工具插槽；`PROMPT_VERSION="v3-neutral"` |
| **检索单元匹配** | 分块作为显式因子（见 3.2） |
| **judge 解耦** | 外部端点 + 锁定 model/revision/prompt/decoding；`110_stratified_grade.py` 已有硬约束 |
| **温度/种子** | harness 允许则固定；不允许则在报告显式声明"不可控" |
| **顺序随机化** | 逐题随机化轨序；记录实际顺序 |
| **自愈禁用** | 计分 run 期间禁用 `runner.py` 的 web 重启；重启记为协变量 |
| **索引新鲜度** | 计分前强制 `ragctl restart backend`（BM25 陈旧，PIPELINE:159-165），并验证 collection/chunks |
| **provenance** | 每个结果文件内嵌 git sha · config hash · seed · BGE-M3 HF revision · HNSW(M/ef_construction/ef_search) · chunk 总数 |
| **run id** | 强制 `results/runs/<utc-ts>-<git-sha>/`，**不可原地覆盖**；`provenance_audit.py` 进 CI |

### 3.7 统计规程

- 每个随机通道配置 **≥5 次**运行，报 mean ± SD；时延报 median + IQR。
- 逐题配对 → **Wilcoxon signed-rank**（n=80 时比 t 更稳；若用配对 t 先查正态）。
- **Holm 多重比较校正**（4 个 baseline × 多指标）。
- 报 **effect size + 95% CI**；正文写 **power statement**（给 n 与最小可检测效应）。
- **一个数字一个来源**：正文数字由冻结 run 重生成，禁止手写（对应 C2/C4）。

### 3.8 执行顺序（按"证据价值 ÷ 工作量"排序）

| 序 | 任务 | 工作量 | 解锁 |
|:--:|---|:--:|---|
| 1 | **隔离答案键 + 预算对齐 + 提示词恒定**（F1/F2/F3） | **1–2 d** | 内部效度，立即生效 |
| 2 | 平台加"关闭裁决"开关 | 1–2 d | 解锁 2×2 的两格 |
| 3 | 题集重建（80 题六层，人工防泄漏） | 2–3 周（人力） | FPR / not-found / 功效 |
| 4 | 池化 graded qrels(0–3) | 与 3 并行 | nDCG@10 / R@k |
| 5 | L2 judge + L3 人工 κ | 1 周 | 答案正确性 + 校准仪器 |
| 6 | 6 个 baseline 复现（同后端） | 1 周 | 主表可比性 |
| 7 | 5 次重复 + 显著性 + CI | 脚本化后自动 | 显著性声明 |
| 8 | 消融（同协议同 qrels） | 3 d | 归因到 stage |
| 9 | 效率权衡曲线 + 裁决边际开销 | 1 d | 把 3× 成本从负债变资产 |
| 10 | run id 化 + provenance 进 CI | 1 d | 可复现性 |

### 3.9 效度威胁（报告必写）与不可证部分

- **作者自评偏置**（最强威胁）：题集、语料、判分、分析全部由作者完成 → 必须靠"外部 judge + 人工 κ + 公开 artifact"部分抵消。
- **单 harness / 单模型**：结论不能外推到其他 LLM。
- **长期模块不可测**：经验模块 E0–E12 的 30 天时效衰减在当前观测窗口内**无法验证**，应显式声明。
- **自建语料边界**：若公开多域轨（3.2）未完成，claim 必须在摘要/C1 **限定在自建语料**。

---

## 4 · 与论文表格的映射

| 表/图 | 内容 | 来源 |
|---|---|---|
| Table 1 | 数据集统计（题数/类型/文档数/KB 数/平均 token） | 题集 + 语料 |
| **Table 2** | **主表**：8 方法 × P@5/R@10/nDCG@10/FPR/正确率 | 2×2 析因 + baseline |
| **Table 3** | **交互项表**：organization × adjudication 2×2 与交互效应 | 析因（= claim） |
| Table 4 | **裁决器评测**：0–8 rubric 作分类器 vs ChatGPT zero-shot vs 人类（含 κ） | L2/L3 |
| Table 5 | 消融表（同协议同 qrels） | leave-one-out |
| Table 6 | 经验模块（no-synthesis / LLM-summary 两个 baseline） | TODO-6 |
| Fig | quality–latency / quality–cost 权衡曲线 | 监控数据 |
| **Fig** | **散点：向量分 s vs 内容分 c**，标出"高 s 低 c 被丢弃"占比 | 裁决日志 |

> 最后那张散点图是现在唯一缺、却最能一击说服人的：它把中心论点（"相似度不等于有用性"）从一句话变成一个可计数的实证形态。

---

## 5 · 最小可行版（若只剩 6 周）

- 题集缩到 **40 题**（六层等比缩放）；
- baseline 保留 **#1 BM25 / #2 向量 / #4 CE-rerank / #5 CRAG 式** 四个；
- 重复 **3 次**；
- 必做 **F1 答案键隔离 + A2 轨 + 预算匹配**（这三条最便宜、收益最大）；
- 投 **CIKM Applied Research** 并在摘要/C1 把声明限定在自建语料。

> **不要在 F1/F2 未修、题集未重建前冲 Full Research**——`EDITORIAL-DECISION.md` 的 8 个 CRITICAL 里有 6 个是实验问题，不是写作问题。

---

*本文所有"事实"均标注 file:line 或落盘工件路径；未测量项写"未测量"，不做推测。*
