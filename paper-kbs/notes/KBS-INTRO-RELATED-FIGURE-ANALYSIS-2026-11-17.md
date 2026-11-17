# KBS 引言 / 相关工作配图模板分析

日期：2026-11-17 ｜ 服务对象：`paper-kbs/tex/journal_20p/main_20p.tex`（HMRS，投 KBS）

> 与 2026-11-14 那份分析的区别：上一轮定位的是**方法章节的架构图/流程图**；本轮按用户新要求，专门定位**Introduction / Related Work 章节内的配图**，目标是找可直接当作作图模板的优质图。

---

## 1. 方法：先定章节，再定图

新脚本 `paper-kbs/notes/locate_intro_related_figures.py`：

1. 逐页扫描标题式文本行（长度 < 95 且行首匹配），识别 `Introduction`、`Related Work / Background / State of the art / Literature review`、以及其后的第一个 `Method / Model / Framework / Evaluation / Experiment` 等章节；
2. 复用 11-14 已建好的 `kbs_all_figure_index.json`（29 篇逐页图注），把图注页码落在 `[intro_page, first_method_page)` 或 Related Work 区间内的图判为候选；
3. 结果 `kbs_intro_related_figures.json`：**29 篇全部扫描，定位 42 张章节内候选图**。

随后人工看图注筛掉混入的方法/实验图（如 HELIOT 的 prompt 图、LGMT 的柱状图、DualMemory 的训练流程），保留 **13 张**真正具备模板价值且经过逐张视觉核对的图，由 `render_intro_related_figures.py` 渲染 20 页（LGMT p03 只有正文提及、无图注，仅出整页），共 **39 张 PNG**：整页 + 图注上界约束裁剪两种版本，命名后缀 `_intro.png` / `_intro_crop.png`，与上一轮产物区分。

**主交付**：`paper-kbs/reference/kbs/INTRO-RELATED-FIGURE-GALLERY.html`（14 张卡片、5 组、点击放大、可跳整页）。

---

## 2. 13 张精选模板图清单

| # | 论文 / 位置 | 图号页 | 原文图注 | 图型 | 模板价值 |
|---|---|---|---|---|---|
| 1 | FinBloom (KBS 2026) · Intro | Fig.1 / p03 | *Static approach for answering user query without knowledge grounding* | T1 Before | ★★★ 极简 before 图，三元素即可 |
| 2 | FinBloom (KBS 2026) · Intro | Fig.2 / p04 | *Dynamic approach for answering user query with knowledge grounding* | T1 After | ★★★ 与左图同构，贡献边界一眼可见 |
| 3 | LGMT (KBS 2026) · Intro | Fig.1 / p04 | *An illustration of an LLM's failure to maintain logical consistency* | T2 失败案例 | ★★★ 双栏共用问题 + 对话气泡 + ✓✗ |
| 4 | PrivateLibrary (KBS 2025) · Intro | Fig.1 / p03 | *An example of code generation on public library* | T2 失败案例 | ★★ 真实代码 + 绿✓/红✗ + 模型自述气泡 |
| 5 | FineGrained Stateful (KBS 2025) · Intro | Fig.2 / p04 | *A simple example illustrating the differences between the paradigm we propose and the existing mainstream paradigm* | T3 范式对比 | ★★★ 同一真实例子 + 上下泳道 + 回答对照 |
| 6 | MSDiagnosis (KBS 2025) · Intro | Fig.1 / p01 | *An example of our diagnostic benchmark and the multi-step diagnosis task* | T3 范式对比 | ★★ 真实病例 + 单步/多步 + 图标图例 |
| 7 | KnowledgeGrounded Dialogue (KBS 2024) · Intro | Fig.1 / p02 | *An example of knowledge-grounded dialogue with responses from models* | T3 示例对比 | ★★ 多模型回答 + 真值 + grounded graph |
| 8 | XAI MetaSurvey (KBS 2023) · Related | Fig.1 / p02 | *The five main perspectives for the need for XAI* | T4 分类 | ★★ 五圆 + 图标 + 柔和配色 |
| 9 | LLM Understand KG (KBS 2025) · Related | Fig.1 / p02 | *KG is processed into different input formats to provide LLM with knowledge* | T4 背景 | ★★ 左 KG + 右三种输入格式 + 问题答案 |
| 10 | QueryExpansion (KBS 2023) · Related | Fig.2 / p03 | *Semantic network for concept mammal* | T4 概念 | ★ 黑白极简关系图，适合定义 |
| 11 | Survey LLM+KB (KBS 2025) · Intro | Fig.2 / p03 | *The evolution of large language models* | T4 时间轴 | ★★ 水平时间轴 + 交错事件框 |
| 12 | Survey LLM+KB (KBS 2025) · Intro | Fig.1 / p02 | *Overall structure of the paper organization* | T5 论文地图 | ★★ 三列 chevron + 底部大括号 |
| 13 | Journalistic KP (KBS 276, 2023) · Intro | Fig.1 / p03 | *Construction process of the SRA for JKPs* | T5 方法论 | ★ 6 步黑白流程，用于可信性说明 |
> Note: FineGrained Stateful Fig.1 (p03) 也在候选内，但未纳入画廊——它没有进行独立视觉核对，避免把未看过的图当模板推荐。

---

## 3. 5 类可复用模板（画法骨架）

| 模板 | 何时用 | 骨架 |
|---|---|---|
| **T1 Before/After** | 贡献就是流程中新增一个模块 | 两图严格同构；左 `Without X` 只有 Query→LLM→Output；右 `With X` 在中间插入虚线框标 Contribution，LLM 输入变成 `c, x`。灰阶 + 单一强调色 |
| **T2 Failure Case** | 要证明现有方法在真实问题上出错 | 左右共用 Premises/Question；改写一处关键条件用黄虚线框高亮；下方 chat bubble + 机器人图标；答案用 Unknown / No + ✓✗ |
| **T3 Paradigm Comparison** | 贡献是改变整个检索/推理范式 | 上下两泳道（冷色旧 / 暖色新）+ 同一真实问题 + 右侧 Response 逐字标对错；底部一句话说明依据什么做选择 |
| **T4 Taxonomy / Background** | Related Work 交代领域版图 | 2–6 个圆形或圆角框，圆内图标 + 短标题 + `e.g., ...`；或水平时间轴，节点挂年份事件框。柔和配色，文字黑色 |
| **T5 Organization / Dataset** | 引言末尾全文地图 / benchmark 定义 | 综述：3 列箭头带 + 子条目 + 底部大括号；数据集：顶部真实案例框 + 旧/新两条步骤链 + 底部图标图例 |

**共同风格**：引言图多为单栏或 2/3 栏，不是跨栏大图；图注写成 2–3 行小摘要并解释颜色含义；红/绿只表示错/对；图标（人、机器人、文档、数据库、剪贴板）比抽象方框降低理解成本。

---

## 4. 对 HMRS 论文的落地建议

| 级别 | 建议图 | 模板与画法 |
|---|---|---|
| **P0** | **Figure 1：无内容验证 vs 有内容验证** | 套 T1。左：`Without content verification` = Query→向量召回 top-1 (s=0.95)→LLM→错误答案；右：`With content verification` = 召回后插入虚线框 `Contribution: 0–8 Content Rubric`，输出 `c=3 ⇒ discard → not-found report`。两图结构严格对称，灰阶 + 1 强调色 |
| **P0** | **Figure 2：一个具体失败 query** | 套 T2（LGMT + PrivateLibrary）。域外问题；左栏展示「相似度最高但正文无关」候选（红虚线高亮），右栏展示读正文后 `c≤4` 并输出 not-found；底部 chat bubble 写两边模型回答，绿✓/红✗ |
| **P0** | **Figure 3：向量召回范式 vs 内容优先范式** | 套 T3（FineGrained Fig.2）。上泳道冷蓝：整题→向量召回→top-k 堆叠→冗余/错配；下泳道暖橙：按内容路由到领域库→逐候选正文证据核对→采用/fallback/丢弃；右侧同一 query 两种回答 |
| **P1** | Related Work：检索系统版图 | 套 T4。4–5 个圆形：向量检索 / 图检索 / 自反思 RAG / Agent 工具检索 / 内容验证检索（自己高亮），每圆图标 + `e.g., ...`；或「RAG 演化轴」2020→2026 |
| **P1** | 图注写法 | 形如 *An example of content-overrides-vector retrieval. Red denotes a high-similarity but content-irrelevant candidate; green denotes the accepted evidence.* |
| **P1** | 方法论可信性 | 套 T5 的 Journalistic KP Fig.1，画 Rubric 的推导六步，证明不是拍脑袋定的 |
| **P2** | 不要做 | 不要把方法部分的 ArchiMate 架构图搬来当 Figure 1（那是 Figure 4 的位置）；动机图不要用十几种颜色；不要用没有真实 query 的纯抽象方框 |

**一句话结论**：HMRS 最强叙事是「向量很相似但正文不支持」，对应 T2 失败案例图 + T1 前后对比图，比再画一张系统架构图更能让评审在 10 秒内抓住贡献。

---

## 5. 诚实边界

1. **章节定位是启发式的**：按标题行文本匹配，Elsevier 双栏稿的抽取顺序偶有错位。例如 `B_LGMT` 的 Related Work 被识别在 p15（明显偏后），导致窗口过宽混入实验图；这些已人工剔除。`A_Survey` / `B_Survey` 的窗口同理。
2. **边界图**：Journalistic KP Fig.1（p03）、RAG Design Fig.1（p02）严格说处于 Introduction 末尾/方法开头交界，仍作为引言末的方法可信性图收录。
3. **`B_LGMT` p03 无图注**（只是正文提到 Figure 1），已渲染整页但未纳入画廊。
4. **未改动投稿正本**：`paper-kbs/tex/journal_20p/*` 和 `main_20p.pdf` 本轮未触碰，**未 commit/push**；主工作区原有改动完整保留。
5. **不是所有图都适合照搬**：T4 的 QueryExpansion 语义网络是极简黑白概念图，只适合定义，不适合承载贡献叙事。
6. **图片数量**：本轮新增 39 张 `_intro*.png`，与上一轮 88 张方法图累计 127 张，均在 `paper-kbs/reference/kbs/figures/`。
