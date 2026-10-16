# KBS 期刊论文评估报告

**评估对象**：`paper-kbs/tex/journal_20p/main_20p.tex`（Knowledge-Based Systems 投稿版，v2，2026-10-12/13）
**评估日期**：2026-10-16
**评估维度**：① 整体写作逻辑；② 实验结果可否与论文互相印证；③ 是否满足 KBS 投稿要求
**方法**：通读 n1–n11 全部源文件 + 编译产物；对 `paper-kbs/experiments/results/` 全部 23 个产物做数值复算；比对 KBS 官方 Guide for Authors

---

## 0. 结论速览

| 维度 | 结论 |
|---|---|
| **写作逻辑** | **清晰且自洽**，采用"设计→证据"的论证弧 + 5 个 RQ 贯穿；每处主张都区分"机制(Mechanism)"与"检验(Check)"，口径克制。逻辑严密程度高于同类系统论文 |
| **实验印证** | **高度一致**。论文中**每一个头条数字都能从已提交产物复算出来**（逐项核对无偏差）。这是相比 demo 论文的**实质性改进** |
| **KBS 合规** | **结构/声明类要求基本齐全**（CRediT、利益冲突、资金、伦理、数据可用性、GenAI 声明、Highlights 均具备）；**主要风险是篇幅超限**，以及作者信息与 GenAI 声明的工具名仍是占位符 |
| **总体** | **技术上可投**，但作为 KBS 论文存在一个结构性弱点：**核心机制的实验结论是零结果/负结果**，论文自己已把贡献重新定位为"可审计的部署记录 + 一条诊断性警告" |

---

## 1. 整体写作逻辑

### 1.1 论证骨架：一条"设计→证据"弧

论文不是"提出新算法→刷新 SOTA"的范式，而是**部署型系统案例研究（deployed system case study）**。逻辑链：

```
① 问题定义（n1）
   RAG 把「主题相似」当成「证据存在」；
   解析 / 组织 / 检索 / 作答各管一段，
   却没有任何一环对「被引用的句子确由被引文档支持」负责
        ↓
② 设计承诺（n1/n3）——三条契约，分处不同执行层
   C1 内容决定归属（content informs placement）
   C2 内容决定准入（content informs admission）
   C3 缺失必须报告（absence is reported）
        ↓
③ 系统（n3–n7）
   架构 → 数据模型 → 采集 → 组织 → 检索三通道 + 判定闸门 → MCP/运行时
        ↓
④ 证据（n8a–n8c）——E1~E8 八个实验，三套语料，互不混用
   E1 采集解析  E2 组织一致性  E3 经验库  E4 检索质量与裁决角色
   E5 端到端/弃答/成本  E5b 部署层系统臂  E6 判定器失效
   E7 非功能  E8 闸门与检索范围消融
        ↓
⑤ 收敛（n9–n11）
   Discussion → Threats to validity → Conclusion
   「贡献是可审计的部署记录与一条诊断警告，
     不是普适的检索或作答质量优越性」
```

### 1.2 逻辑上的三个亮点

1. **RQ 驱动的阅读契约**。5 个 RQ 在 §1.2 给出，§9 逐条回收并标注各自"证据等级"（RQ1 部分回答、RQ2 操作观察、RQ3 不主张因果……）。读者能清楚知道每条结论的强度边界。

2. **"机制 / 检验"双栏写法贯穿全文**。每条契约都写明 Mechanism（代码做了什么）与 Check（如何被检验），并明确区分二者：
   > "They do not mechanically establish semantic placement accuracy or answer faithfulness."（n3:43）

   这直接回应了上一轮审计发现的"编排靠提示词"问题——论文不再声称服务端强制，而是说"机制在这一层，检验在那一层"。

3. **主动披露负面结果**。论文不隐藏不利数据，反而把它作为主线：
   - 判定器当重排器：Hit@5 0.94 → 0.44（变差）
   - 191 个记录分数**全部 > 0.5 阈值**（闸门什么都没过滤）
   - BM25 在工业语料上 Hit@5 = 1.00（"Nothing here is a retrieval advance"）
   - 闸门消融符号检验 p=1.0（零效应）
   - 端到端三臂 gold-ID 全部 10/10（天花板效应）

### 1.3 逻辑上的弱点

- **正面论点是架构性的，不是被证明的**。三条契约里只有 C2（准入）做了受控检验，而它**失败**了；C1、C3 只有"机制描述 + 观察到的行为"，没有可测量的有效性结论。因此贡献 #1（"A knowledge-base architecture and workflow…"）本质上是**设计陈述**而非实证结论。
- **消融是"重建的"而非原生的**。E8 闸门消融的 `deviation_from_plan` 自己写着：`kb_hybrid_search(enable_judge=...)` 在现行 95 工具层中**已不存在**，故消融围绕 `kb_laya_judge` + 冻结候选集**重建**。论文如实披露，但这使"闸门有效性"这一核心问题的证据强度打折。
- **相关工作的定位是"整合问题"而非"新能力"**。§2.4 自认 "the distinction here is not that abstention or evidence checks are absent from prior research" —— 这降低了新颖性的可辩护空间。

---

## 2. 实验结果能否与论文互相印证

### 2.1 逐项复算（全部命中）

我用 `paper-kbs/experiments/results/` 的产物独立复算了论文的关键数字：

| 论文位置 | 论文数值 | 产物复算 | 结果 |
|---|---|---|---|
| Tab.2 BM25 Hit@5 | 1.00 | `exp1_retrieval.json` → 1.0000 (n=16) | ✅ |
| Tab.2 Dense | 0.94 | 0.9375 | ✅ |
| Tab.2 RRF | 1.00 / MRR 0.927 | 1.0000 / 0.9271 | ✅ |
| Tab.2 Graph | 0.56 | 0.5625 | ✅ |
| Tab.2 Two-stage | 1.00 / Recall 0.97 | 1.0000 / 0.9688 | ✅ |
| Tab.2 Fusion-only | 0.94 | 0.9375 | ✅ |
| Tab.2 QDCVR-Hybrid | 0.44 | 0.4375 | ✅ |
| Tab.2 Judge-as-filter | 0.94 | `exp5_judge_filter.json` → 0.9375 | ✅ |
| Tab.2 RRF-fuse | 0.88 | 0.875 | ✅ |
| E6 第二判定器 Hit@5 | 0.3125 | `exp7_second_signal.json` → 0.3125 | ✅ |
| E6 NLI 中位数 | gold 0.0113 / non-gold 0.05285, p=0.120 | 完全一致 | ✅ |
| E6 span-NLI | gold 0.4728 / non-gold 0.91855, p=0.0074 | `exp9_span_nli.json` 完全一致 | ✅ |
| E4 margin 扫描 | LOO 0.9375 / m=0.20 → 1.00 | `exp6_loo_margin.json` 一致 | ✅ |
| E8 范围消融 | pinned-gold 1.0 / pinned-other 0.0 / catalog rank 1.75 / 路由 6/8 | `exp12_partition_ablation.json` 完全一致 | ✅ |
| Tab.5 三臂网格 | gold 10/10/10 · strict 9/9/9 · alias 10/10/10 · cited 9/7/2 | `exp_r2_grade_corrected.json` 完全一致 | ✅ |
| E8 闸门消融 | 配对均值差 0.2，符号检验 p=1.0 | `exp11_gate_ablation.json`（paired_mean_delta=0.2） | ✅ |

**结论：论文与其实验产物高度自洽，没有发现"写了但复算不出"的数字。**

### 2.2 相比 demo 论文的改进（重要）

上一轮审计发现的 demo 论文问题（A 臂 keyword 报 10 但重算为 9、题集未提交改动、成本漂移）在**期刊版里被正面处理了**：

- 期刊 Tab.5 报 **strict 9/9/9 + alias 10/10/10**，并在 `n10_threats:30-33` 明确写："BQ06 gold key was corrected…the pre-correction question set and its grade (**strict 10/9/9**) are retained alongside the corrected regrade (**strict 9/9/9**)"。
- 三个评分文件同时存在并可复算：`exp_r2_grade.json`(旧) / `exp_r2_grade_corrected.json`(新) / `exp_r2_grade_original_revised.json`。**两套口径都保留**，这符合学术规范。

即：**期刊版的口径比 demo 版更保守、更诚实**。

### 2.3 印证性的三个缺口（需注意）

1. **工业语料不可复现**。`n_back:52-53` 自认："The deployed industrial corpus **cannot be redistributed for contractual reasons**"。论文的**头号检索表（Tab.2，42 篇工业文档、16 题）**因此无法被第三方独立重跑——只能看到结果 JSON，看不到语料。这是最大的可复现性缺口。
2. **多张表依赖归档的 superseded 包**。E5b、E7 及 E8 的部分数字来自 `superseded-20261013-batch2.tar.gz` 等归档；只有 30 单元网格（`run-20261013T094350Z-5f9faac`）是当前未归档的。
3. **标注集仍在变动**。`qa_questions_e5_corrected.json` 的生成时间是 **2026-10-15**（论文数字定稿于 10-12/13 之后）。说明 E5 的标注口径在论文定稿后仍在调整——投稿前需冻结。

---

## 3. 是否满足 KBS 发表要求

KBS 官方 Guide for Authors 要点 vs 当前稿件：

| 要求 | 稿件状态 | 判定 |
|---|---|---|
| 文章类型：original research（≤20 双倍行距页） | 21 页 camera-ready（`[final,5p,twocolumn]`），正文约 14,100 词、9 图 12 表 | ⚠️ **超限风险（最高优先级）** |
| LaTeX `elsarticle` 模板 | `\documentclass[final,5p,times,twocolumn]{elsarticle}` | ✅ |
| 摘要不计入章节编号 | 摘要独立，章节从 Introduction 起编号 | ✅ |
| 摘要词数 | 245 词（KBS 未明确上限，Elsevier 惯例 ≤250） | ✅ |
| Highlights：3–5 条、每条 ≤85 字符 | 5 条，长度 58/67/67/69/70 字符 | ✅ |
| 关键词 | 6 个 | ✅ |
| CRediT 作者贡献声明 | 已具备（`n_back.tex`） | ✅（**姓名为占位符**） |
| Declaration of competing interest | 已具备 | ✅ |
| Funding 声明 | 已具备（"no specific grant" 句式） | ✅ |
| Ethics statement | 已具备 | ✅ |
| Data availability statement | 已具备，含仓库路径与归档说明 | ✅ |
| **GenAI 使用声明**（须置于参考文献之前） | 位置正确（`n_back` 末尾、bibliography 之前） | ⚠️ **内容不合格** |
| 作者信息（姓名/单位/通讯邮箱） | 仍为 `Author Name` / `Co-author Name` / `author@example.com` | ⚠️ **必须替换** |
| 图件格式：矢量 PDF，一图一文件 | 11 个矢量 PDF（`submission-20p/`） | ✅ |
| 参考文献按出现顺序编号 | `elsarticle-num`，54 条 | ✅ |
| Supplementary material | `supplementary-material.pdf` 存在 | ✅ |
| 单盲评审 | 非匿名，符合 | ✅ |

### 三个必须修的合规问题

**(1) 篇幅超限 ⚠️ 最高优先级**
KBS 明文："preferably no more than **20 double line-spaced manuscript pages** (including tables and figures)"。
当前编译产物是 **21 页双栏 final 格式**。换算成 Elsevier 投稿所需的**单栏双倍行距**格式（约 250–300 词/页），正文 14,100 词 ≈ 47–56 页，加 9 图 12 表后**远超 20 页**。
→ 虽然写的是 "preferably"，但这是最可能触发 "please shorten" 甚至退稿的点。**投稿前必须核对投稿格式下的实际页数**，并准备压缩方案（附录 5 张表移入 supplementary、E7/E8 进一步精简）。

**(2) GenAI 声明必须点名工具与版本 ⚠️**
KBS 要求声明中写明 `[NAME OF TOOL/SERVICE]`。当前文字只写 "LLM-based coding agents"，文件里也留着 `%% AUTHOR ACTION: name the exact tool/service(s) and version(s) used`。
→ 必须替换为具体工具名与版本。

**(3) 作者信息与 CRediT 姓名仍是占位符 ⚠️**
`main_20p.tex:65-67` 与 `n_back.tex` 多处 `AUTHOR ACTION` 未处理。KBS 要求作者名与投稿系统一致、通讯作者邮箱上首页。

### 一个需要权衡的软性风险：期刊契合度

KBS 的定位是 "systems that use knowledge-based techniques to support human decision-making"，通常期待**方法/系统有可展示的优势**。本稿的特征是：

- 检索层明确声明 "Nothing here is a retrieval advance"（BM25 三项并列 Hit@5 1.00）
- 核心机制（内容判定闸门）的受控实验是**负结果**（重排有害、阈值零过滤、消融 p=1.0）
- 贡献被自我限定为"可审计的部署记录 + 一条诊断警告"

这类**负结果 / 部署案例**论文在 KBS 并非不能发，但需要审稿人接受"以部署真实性而非性能增益为卖点"。风险在于：审稿人可能认为**系统贡献不足**（更像工程报告）或**结论偏负**。

---

## 4. 总体判断与建议

### 4.1 判断

- **写作逻辑**：**优**。论证弧完整、RQ 贯穿、机制/检验分离、负面结果如实披露。这是本稿最强的部分。
- **实验印证**：**优**。所有头条数字可复算，且期刊版修正了 demo 版的标注口径问题并双口径保留。
- **KBS 合规**：**中**。声明类材料齐全，但**篇幅、GenAI 工具名、作者占位符**三项必须处理。
- **发表可行性**：**有条件可行**。主要障碍不是合规，而是**贡献定位与期刊期待的匹配度**——论文把自己写成了一个"诚实的负结果 + 部署记录"，这在 KBS 需要一个更强的问题重构。

### 4.2 建议（按优先级）

**P0（投稿前必须完成）**
1. 按投稿格式核对页数，压缩到 20 双倍行距页以内；把附录 5 张表与 E7/E8 细节移入 supplementary。
2. GenAI 声明点名具体工具与版本。
3. 替换全部作者占位符与 CRediT 姓名。

**P1（提升可辩护性）**
4. **重构贡献陈述**：把"三条契约"从"已实现的架构"改述为一个**被检验的假设集**，并把"闸门不适合当重排器"提升为**第一贡献**（这是一个可迁移的设计结论，比"我们搭了个系统"更有价值）。
5. **冻结标注集**：投稿前锁定 `qa_questions_e5_corrected.json`，并在文中声明版本号与冻结日期。
6. 明确列出**工业语料的脱敏替代方案**（哪怕是合成样例），否则 Tab.2 的不可复现会成为审稿人的主要攻击点。

**P2（增强说服力）**
7. 为 C1（内容归属）补一个**独立于文件名的**放置正确性度量——目前论文自己承认命名前缀（`{domain}__{arxiv_id}__{slug}`）使基于文件名的路由无法作为独立真值。
8. 若篇幅允许，补一个"闸门作为过滤器在**高混淆密度**下是否仍有价值"的针对性实验，把 E6 的关联性观察升级为可控实验。

---

## 附：评估所用关键证据索引

| 结论 | 证据位置 |
|---|---|
| 21 页 / 245 词摘要 | `paper-kbs/tex/journal_20p/main_20p.log`；`main_20p.tex` |
| Highlights 5 条 ≤85 字符 | `paper-kbs/tex/journal_20p/highlights.tex` |
| 检索表数值 | `paper-kbs/experiments/results/exp1_retrieval.json` |
| 判定角色分解 | `paper-kbs/experiments/results/exp5_judge_filter.json` |
| 第二判定器 | `exp7_second_signal.json`、`exp9_span_nli.json` |
| margin 扫描 | `exp6_loo_margin.json` |
| 闸门消融（重建） | `exp11_gate_ablation.json`（`deviation_from_plan` 字段） |
| 范围消融 | `exp12_partition_ablation.json` |
| 三臂网格双口径 | `exp_r2_grade_corrected.json`、`exp_r2_grade_original_revised.json` |
| 工业语料不可发布 | `paper-kbs/tex/journal_20p/n_back.tex:52-53` |
| 作者/GenAI 占位符 | `main_20p.tex:65-67`、`n_back.tex:11,17,26,57,77` |
| 三条契约与机制/检验分离 | `n3_overview.tex:13-43` |
| 负结果主线的自我限定 | `n8b_eval.tex:244-252`、`n11_conclusion.tex:31-33` |
