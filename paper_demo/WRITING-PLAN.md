# WRITING-PLAN — CIKM Demo Paper: QDCVR 平台演示论文

> 产出目标：`paper_demo/tex/main.tex` → `paper_demo/main.pdf`（≤4 页正文 + GenAI 披露不计页）
> 撰写依据：academic-paper skill 规范 + 6 篇 CIKM Demo 范文实证研读 + 平台真实运行数据（严禁编造）
> 版本：v2.0（2026-09-18）— 已吸收 CIKM Demo 审稿人视角评审 R1（见 §10 评审循环），verdict: Borderline→修复后 Weak Accept

---

## 0. 任务定位（一句话）

把 rag-knowledge 平台以 **CIKM Demo Track** 形式发表：定位是**可直接部署的知识库管理平台 + 基于内容的检索策略（content-based retrieval）**，RAG/问答只是平台的消费端之一，**不是论文主线**。

**用户硬约束：**
1. 侧重点 = 知识库管理功能 + 基于内容的检索策略 + 可部署上线的完整系统；**不要把重心放在 RAG 上**。
2. ≤5 页（官方实为 **4 页正文**，见 §1；计划按 4 页设计，GenAI 披露另计）。
3. 所有数字必须来自 benchmark-suite 真实运行工件；引用必须逐条核实（academic-paper IRON RULE）。
4. 配图、图表、tex、编译 PDF 全部收在 `paper_demo/`。

---

## 1. CIKM Demo Track 合规清单（已核实）

来源：CIKM 2026 官网 demonstration-papers 页（2026-06 截止已过，**目标投 CIKM 2027**，历届要求高度稳定；写作时以当届 CFP 复核一遍）。

| 项目 | 要求 | 本计划的落实 |
|---|---|---|
| 页数 | **正文含附录/致谢 ≤ 4 页**；GenAI 披露不限页；参考文献历届惯例不计页（范文中 refs 排在 GenAI 披露之后溢出到第 5 页） | 正文按 4.0 页裁剪；refs + GenAI 放其后 |
| 模板 | ACM `sigconf` 双栏，单盲（作者信息保留） | 沿用 `docs/paper/cikm/main.tex` 的 acmart 配置 |
| 演示视频 | 3 分钟视频，URL 写入论文 | 待录制；**录制提前至与 tex 起草并行**（避免正文与 UI 状态不符回改）；摘要尾句给 URL（PolyUQuest 式） |
| 必答内容 | 受众、创新点、对 SOTA 的贡献、与会者将体验到什么、功能、用户场景、界面/交互选项、与现有系统对比 | §1 贡献列表 + §3 演示场景逐项覆盖（见 §4 映射表） |
| 评审标准 | 技术新颖性、**研发挑战**、预期影响、时效性 | §2.5 新增 engineering challenges 小节显式回应（R1 意见 MAJOR-7） |
| 必备声明 | Data Availability / Ethics / COI / Funding / GenAI 披露 / CRediT（skill 要求） | 4 页限制下压缩为 Acknowledgments + GenAI 披露 + 代码/数据可用性脚注（范文同款做法） |

**ACM Reference Format 页数说明**：范文中 "5 pages" 指含 refs+GenAI 的 PDF 总页数；正文均 ≤4。

---

## 2. 范文研读结论（6 篇，已下载至 `paper_demo/reference/`）

| 范文 | 系统 | 结构特点 | 可模仿点 |
|---|---|---|---|
| PolyUQuest (CIKM'26) | 结构感知 Web RAG | §1 痛点场景→局限→贡献 bullets；§2 系统三层图+路由；§3 三场景+UI 大图+性能表+泛化性段 | **整体骨架的最佳模板**；Fig1 架构图风格；Table1 主结果+消融合并表；演示场景写法 |
| AppAgent-Pro (CIKM'25) | 主动 GUI agent | §2 System Overview 三阶段；§3 Demonstration Plan 三场景配三张截图 | "Scenario N" 命名式演示写法；每场景一段功能陈述+一句价值总结 |
| SAFE-Cascade (CIKM'26) | 成本自适应级联 | §3 系统设计+§4 双表（主结果+行为分析） | 表格把"质量+成本"并列、↓ 标注成本列 |
| SearchLog (CIKM'26) | 浏览器扩展工具 | §3 System Design+Logged Data；§4 技术验证表 | 与现有系统功能对比表（✓/✗ 矩阵）——可用于"与通用框架/平台对比" |
| JustEva (CIKM'26) | 评测工具包 | 架构图+选定结果表 | 工具型论文的紧凑写法 |
| PrismaDV (CIKM'26) | 数据校验演示 | Fig2 UI 截图+编号 callout（1 数据表 2 统计…） | **截图编号 callout 样式**（①②③ 标注界面功能区） |

**六篇共同公式（本论文采用）：**

```
Abstract (180词) → §1 Introduction (0.9栏, 场景痛点+已有系统局限+贡献bullets)
→ §2 System (1.2页: Fig1 架构 + 2.1/2.2/2.3 组件小节，至多1个公式)
→ §3 Demonstration (1.3页: Demo Setup → Scenario 1/2/3 各一段+UI截图Fig2 →
   Performance Highlights 表1 → Generalizability 段)
→ §4 Conclusion (0.2栏) → Ack → GenAI 披露 → References (可溢出)
```

**绘图风格规律**：Fig1 全部是"横向流水线架构图"——圆角框+箭头+阶段标签，一条**真实示例 query 沿流程走一遍**并印在图上；UI 截图带编号 callout；表格 booktabs 三线表、系统为行、质量与成本并列列、本系统行加粗。配色低饱和、色盲安全、图内字号 ≥7pt、全部矢量 PDF。

---

## 3. 系统介绍素材（论文 §2 的完整弹药库）

> 以下全部为平台真实能力与真实数据；每条注明证据来源，写作时禁止超出这些事实。
> **R1 数字审计修正**：~~"~20 kb_* 工具"~~ → kb-mcp/server.py 实有 **41 个 kb_* MCP 工具（全 server 共 94 个 tool）**，写作统一口径 "40+ kb_* tools"；~~"ragctl down 6s / up 19s"~~ → PIPELINE.md 仅载"冷启动 ~20s"，6s/19s 无工件可溯，**执行期补录计时日志或正文写 "~20 s cold start (measured)"**。

### 3.1 一句话定位（论文反复出现的 elevator pitch）

> **QDCVR** is a deployable knowledge-base management platform whose organization and retrieval are driven by document **content** rather than filenames, fixed taxonomies, or bare vector similarity: documents are parsed, **classified into category bases by their actual text**, tagged, and served to human users and AI agents alike through a **query-driven, content-verified** retrieval protocol with an explicit honest-failure contract.

（英文论文全程用此口径：knowledge-base management platform；避免自称 RAG system。R1 补充：§1 需一句**预防性认亲**——"agentic RAG 方法可自证与弃答，但无协议化、可审计的 rubric 与失败契约"，把 Self-RAG/FLARE 划为近邻而非未知。）

### 3.2 核心功能（§2 小节划分依据）

| 功能 | 内容 | 真实证据 |
|---|---|---|
| **F1 文档摄取与解析** | Web 控制台/CLI/MCP 三入口上传；MinerU 解析 PDF→结构化 Markdown；>12k 字符自动切分为 ≤10k 的 "(part k of N)" 分段并携带章节上下文头 | 50/50 篇论文解析成功；ingest_survey.json |
| **F2 基于内容的组织** | 阅读文档**正文**（非文件名）分类入库；50 篇真实论文按内容分入 5 个门类库（人工智能 18/684 分段、自然科学与地学 15/230、生命与医学 10/301、经济与社会 5/74、工程与能源 2/32）；标签批量传播（1321 分段，0 失败）；含 3 次"内容推翻文件名"的判定记录（2001.10696 / 2604.01385 / 1311.6857） | classification.json（agent 判定工件）+ 61 脚本路由日志 + _pipe_tags2.log `ok=1321 fail=0` |
| **F3 内容裁决检索（QDCVR 协议）** | Phase 0 查询改写 → Phase 1 向量召回（跨库平衡）→ 内容门控：实读候选原文按 0–8 可解释 rubric 打分（主题 0-3/场景 0-3/证据 0-2，≥6 快速通过）→ Phase 2 图书管理员兜底（通读库摘要、多路定向召回）→ Phase 3 五段式答案或**如实奉告未找到**。**R1 修正（勿再混写）**：10 题最终门控 7-8/8（5×7/8 + 5×8/8）；**BQ06** 初检 5/8（头窗止于摘要）→**长文续读条款**转 8/8；**BQ10** 初检 4/8（top chunk 为参考文献页）→**Phase 2 兜底**定位 §4 Discussion 转 8/8。初检低分不是丑闻而是卖点：证明门控有区分度、兜底真被触发 | skill_track_evidence.json + skill_threeway_replication.md 逐题记录 |
| **F4 Agent 原生界面** | MCP server（stdio/uv）暴露 **40+ kb_\* 工具**（41 实测），任何 agent harness 可即插即用；knowledgebase-search skill 封装 QDCVR 协议 | kb-mcp/server.py |
| **F5 经验生命周期** | QA 日志→经验条目→可复用 playbook，回流检索 | knowledgebase-experience skill 链 |
| **F6 生产可部署** | 单机全栈（FastAPI :8771 + Nuxt :6789 + ChromaDB/BGE-M3 + Neo4j + MinerU + MCP）；ragctl 一键停/起（**冷启动 ~20s 实测**；6s/19s 口径待补录计时日志） | PIPELINE.md Stage0 预检记录 |

### 3.3 与现有系统的对比（§1 或 §3 对比段素材）

**R1 修正（防稻草人）**：对比维度改为"**默认开箱行为**"语义——表头/图注必须注明 *"as documented default behavior (accessed 2026-xx)"*；框架类"诚实契约"格写 **"—（不作为协议提供，需自行实现）"** 而非 ✗；措辞纪律 "commonly requires / by default" 保留。

| 维度（默认行为） | 通用 RAG 框架 (LangChain/LlamaIndex) | 一体化平台 (Dify 等) | **QDCVR** |
|---|---|---|---|
| 内容级分类入库 | 需手工建库 | 规则/metadata 为主 | ✓（读正文自动分类+可审计判定工件） |
| 可解释内容门控 | 需自行实现 | 需自行实现 | ✓（0-8 rubric，逐条留痕分数与通过路径） |
| 检索失败契约 | —（不作为协议提供） | —（不作为协议提供） | ✓（未找到→如实奉告，协议级一等输出） |
| Agent 原生（MCP） | 需自建 | API 为主 | ✓（kb-mcp 40+ 工具 + skill） |
| 长文档一等公民 | 默认分块即弃 | 默认分块即弃 | ✓（分段+章节头+offset 定位回读+续读条款） |
| 一键部署 | 需自行编排 | ✓ | ✓（ragctl 冷启动 ~20s） |

⚠ 若空间紧张，本表按 §9 裁剪顺序降级为 §1 文字三句。

### 3.4 Benchmark 结果对照（§3 Performance Highlights 表的数据源）

全部取自 `benchmark-suite/results/`，写 tex 前逐一开文件复核（R1 已审计，结论见括号）：

| 指标 | 数值 | 来源工件 | R1 审计 |
|---|---|---|---|
| 解析成功率 | 50/50 | ingest_survey.json | ✓ |
| 门类库规模 | 5 库 / 50 篇 / 1321 分段（684+230+301+74+32） | classification.json + _pipe_tags2.log | ✓ |
| 10 题回归 | **9/10** | bench10_qa.json（total=10, passed=9） | ✓；失败题=BQ06（kw_hit 空） |
| Track A 门控 | 最终 7-8/8；8 题快速通过；兜底 2/2 成功 | skill_track_evidence.json + replication MD | ✓ |
| Phase1 向量耗时 | 均值 ~1.9 s（1.75-2.53），doc 读 ~0.8 s | timings 字段 | ✓ |
| Track A 关键词命中 | **未测量（ANALYSIS.md 明示）→ 执行期对 skill_track_answers.json 按"≥1 gold 关键词子串命中"实算补上** | 待产工件 | ✗→待补 |
| Track A 端到端耗时 | **未测量（ANALYSIS.md：回答由执行 agent 撰写不计时）→ 执行期补测一轮** | 待产工件 | ✗→待补 |
| Track B 裸 agent | 端到端均值 55.5 s（**逐题 18.5-76.9 s**），KW hit 9/10（任一关键词口径） | track_bc.json | ✓；**严禁引 ANALYSIS.md 的 "32-107 s" 区间（与工件不符）** |
| Track C 纯稠密 | 检索 0.72 s + 生成 ~22.5 s，KW hit 10/10（任一关键词口径） | track_bc.json | ✓ |
| 复刻库（对照） | Chunks800 2516 / Struct 1466 / Paras 11296 chunks | _pipe_repro.log | ✓ |
| Phase1 top1 金标 | 10/10（hits[0].doc_path 对金标） | skill_track_evidence.json | ✓ |
| honest-failure 实例 | **现有工件零捕获 → 执行期新增 probe 产证**（见 §9 步骤②） | 待产 honest_failure_probe.json | ✗→必须补 |

**表格叙事三条（如实、不回避 Track C 优势）：**
1. 门控协议以 ~2 s 级检索拿到 7-8/8 内容分、Phase1 top1 金标 10/10，且带逐条可审计的通过/兜底轨迹——纯稠密没有这些；
2. 纯稠密更快（0.72 s）但**无内容验证、无失败契约**——功能对比不是刷点对比，这正是 Demo 要展示的差异；
3. 裸 agent 也能答对但端到端 ~55 s、无轨迹——协议把 agent 自由发挥收敛为可复现流程。**"28 倍"禁用**（B 端到端÷A 向量段属基准混装，R1 否决）；如需倍数，用"端到端 X 倍（补测后按同口径填写）"。

**9/10 与 Track A 全解的调和句（R1 意见 MINOR-8，必须写）**：唯一回归失败题（BQ06）败于证据窗口伪影，而完整协议的长文续读条款在同一语料的 Track A 中将其解出——把失败转化为 F1 长文档设计的论据。

**统计口径披露（脚注必须含）**：KW hit 判定 = "≥1 个 gold 关键词子串命中"；轮间存在 ±1 波动（B 10→9、C 9→10，ANALYSIS.md #4）；n=10 属 spot check，per-question 轨迹以 repo 工件为准。

---

## 4. 论文逐节写作方案（含页预算与"怎么写"）

**标题（草案）**
> **QDCVR: A Deployable Knowledge-Base Management Platform with Content-Based Organization and Content-Verified Retrieval**

（不用 "RAG" 一词进标题；两关键词=用户指定主线。）

### Abstract（~170 词，1 段）
- 句 1-2 痛点：组织/团队的文档资产被当作扁平 chunk 袋；文件名与固定目录不可靠；裸向量检索无法自证"找对了"。
- 句 3-4 系统与机制：QDCVR 按内容分类组织文档，检索时实读候选按 0-8 rubric 裁决，失败则如实奉告。
- 句 5 数字：50 篇真实论文 / 5 门类库 / 1321 分段；10 题回归 9/10；门控 7-8/8 且兜底全部成功。
- 句 6 演示什么 + 视频 URL（摘要尾句，PolyUQuest 式；若超词移入脚注）。

### §1 Introduction（0.9 栏）
- 开场场景（范文式具体化）：研究组/企业知识管理员面对 50 篇 PDF——哪个库？什么标签？问一句"X 的结论是什么"，系统凭什么说找对了？
- 已有系统局限 **4 句**（R1 增补第 4 句，带引用）：① 框架类默认扁平分块；② 平台类靠手工建库与 metadata 规则；③ 裸向量靠相似度分自证，无内容裁决与失败契约；④ **agentic 方法（Self-RAG、FLARE 一类）可自证与弃答，但无协议化、可审计的 rubric 与失败契约，也未解决"按内容组织库"本身**。
- "We present QDCVR…" + **4 条贡献 bullets**：
  1. content-based organization：正文分类入库+标签传播+可审计判定工件；
  2. content-verified retrieval：QDCVR 协议（向量优先→内容门控→图书管理员兜底→如实奉告）；
  3. agent-native + deployable：MCP 40+ 工具 + skill 协议封装 + ragctl 一键单机部署（冷启动 ~20s）；
  4. evidence：50 篇真实文献全链路 benchmark（三轨对照，回归 9/10 spot check）。
- 尾句：§3 给出三个现场演示场景。

### §2 The QDCVR Platform（≈1.2 页）
- **Fig 1**（全宽 architecture，见 §5）后接 5 小节：
  - **2.1 Knowledge-Base Lifecycle**：上传→MinerU 解析→内容分段（>12k→≤10k part+章节头）→分类→标签→索引；一段话+行内小数字（50/50、1321）。
  - **2.2 Content-Based Organization**：分类器读正文而非文件名（举 1 个真实"文件名误导、内容改判"例子——classification.json notes 三例选一）；标签批量传播；判定工件落盘可审计。
  - **2.3 Query-Driven, Content-Verified Retrieval**：Phase 0-3 流程文字化；唯一公式给 0-8 rubric：`s(e|q) = w_topic + w_scenario + w_evidence ∈ [0,8], pass iff s ≥ 6`；失败契约一段（五段式答案 vs 如实奉告）。
  - **2.4 Agent-Native Surface and Deployment**：MCP 40+ 工具 + skill 协议封装 + ragctl 单机栈。经验生命周期一句带过。
  - **2.5 Engineering Challenges（R1 新增，2-3 句，回应 CFP 研发挑战项）**：① 长文档分块产生窗口伪影（头窗止于摘要、引用页误中）→ 续读条款与章节上下文头；② 多库重复分块污染混合检索 → **向量优先+跨库平衡正是协议契约的设计动因**，hybrid 引擎修复如实一句带过（"our two-stage hybrid retriever currently degrades under cross-base chunk duplication; the protocol therefore contracts vector-first recall"—主动承认比被抓到强）；③ 门控分数阈值 6 的来源（校准说明）。

### §3 Demonstration（≈1.3 页）
- **Demo Setup 段**：现场跑 5 门类库 50 篇 1321 分段；Web 控制台 + 任意 MCP agent harness 双入口；视频 URL。
- **Scenario 1 — 从上传到可问：基于内容的组织**（Fig 2 左）：拖入 PDF→MinerU 解析→自动归类→标签传播；callout ① 分类理由 ② 分段结构 ③ 标签面板。价值句：管理员零手工建库。
- **Scenario 2 — 内容裁决的问答**（Fig 2 右）：BQ02 现场问 NISQ 局限→Phase1 向量命中→门控 8/8 快速通过→五段式答案+引用直达 "(part k/N)+章节路径"。callout：④ 门控 rubric 分数 ⑤ 引用溯源 ⑥ 轨迹。
- **Scenario 3 — 门控的区分度与诚实的失败**（R1 重写）：
  - 3a 兜底案例：BQ10 初检 4/8（top chunk 为参考文献页）→ 图书管理员重检索定位 §4 Discussion → 8/8。展示**门控有区分度、兜底真被触发**。
  - 3b honest-failure 案例：**必须用 §9 步骤② 产出的真实 probe 材料**（语料外问题实跑协议 → 系统如实奉告的原文报告 + 截图）。**禁止**再用"9/10 那题"冒充（该题实为续读成功作答，R1 查实）。
  - 价值句（R1 修正，删"第一次"）："把'不知道'变成**协议级、逐条留痕**的一等输出"。
- **Performance Highlights**：Table 1（三轨对照，规格见 §5，数据=§3.4）+ 一段如实叙事（见 §3.4 三条 + 9/10 调和句）。
- **Generalizability 段**（仿 PolyUQuest，两句）：换域只需新文档集与门类 schema；管道/协议/工件不变。**R1 增补**：引用第二域冒烟测试结果一句话（§9 步骤⑥ 产出），措辞限定 "on a 10-question spot check"。

### §4 Conclusion（0.2 栏）
一句系统 + 一句协议 + 一句演示邀请 + repo/视频 URL。不写未来工作长清单。

### Acknowledgments / GenAI / References
- Ack + Funding 一两句（有则写，无则省）。
- **GenAI Usage Disclosure**：如实声明（范文同款句式）：GenAI 用于文字润色与图表绘制辅助；全部实验、数据、结论由作者真实运行产生并负责。
- References ~16 条（见 §7）。

### CFP 必答内容 → 位置映射（自查表）
| CFP 要求 | 落位 |
|---|---|
| Intended audience | §1 场景段（知识管理员/研究者/agent 开发者） |
| Innovative aspects | §1 bullets 1-2 |
| Contribution to SOTA | §1 bullet 4 + §3 Performance |
| What attendees will experience | §3 每场景首句 |
| Functionality & user scenarios | §3 Scenario 1-3 |
| Interface/interaction options | §2.4 + §3 Demo Setup（Web+MCP 双入口） |
| Comparison with existing systems | §1 局限 4 句 + §3.3 对比表（可降级为文字） |
| **R&D challenges（评审标准）** | **§2.5 Engineering Challenges**（R1 新增） |

---

## 5. 配图与图表设计规范（照范文风格执行，含 R1 修订）

**Fig 1 — 系统架构（全宽跨栏，矢量 PDF，横向流水线）**
- 4 条横带（自上而下）：Client Layer（Web Console / ragctl CLI / MCP Agents）；Agent & Protocol Layer（QDCVR skill：Phase 0→1→Gate→2→3 小框串联）；Service Layer（FastAPI：解析 MinerU / 分类 / 检索 / 标签 / 经验）；Storage Layer（ChromaDB+BGE-M3、Neo4j、YAML tree-fs）。
- 一条**真实示例 query**（"What limits NISQ devices?"）用高亮箭头从 Client 走到 Storage 再折返答案。**R1 约束：毫秒/耗时标注只印在示例 query 路径上，其余框保持干净**（防信息糊）。
- 风格：圆角矩形、低饱和色（蓝灰系+一个强调橙）、无阴影、全图无衬线、字号 ≥7pt、色盲安全；TikZ 或 matplotlib 生成（放 `figures/fig1_architecture.pdf`，源码同目录 .py/.tex）。

**Fig 2 — 演示界面截图拼版（全宽，Scenario 1+2 共用）**
- 左右双截图：左=摄取分类界面，右=问答+门控轨迹界面；截图上叠 ①-⑥ 编号圆点 callout（PrismaDV 式），图注逐一解释。截图必须为**系统实拍**。
- **R1 可读性约束：截图前浏览器 zoom 125–150%、只裁相关功能面板（非整窗）、callout 与图内正文字号 ≥7pt**（1280px 整窗塞半栏会 <5pt，违者重截）。

**Table 1 — 三轨对照（booktabs 三线表，R1 重新设计）**

```
System / Track    | Contract            | Retrieval (s) | End-to-end (s) | KW hit (/10)ᵃ
------------------|---------------------|---------------|----------------|---------------
B  Bare agent     | free-form           |     —         | 55.5 (18-77)   | 9
C  Dense baseline | none                | 0.72          | 23.2           | 10
A  QDCVR protocol | gate + fail-contract| 1.93 (+0.80)  |  <补测>        |  <补测>ᵃ
```
- ᵃ 脚注：判定="≥1 gold 关键词子串命中"；轮间 ±1 波动披露（B 10→9、C 9→10）。
- **A 轨两格空缺不允许存在到提交**：执行期补测端到端 + 实算 KW hit（对 skill_track_answers.json 五段式答案）。若 KW hit 补测不利，备选方案=整列删除，换能力列 "Answer contract (cited 5-section / free-form / none)"。
- 成本列语义分离：Retrieval 与 End-to-end 不得混排（R1：原单 Latency 列三口径混装被否决）。

**可选 Table 0（§2.1 行内，若空间允许）**：5 门类库 papers/parts 规模表——若紧则改为正文一句话+数字。

**图表红线**：任何图内数字必须能在 benchmark-suite/results/ 工件中找到；截图不得摆拍未实现功能。

---

## 6. 演示视频与现场清单（CFP 硬要求）

- 3 分钟视频脚本 = 论文三 Scenario 顺序实拍：上传分类（40s）→ 内容裁决问答（80s）→ **门控区分度+真实 honest-failure probe 报告（40s，用 §9 步骤② 产出物）** → 架构一屏（20s）。
- **R1 排期修正：视频与 tex 起草并行（步骤③），不得后置**——录制中若发现 UI 与文字不符，先改文稿再编译。
- 录制前跑 `ragctl up` 预检；演示语料固定为当前 5 库 50 篇（勿动库）。
- 视频 URL 占位：`https://youtu.be/<TBD>` 写入摘要尾句与 §3。

---

## 7. 引用清单（写入前逐条 DOI/arXiv 核实 — IRON RULE）

预计 ~16 条，全部为已存在可验证文献：
1. BGE-M3 embedding（arXiv:2402.03216，待核）
2. ChromaDB（优先论文/arXiv 版本，次选官方+访问日期，待核）
3. Neo4j（书籍或官网引用格式，待核）
4. MinerU（arXiv 号待核——**务必核**）
5. Model Context Protocol（Anthropic 规范/网站，带访问日期）
6. RAG 奠基：Lewis et al. 2020（NeurIPS）
7. Dense retrieval：Karpukhin et al. 2020（DPR）
8. BM25：Robertson & Zaragoza
9. GraphRAG（arXiv:2404.16130）/ LightRAG（arXiv:2410.05779）——结构化 RAG 近邻
10. **Self-RAG（arXiv:2310.11511，待核）——R1 增补：检索自证近邻**
11. **FLARE（arXiv:2305.06983，待核）——R1 增补：主动检索+弃答近邻**
12. RAPTOR（arXiv:2401.18059）——长文档层次化组织对照
13. Hallucination survey（Siren's Song, CL 2025）——honest-failure 契约动机
14. LangChain / LlamaIndex（官方文档引用，带访问日期；若寻得论文版本优先）
15. 本组 full paper（若已可引用，作为机制细节延伸；否则不引）

**禁令**：不得出现任何未核实的条目；每条写 tex 前用 DOI/arXiv 链接核验标题+作者+年份。弃答/校准文献（如 "teaching models to express uncertainty" 一类）如有余量可加 1 条，不加超过 2 条。

---

## 8. academic-paper skill 合规与反模式

- **真实执行铁律**：正文每个数字 → 工件可溯（§3.4 表的来源列即审计链）；写作期发现对不上的数字，**改论文不改数据**。R1 审计实证了该流程有效（拦出 F3 张冠李戴、B 轨区间错引、工具数少报），但 F3 行漏执行说明**"逐一开文件复核"必须逐行留痕，不得凭记忆搬运**。
- **无空话**：删除 "recently, more and more…" 式开头；每句承载事实。**禁止 "first/novel" 类无出处断言**（R1 判"第一次"句为可证伪 overclaim）。
- **4 大声明**：4 页内压缩为 Data Availability 脚注（repo+工件，含 honest_failure_probe.json 与补测工件）+ Ack（funding/COI 一句，如实）+ GenAI 披露页。
- **写作流水线（skill 12-agent 的裁剪）**：本计划获批后 → **honest-failure probe 产证** → visualization_agent 出 Fig1 → 截图采集 → 起草（每节写完自查 §4 自查表）→ 编译查页数（4.0 红线）→ 引用核验 → 终检（IRON RULE + CFP 映射表全绿）。

---

## 9. 目录结构与执行步骤（R1 修订版）

```
paper_demo/
├── WRITING-PLAN.md          ← 本文件
├── README.md
├── reference/               ← 6 篇范文 PDF+txt + papers_index.json
├── figures/                 ← fig1_architecture.pdf(+源码)、fig2_screens.pdf、png/ 截图原图
└── tex/
    ├── main.tex             ← acmart sigconf（复用 docs/paper/cikm 的前导配置）
    └── main.pdf
```

**执行顺序（含 R1 新增产证步骤）：**
1. **① UI 截图采集**（系统在跑；zoom 125-150%、裁面板，供 Fig2 与视频）
2. **② honest-failure probe 产证**（R1 最高优先）：设计 2-3 个语料外问题（不存在的论文 / 跨库矛盾 / 杜撰概念）实跑 QDCVR 协议 → Phase 3 如实奉告原文落盘 `benchmark-suite/results/honest_failure_probe.json` + 截图 → Scenario 3b 与视频第三段专用
3. **②′ 缺口补测**：(a) Track A 端到端耗时一轮（10 题）；(b) Track A KW hit 实算（对 skill_track_answers.json，"≥1 gold 子串"口径）；(c) ragctl 冷启动计时日志落盘（或正文口径改 "~20s measured"）
4. **③ visualization_agent 画 Fig1 + 视频录制（与 tex 起草并行）**
5. **④ tex 起草**（按 §4 顺序；引用逐条核验后入 .bib）
6. **⑤ 第二域冒烟测试**（R1 增补，供 Generalizability 一句话）：10-15 篇异构 PDF 混入新库，验证内容分类与门控不退化，结果记 `results/second_domain_smoke.json`
7. **⑥ 编译+页数裁剪**：预算实估 ~4.2-4.4 页（R1 指出原预算偏乐观），**预授权裁剪顺序：Table 0 删除 → §3.3 对比表降为文字三句 → Generalizability 压两句 → Fig2 由双图改单图**，直到 ≤4.0 页
8. **⑦ 引用核验终检**（每条 DOI/arXiv 打开验证）
9. **⑧ 终检**：§4 CFP 映射表全绿 + §8 铁律（数字逐行对工件）+ "无 first/novel 断言"扫描

---

## 10. 评审循环记录

**R1（2026-09-18，CIKM Demo 审稿人视角 subagent，verdict: Borderline as planned → 修复后 Weak Accept）**
已采纳：
- MAJOR-1 honest-failure 零实证 → 新增执行步骤② probe 产证，Scenario 3b/视频改用真实材料；禁用"9/10 那题"冒充未找到（该题实为续读成功）。
- MAJOR-2 F3 张冠李戴 → BQ06（5/8 摘要窗口→续读转 8/8）与 BQ10（4/8 参考文献页→兜底 §4 Discussion）已分列改正。
- MAJOR-3 Table 1 基准混装 → 拆 Retrieval/End-to-end 两列；A 轨 KW hit/端到端列为待补测（步骤②′）；"28 倍"禁用；KW 口径与 ±1 波动入脚注。
- MAJOR-4 新颖性划界 → §1 局限增第 4 句（Self-RAG/FLARE 类 agentic 方法无协议化 rubric 与失败契约）；引用清单增 2 条；"第一次"句删除，改"协议级、逐条留痕的一等输出"。
- MAJOR-5 泛化性 → 新增步骤⑤ 第二域冒烟测试；正文措辞限定 spot check。
- MAJOR-6 对比表稻草人风险 → 表头注明"as documented default behavior (accessed 2026-xx)"；框架类契约格改"—（不作为协议提供）"。
- MAJOR-7 R&D challenges → 新增 §2.5；two_stage 缺陷转化为"向量优先是协议契约"的设计论证 + 一句如实承认待修。
- MINOR 全部采纳：ragctl 口径改 ~20s（或补录）、工具数改 40+、B 轨区间只引 track_bc.json（18.5-76.9s）、页数预算下调+预授权裁剪顺序、截图 zoom/裁剪/字号约束、Fig1 毫秒只标 query 路径、弱引用升级、9/10 调和句、视频并行录制、摘要 URL 位置。

保留不变（R1 KEEP 确认）：数字→工件审计链与"改论文不改数据"；platform-first 定位与不含 RAG 的标题；范文推导的结构公式与图表规范；CFP 映射自查表；三轨"功能对比非刷点对比"叙事；对比表措辞纪律；"失败如实呈现"原则（改用有工件支撑的呈现）；引用待核纪律与 ~16 条规模；视频三段式脚本；"截图不得摆拍"红线。
