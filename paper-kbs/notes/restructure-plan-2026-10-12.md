# 论文重构方案：由 QDCVR 检索论文 → 知识库管理系统设计论文

> 目标期刊：**Knowledge-Based Systems (Elsevier, KBS)**
> 依据：用户指令（m00002 / m00004）＋ `/academic-paper` skill Phase 0→2 产物
> 日期：2026-10-12　现存稿：`paper-kbs/tex/main.tex`（1789 行，48 页 elsarticle preprint，7 图 9 表，32 条参考文献）

---

## 0. 用户指令解析（需求基线）

用户原话（m00002，用户连发两次，m00004 同文）：

> 「我的这个项目其实并不是单纯的讲解基于内容检索，而是创建了一个知识库管理系统，因此请你给我按照整个的系统的功能，做详细的讲解，把整个系统设计，架构，功能，全部讲述清楚，不是只讲述这个QDCVR，论文题目可以做一下修改，改为基于内容检索的知识库管理系统设计，然后可以根据当前的真实的项目设计把文章内容做一些修改，讲解整体的系统设计，而不是单纯讲解QDCVR，实验部分可以用QDCVR实验结果，并且要有其他的功能的测试结果，请根据我的需求把整篇文章重构！ /academic-paper 请你使用这个skill对论文做好架构编排，满足KBS期刊要求。」

拆解为 6 条硬需求：

| # | 需求 | 本方案的落实位置 |
|---|---|---|
| N1 | 不是单纯"基于内容检索"，而是**知识库管理系统** | 全篇重定位：§3 系统总览 + §4 采集 + §5 组织与生命周期（新增，最大增量） |
| N2 | **讲清整个系统的设计、架构、功能** | §3–§7 五个设计/实现章节，系统功能表（表 1）逐模块交代 |
| N3 | 论文题目改为**基于内容检索的知识库管理系统设计** | §A 配置记录给出中英标题候选 |
| N4 | 按**真实项目**改写（不是泛泛而谈） | 所有设计描述绑定真实构件：MCP 工具名、`.tree-fs.json`/`.knowledge-base.yml`、MinerU、ChromaDB、Neo4j、medi tation、SOUL、ragctl |
| N5 | 实验保留 **QDCVR 结果** ＋ **其他功能的测试结果** | §8 评估重构为 E1–E7 七组（QDCVR 仍是 E4/E5/E6），新增 E1 采集、E2 组织与一致性、E3 经验库与冥想、E7 非功能 |
| N6 | 用 `/academic-paper` 做好**架构编排**，满足 **KBS** 要求 | 本文档 + KBS 合规检查表（§B） |

---

## A. Phase 0 — Paper Configuration Record（待用户确认）

| 字段 | 取值 |
|---|---|
| **类型** | 系统设计＋实证评估（design-science artifact paper），原创研究论文 |
| **标题（英，主推）** | *Design of a content-retrieval-based knowledge base management system for trustworthy enterprise document intelligence* |
| **标题（英，备选 1）** | *A content-verified knowledge base management system: integrating quality-gated ingestion, content-routed organization, and verified retrieval* |
| **标题（英，备选 2，更贴用户原题）** | *Design of a content-retrieval-based knowledge base management system* |
| **标题（中）** | 基于内容检索的知识库管理系统设计 |
| **目标期刊** | Knowledge-Based Systems（Elsevier）；备选：Expert Systems with Applications |
| **篇幅** | 正文 ≈13,000–14,500 英文词（KBS 无硬性页数上限，常见 6,000–9,000 词；系统类论文可上探）。如需压缩，可裁至 ≈9,500 词（见 §G-3） |
| **结构** | 11 节 IMRaD-变体（系统设计论文式）：1 引言 · 2 相关工作 · 3 系统总览与设计原则 · 4 知识采集 · 5 知识组织与生命周期管理 · 6 内容验证检索 · 7 智能体接口与实现 · 8 评估 · 9 讨论 · 10 有效性威胁 · 11 结论 |
| **引用格式** | Elsevier `elsarticle` + `unsrtnat`（数字制），DOI 全量核验（IRON RULE） |
| **语言** | 正文英文；摘要双语（中文＋英文）；关键词 5–7 |
| **图/表预算** | 图 9–10（新增 1 张"采集—组织—检索"知识流水线证据图）· 表 14–16（新增 系统功能表、数据模型表、采集质量门控表、经验可信度分级表、100 篇流水线审计表、跨语言三模块表、三模式对照表、稳定性表、冥想消融表） |
| **必备声明** | Data availability · Declaration of generative AI · Competing interest · CRediT · Funding · （新增）Ethics（无需伦理审批，写明"不含人类受试者"） |
| **模式** | `revision` 模式（在既有稿上重构），非 `full` 从零生成 |
| **不可变约束** | ① 所有实验数字必须来自已落地运行的日志/JSON，禁止编造；② 不得声称未实现的功能；③ 作者姓名/单位/ORCID/基金仍为占位符（用户需自行补） |
| **确认项（需用户拍板）** | 标题取舍 · 篇幅取舍 · 是否补做"关闸对照"实验（见 §E-3） · 是否保留负面结果为主角之一 |

---

## B. KBS 期刊要求合规检查表

来源：Elsevier KBS Guide for Authors、Elsevier 作者政策、Editorial Manager 流程（2026-10 核）。

| KBS 要求 | 现状 | 本方案的处置 |
|---|---|---|
| **必须是"知识驱动"贡献，不能是"把现成模型套到新数据集"** | 现稿偏"部署型应用系统"，有 desk-reject 风险 | 框架重写为**知识驱动**三段论：知识**获取**（质量门控解析→可检索知识）、知识**表示与组织**（内容路由 + 标签体系 + 文档图 + 经验知识库的可信度分级）、知识**决策支持**（内容验证闸门 + 拒答契约） |
| **必须有隔离"知识组件"贡献的消融** | 部分具备：judged vs fusion-only vs judge-as-filter（检索层消融）；冥想 `exp_hit@3` 消融；缺端到端"关闸"对照 | ① 保留并前置检索层消融；② 新增 E1/E2/E3 的组件证据（去重、路由、描述/标签、经验层）；③ §E-3 建议补做"关闸对照" |
| **方法学新颖性（不是"首次把 X 用于 Y"）** | 有：验证闸门作为平台原语 + 裁决角色分解（filter/ordering/threshold）+ 内容路由组织 | 引言把贡献写成**设计原则 + 可强制契约**，而非"我们做了一个系统" |
| **真实部署情境** | 强项：5 个工业 KB、42 文档、100 篇 arXiv、跨语言 3×400 页 | 全部保留并集中到 §8.1 与 §8.2 |
| CRediT 全体作者 | 有（占位） | 保留 + 按新贡献微调 |
| Competing interests | 有 | 保留 |
| Data availability | 有 | 扩写（新增各功能测试的日志/JSON 路径） |
| Funding statement | 有（无基金） | 保留 |
| 图表按独立高分辨率文件 <10 MB | 现为 PDF/PNG @300dpi | 保留生成脚本 `paper-kbs/figures/figures.py`，出版时导出 TIFF/EPS |
| 可复现（代码/数据可得） | 有：GitHub 仓库 + benchmark-suite | 保留并在 §8.1 写明复现路径 |
| 建议审稿人 / ORCID | 无 | **用户待办**（投稿时在 Editorial Manager 填） |
| 语言门槛（triage 阶段即筛） | 需通读润色 | Phase 7 增加一轮语言与句式一致性检查 |

**风险提示（必须正面处理）**：KBS 编辑最常 desk-reject 的四类之一是——"有部署但无方法学推进的纯应用系统"。因此新稿不能写成产品说明书；每一节都必须落在**可检验的设计决策 + 证据**上，并且至少有一个消融把收益归因到知识组件本身。

---

## C. Phase 2 — 新架构编排（章节级）

### C.0 全书骨架与字数预算

| 节 | 标题 | 现稿对应 | 目标词数 | 状态 |
|---|---|---|---|---|
| 1 | Introduction | §1（L79–252） | 1,300 | 重写 |
| 2 | Related work | §2（L253–388） | 1,200 | 重写（+3 新小节） |
| 3 | System overview and design principles | §3.1–3.3（L389–521） | 1,500 | 大幅扩写 |
| 4 | Knowledge acquisition: parsing, ingestion, and index verification | §3.2 的 20 行 | 1,500 | **新增** |
| 5 | Knowledge organization and lifecycle management | 几乎空白 | 1,800 | **新增（最大增量）** |
| 6 | Content-verified retrieval | §4（L575–735） | 1,800 | 压缩整合 |
| 7 | Agent interface, implementation, and non-functional properties | §5（L736–767） | 1,100 | 扩写 |
| 8 | Evaluation | §6–§7（L768–1527） | 3,000 | 重构为 E1–E7 |
| 9 | Discussion and lessons learned | §8（L1528–1620） | 900 | 改写 + 新增 L6/L7 |
| 10 | Threats to validity | §8.1（L1621–1700） | 600 | 扩写（覆盖新增证据） |
| 11 | Conclusion | §9（L1701–1733） | 300 | 重写 |
| — | 声明 + 附录 | L1734–1789 | 400 | 扩写 |

### C.1 逐节设计

#### §1 Introduction（1,300 词）
- 1.1 问题：企业文档散落在共享盘；三个动作（**采集**、**组织**、**回答**）被分开研究，却必须在一个系统里协同。
- 1.2 现状缺口：RAG 只解决"定位"，相似度≠证据；知识管理文献只解决"组织"，不闭环到回答；文档解析只解决"可读"。→ 需要**以内容为治理对象**的一体化设计。
- 1.3 本文主张（3 条设计原则的种子）：内容决定归属（content-routed organization）、内容决定可采信（content-verified promotion）、无证据则拒答（fail-closed abstention）。
- 1.4 贡献 C1–C6：① 一个以内容为治理对象的知识库管理系统架构与可强制契约；② 质量门控的采集流水线及其 100 篇实证；③ 内容路由的组织与生命周期管理体系（三源一致性、标签治理、去重、图谱、经验库）；④ 多通道内容验证检索与裁决角色分解；⑤ 七组实证（含跨语言 3×400 页、三模式对照、27 轮稳定性）；⑥ 失败模式目录与工程教训。
- 1.5 RQ1–RQ5（见 §C.2）＋ "论文一览表"（保留 `tab:ataglance`，重填）。
- 1.6 与 CIKM demo 的区别（保留现有段落，更新为"demo 只覆盖组织与检索层；本文补齐采集、生命周期、经验知识、非功能与七组实证"）。

#### §2 Related work（1,200 词）
- 2.1 知识库、知识组织与知识管理系统（**新**：KBMS/KM/SECI/经验复用/受控词表与元数据质量）
- 2.2 文档解析与采集流水线（**新**：Document AI、版面/表格抽取、去重与 LSH）
- 2.3 检索：稀疏、稠密、混合与 RAG（现有 2.1，压缩）
- 2.4 结构化与图式组织（现有 2.2，压缩；+ 知识图谱构建）
- 2.5 内容验证、纠错与拒答（现有 2.3，保留 judge 文献批评）
- 2.6 智能体检索与工具协议（现有 2.4，压缩）
- 2.7 定位（现有 2.5；**重做定位表**：加入 KB 管理维度列：采集质量门控/组织治理/生命周期/经验知识/验证/拒答/多通道/工具协议）

#### §3 System overview and design principles（1,500 词）
- 3.1 需求 R1–R6（从系统功能反推）：可解析、可组织、可管理、可检索、可采信、可运维。
- 3.2 设计原则 P1–P6：P1 内容路由组织；P2 内容优先于相似度（验证前置）；P3 契约化终止（每个模块终于 schema/rubric/budget）；P4 失败即拒绝（fail-closed）；P5 可审计（每次判定留痕）；P6 引擎无关（14 个 harness 适配器）。**注意**：现稿 P2 是"MCP 优先"，新稿把 MCP 移到 §7 作为接口实现，原则层保留 6 条设计原则。
- 3.3 架构与子系统（图 1 重绘：客户端/智能体层 → 工具层（**95** 个 MCP 工具，见 §D-0 勘误）→ 领域服务层 → 存储层；旁挂：采集流水线、组织管理、经验/冥想、图谱、人格）。**表 1：系统功能表**（功能 → 构件/工具名 → 设计决策 → 证据编号 E1–E7）。
- 3.4 数据模型与存储布局：**表 2**（`.tree-fs.json` 字段、`.knowledge-base.yml` 文档记录字段、Markdown+images、ChromaDB collection 命名、Neo4j 节点/关系、SQLite 库表、任务注册表）。
- 3.5 对象生命周期：文档状态机（raw→parsed→stored→indexed→verified）、KB 状态（active/merged/split）、版本与重建索引语义。

#### §4 Knowledge acquisition（1,500 词）
- 4.1 多格式接入与 MinerU 解析（OCR/表格/公式/扫描件；返回路径而非内容；Nuxt 代理回填）。
- 4.2 质量门控：SHA-256 精确去重 + 向量近重（≥0.85/0.90 阈值，以实际实现为准）；解析质量门（乱码/空正文/二进制残留 → 拒收）。
- 4.3 结构感知拆分：30,000 字符上限；语义拆分门（0.85 目标利用率、禁止超大原子单元）；part 文件与行偏移寻址。
- 4.4 内容派生的描述与标签：四要素描述规范、标签黑名单/归一化/正文回查、**描述是待验证的声明而非事实**（26 条描述审计中 24 条与正文不符 —— 这是把验证闸门提升为平台原语的经验依据）。
- 4.5 索引构建与可检索性验证：三通道（向量/BM25/图谱）；以 `total_chunks > 0` 判定成功（GPU-OOM 曾返回空载荷成功信封）；A6-V 校验 + 八项终检。
- 4.6 异步执行与失败恢复：非阻塞解析、任务注册表、轮询工具、断点续传。

#### §5 Knowledge organization and lifecycle management（1,800 词，**核心新增**）
- 5.1 内容路由的归置：读正文→选择既有库/提议新库→放置+打标→终检；子库层级；"能放则不放新库"规则。
- 5.2 目录与元数据注册表：`kb_list`/`kb_get_documents` 的渐进式披露；**三源一致性**（磁盘 ↔ `.tree-fs.json` ↔ `.knowledge-base.yml`）作为组织正确性的定义。
- 5.3 标签体系与治理：注册表、孤儿标签检测与清理、归一化、按标签检索。
- 5.4 去重与库体卫生：精确/近似重复识别、合并策略、跨库去重。
- 5.5 库生命周期操作：创建/移动/改名/合并/拆分/删除/重建索引，均为原子操作（磁盘+树索引+YAML 同步）。
- 5.6 文档图谱：Document/KnowledgeBase/Tag 节点、BelongsTo/HasTag/RelatedTo 边、构建信号（共享标签、向量相似、判定）、用途限定为导航与候选扩展而非作答。
- 5.7 运维经验知识库：经验作为一等可检索文档；P0/P1/P2 可信度分级与调节因子；衰减策略；草稿池与人工审批；**自动冥想**（agent-harness 子进程、熔断器、启发式降级）；经验优先检索。
- 5.8 完整性与健康度验证：V1–V9 校验、评分卡、只读审计原则。

#### §6 Content-verified retrieval（1,800 词）
现有 §4 压缩整合：6.1 候选生成 vs 证据（闸门契约：0–8 rubric、阈值 0.5/0.3、批量 ≤6、fail-closed、按引用定位由服务端取正文）；6.2 三条通道（表：优化目标/预算/实测/适用场景）；6.3 通道选择与预算；6.4 拒答契约；6.5 闸门作为平台原语（服务端白名单使通道成为强制层属性）。保留 3.4 的"一次真实查询端到端追踪"作为 §6 的开篇或收尾（现 `sec:trace`）。

#### §7 Agent interface, implementation, and non-functional properties（1,100 词）
- 7.1 MCP 工具面：**95** 个工具 8 组（勘误：现稿写 97，CLAUDE.md 写 94，实测 `kb-mcp/server.py` 为 95）；工具面治理原则。
- 7.2 harness 集成与通道策略：14 个适配器、每通道白名单（21 个只读工具）、会话/权限约束。
- 7.3 实现与运行工程：常驻判定 worker（机器级文件锁、LRU 裁决缓存、CUDA 缓存释放、冷启 10–12 s vs 常驻 1–2 s）；MinerU 子进程生命周期（Windows Job Object / Linux PDEATHSIG / macOS 进程组）；防僵尸端口探测；向量写入按 collection 串行化；BM25 增量；HTTP 客户端 `trust_env=False`。
- 7.4 部署、配置与打包：`config.yml` 单一真源、端口分配、`ragctl` CLI、开源仓库。

#### §8 Evaluation（3,000 词）
- 8.1 实验设置：三个语料（工业 42 文档/5 库；arXiv 100 篇/25 领域；跨语言 en/zh/ja 各 400 页 Wikipedia）；问题集（16 金标 + 4 越界 + 10 arXiv BQ + 跨语言 cloze 40×3）；三种指标族（检索 / 接地与关键事实 / 系统与非功能）；对照与随机性控制（重复轮次、确定性通道、重试策略）；硬件（RTX 5060 8 GB，本地 Windows）。
- 8.2 **E1 采集与解析**：100 篇流水线审计（解析/路由/拆分/去重/描述/存储审计/回归探针）；解析失败率与其在采集设计中的处置；跨语言采集模块（成功率、库归属准确率、存储完整性、自检索 Hit@1）。
- 8.3 **E2 组织、一致性与管理操作**：三源一致性结果；标签健康度；移动/合并/删除后的一致性；图谱构建与查询；规模化（语料规模 vs 延迟/覆盖率）。
- 8.4 **E3 经验知识与自动归纳**：冥想运行成功率、库覆盖、结构完整性、检索接地性、`exp_hit@3` 消融；经验可信度分级的检索行为。
- 8.5 **E4 检索质量**（**已按 H-1 修订：不得出现跨语言检索数字，Module B 全弃**）：工具层 9 配置对照（表：Hit@5/Recall/MRR/延迟）+ 第二语料（arXiv 79 篇，BQ01–BQ10，除 graph 外全 0.9、graph 0.2、BQ03 八配置全败）；**核心消融**：无验证（fusion-only 0.94）vs 验证作重排（0.44）vs 验证作过滤（0.94，符号检验 p=0.008）；阈值与边际（191 条候选、切线上移 0.15→16/17、0.20→17/17、LOO 边际 0.9375 vs 固定 0.20 的 1.0）；复述网格（16 复述 × 9 配置）；三模式对照（平台 vs 裸智能体 vs 稠密检索：接地 10/10 vs 10/10 vs 8/10；关键事实 10/10 vs 8/10 vs 6/10；可核查引用 9/10 vs 6/10 vs 1/10；116 s/48 s/41 s；$0.55/$0.63/$0.28）；分层冒烟（判卷关闭：A 9/10、B 6/10、C 5/10，过度拒答 0）。
  新增补测（见 H-4）：**E-A 关闸端到端消融**（`kb_hybrid_search` enable_judge true vs false，10 题）与 **E-B 组织/分区消融**（pinned-gold / pinned-other / flat / catalog-only），结果到达后写入 §8.5 与 §8.3。
- 8.6 **E5 端到端智能体行为、拒答与代价**：16 次 agentic 运行（4 题×4 臂×2 轮）接地与事实命中；三通道运行点（表）；越界探针拒答 6/6；27 轮稳定性套件（可答 9/9、未覆盖 9/9、越界 9/9，27/27 通道契约合规）；延迟构成（工具 <1 s vs LLM 轮次主导）；三种引擎的成本量级差（agent $0.9–1.8 / claude $0.11–0.36 / omp $0.03–0.07）。
- 8.7 **E6 验证器自身的失效分析**（负面结果为特色）：同域分数膨胀（非金标中位 0.86 vs 金标 0.88，Mann–Whitney p=0.26）；裁决角色不对称；阈值无法拒答；对复述与第二信号（NLI/符号规则）的稳健性。
- 8.8 **E7 非功能行为**：二十路并发写入无数据丢失；索引一致性事故与修复；跨引擎/harness 的稳定性与成本。

#### §9 Discussion and lessons learned（900 词）
保留 L1–L5，新增：
- **L6 知识层是系统的一部分，不是检索的前置**：采集质量门控与三源一致性决定了检索上限（21/100 解析失败若无门控将静默进入知识库）。
- **L7 组织即检索预算**：内容路由与库目录决定了跨库检索的候选生成质量（图书馆通道以目录为先）。

#### §10 Threats to validity（600 词）
现有 6 条扩写 + 新增：新增证据的规模/独立性限制（arXiv 与跨语言语料的题集构造方式）；经验层与冥想的评测来自系统侧；作者自建题集的循环性（保留 Q16 自曝）；KBS 消融完备性说明。

#### §11 Conclusion（300 词）
系统论式收束：以内容为治理对象的 KBMS 如何把"检索到了"变成"系统验证过了"，并在采集、组织、检索、运维四层各自留下可审计契约。

---

## C.2 研究问题（重设）

| RQ | 问题 | 证据组 | 消融/对照 |
|---|---|---|---|
| RQ1 | 如何把"内容优先"落成**可强制**的系统契约（架构与设计原则）？ | §3–§7 设计 + 实现 | — |
| RQ2 | 质量门控与内容路由的采集/组织能否在规模化下产出**可用且一致**的知识库？ | E1、E2 | 门控前后（解析失败、重复、描述质量）；三源一致性 |
| RQ3 | 内容验证的多通道检索是否优于一次性向量 top-k 与未验证融合？ | E4 | fusion-only vs judged vs filter；跨语言 vs 向量基线 |
| RQ4 | 验证闸门的代价与收益是什么，其失效是否结构性？ | E4、E6 | 裁决角色三态；复述网格；第二信号；第二语料 |
| RQ5 | 诚实拒答、延迟、成本与稳定性在运行中落在哪里？ | E5、E7 | 裸智能体对照；三引擎对照；27 轮稳定性 |

与现稿 RQ1–RQ4 的关系：现稿 RQ1（可强制）→ 新 RQ1；现稿 RQ2（代价/收益）→ 新 RQ4；现稿 RQ3（结构性）→ 新 RQ4 的稳健性子问题；现稿 RQ4（诚实与延迟）→ 新 RQ5。新增 RQ2/RQ3 覆盖知识采集与组织层，正是用户要求的"其他功能"。

---

## D. 证据映射表（已清点部分）

> 状态：采集/解析/验证器证据（D-1、D-3）与架构事实（D-2）已核实；跨语言三模块（D-4）、功能/技能测试战役（D-5）、新增参考文献（D-6）由并行清点任务补入。

### D-0 勘误与参数核实（写稿必须使用这些值）

| 项 | 现稿/文档说法 | **实测事实** | 证据 |
|---|---|---|---|
| MCP 工具数 | 现稿 §3.1/§5 写 **97**；`CLAUDE.md` 写 94 | **95**（`@mcp.tool` 装饰器 95 处，逐对 def 校验 95，名称互异 95；`server.py:300` 的 `health_check` 是未装饰的辅助函数） | `kb-mcp/server.py`（正则双路核验）；旁证 `paper_demo/tex/sec2_system.tex:11` "42 kb_* tools inside a 95-tool inventory" |
| 向量分块 | 现稿写 500 字符 / 50 重叠 | **确认**：`chunk_size: 500`、`chunk_overlap: 50` | `config.yml:39-40`；`config.yml:42` `score_threshold: 0.35`；`config.yml:43` `experience_score_threshold: 0.55` |
| 去重阈值 | 现稿写 SHA-256 + 近重 ≥0.90 | **确认**：`kb_find_duplicates(threshold=0.90)`；另有一条手工兜底通道用 0.85 | `.claude/skills/knowledgebase-ingest/SKILL.md:34,38,39` |
| 拆分安全阈值 | 30,000 字符、0.85 利用率 | **确认**（`max_chars` 上限 200,000，下限 500） | `backend/app/api/routes/config_schema.py:163`；`paper-kbs/tex/main.tex:442-443` |

### D-1 采集与解析证据（支持 E1／RQ2）

| 指标 | 数值 | 出处 |
|---|---|---|
| 小规模试跑：10 篇金标 arXiv → 新建 KB | 解析成功 9 / 失败 1；954 chunks | `paper-kbs/notes/review-round4-2026-10-09.md:83-85` |
| 全量：benchmark-suite 100 篇 arXiv PDF | 提交 100 → 状态文件记录 `saved_all` **91** → 实际入库 **79**；失败 **21** | `paper-kbs/experiments/results/exp10_ingest_state.json`；`review-round4-2026-10-09.md:95-97`；`paper-kbs/tex/main.tex:1512` |
| 全量 chunk 产出 | **8,031**（79 篇，≈101.7/篇） | `paper-kbs/tex/main.tex:1403,1512` |
| 领域覆盖 | **26** 个 filenames 域（3–6 篇/域）：agriculture, artificial-intelligence, astronomy, chemistry, climate-science, clinical-medicine, databases, economics, finance, genomics, gravitational-physics, immunology, large-language-models, materials, mathematics, medical-imaging, neuroscience, nlp, oceanography, power-systems, quantum-physics, robotics, seismology, social-networks, speech, statistics | `exp10_ingest_state.json.saved_all` |
| 目标 KB | `6a3c45f2-a1a1-4ce7-b64d-7a5a2f293bb5`，n_docs **79** | `paper-kbs/experiments/results/exp10_papers_toollayer.json` |
| 失败模式（原文） | "21 篇解析失败多为公式密集扫描件"；"中途 kb-mcp 因批量解析崩溃一次, 重启后续跑 (脚本可断点)" | `paper-kbs/notes/review-round4-2026-10-09.md:96-97` |
| 解析耗时 / 逐篇 chunk 统计 | **缺失**（任何 exp10 结果 JSON 都未记录） | — |

**⚠ 三处会计不一致（写稿必须诚实处理，不得四舍五入成"100 篇全部入库"）**：
1. 100 篇提交 → `saved_all` 仅 91 个名字（9 篇无记录）→ KB 内实为 79 篇；两处差额均无 artifact 解释。
2. `exp10_ingest_papers.py:78` 会写 `parse_status`，但提交的 `exp10_ingest_state.json` 里**没有该字段**（文件被后续运行覆盖）。
3. 10 篇金标 PDF（含 BQ03 的 2212.13138）都在 `saved_all` 内，但论文把 BQ03 的全错归因于"解析失败"——状态文件不支持该归因。
   → **建议写法**：报告"提交 100 篇、评测时 KB 内 79 篇、21 篇未进入可检索状态"，把 91/79 差额作为**采集可观测性缺口**写进 §4.6 与 Threats（正好呼应"以可观测效果判定成功"的设计原则）。
4. `exp10b` 的 0.9 分母是全部 10 题（含那篇不可用金标）；限定为 9 题可用集时应为 9/9=1.00。→ 两值并列报告，说明其中一个 miss 是采集失败而非检索失败。

**100 篇语料的第二组审计数据（来自 CIKM demo，可复用于 E2）**：解析并按内容路由 **100/100 → 5 个库**；30k 拆分后 **322** 个 part；每篇九项入库检查 **100/100 通过**；真重复 **0**（近重对 **35**）；描述升级 **165/165**；正文＋存储审计 **322/322** 与 **33/33**；检索回归探针 **15/15**；800 字符稠密副本索引 **4,528** chunks。出处 `paper_demo/tex/sec2_system.tex:31-53`（表 `tab:pipeline`，声明为脚本断言而非人工计数）。

### D-2 架构事实要点（支持 §3–§5、§7）

- **组件与端口**：Web（Nuxt 3，dev 6789 / prod 3000，`defineEventHandler` 代理层）· Backend（Python 3.12 + FastAPI/uvicorn，dev 8765 / prod 8001）· MinerU（隐藏子进程，`MineruApiManager(port=None)` 临时端口，**禁用 8764 硬编码**）· kb-mcp（FastMCP stdio，`.mcp.json` → `uv run --no-sync --directory kb-mcp python server.py`，`--http` 走 SSE）· Neo4j（默认 7687）· ChromaDB（进程内持久化）· `ragctl`（Node CLI：setup/up/status/deps/config/update）。版本 `VERSION = 2.3.0`。优先级 `BACKEND_PORT` env > `config.yml` > 代码默认。
- **`.tree-fs.json`**：全局权威树；顶层键 `version,id,name,type,children,createdAt,updatedAt,nextId,_stats`；节点 `{id,name,type:"folder"|"file",parentId,path,children:[int],metadata,createdAt,updatedAt}`。
- **`.knowledge-base.yml`**：`kb_id`(int)、`name`、`description`、`created_at`、`updated_at`、`meditation`；`documents:[{path,name,description,tags,content_hash,file_size,vector_index,metadata}]`；`metadata.meditation` 随库移动/合并。
- **向量 collection 命名**：每个 KB 一个 Chroma collection，名 `kb_store_<sanitized>`，metadata `{kb_id, kb_name}`，distance `cosine`，embedding `BAAI/bge-m3`；HNSW `M=1000, construction_ef=4000, search_ef=4000`。
- **图谱**：节点 `Document / KnowledgeBase / Tag / Folder / Entity`；关系 `BELONGS_TO / TAGGED_WITH / RELATED_TO / SAME_AS / CONTAINS`（部分标签待最终核实）。
- **HTTP 面**：后端 12 个 router（≈45–48 endpoints：health 1、auth ~7、parse 4、mineru 3、search 2、graph 7、experience 4、config 2、meditation 6、soul 5、system ~6、documents 1）；Web 服务端路由 **69** 个文件 / 9 组（auth 5、filesystem 10、health+stats 2、kb 37、knowledge-bases 2、parse 4、preview 2、skills 1、vectordb 1）。
- **采集流水线（有序，写稿用这条链）**：浏览器 `POST /api/parse/file-vt` → Nuxt 代理 → 后端 `POST /api/v1/parse/file/vt`（异步，返回 task id）→ A0 去重门（指纹 ≥0.85/0.90）→ MinerU 子进程（`MineruParseService` 轮询超时 **600 s**；stdout → `backend/logs/mineru-api.log`，永不走管道）→ 后端只返回 **`markdown_path`**（路径而非内容）→ Nuxt `server/services/pdf-parse-service.ts` 读回并回填 → `TreeFileSystemService.uploadFile()` 同时写磁盘 + `.tree-fs.json` + `.knowledge-base.yml` → A2-Q 解析质量门（乱码/空正文/二进制残留 → 拒收）→ A3b 标签门（黑名单 + 归一化 + 正文回查）→ A3c 描述门（四要素 + 内容回查）→ A5 存储门（解析件必须走 `kb_doc_save_parsed`，禁用 `kb_doc_create`）→ 服务端分块入库（`kb_index_document` / `kb_batch_index`）→ A6-V 索引验证门（collection 名正确 + `chunks ≥ 1`）→ A7 八项终检 C1–C8。
- **关键规则**：向量索引**不自动更新**——`kb_doc_create` / `kb_doc_update_content` / `kb_doc_move` 之后必须显式 `kb_index_document`（stale 向量是检索漏检首因）。
- **闸门实现细节**：`kb_laya_judge(query, documents, criterion="auto", threshold=0.5, max_evidence_chars=40000)`；逐段打分，`noul ≥ threshold` 才存活；全段被拒 → 整篇被拒 → 零存活 → 诚实 not-found；由 `_laya_judge_lock` 串行化（并发判定会触发 torch WinError 1455），超时 **900 s**，`stdin=DEVNULL`。
- **非功能机制**：任务注册表 + `kb_task_status`/`parse_task_status`/`meditation_task_status` 轮询；子进程生命周期 Windows Job Object / Linux `prctl(PR_SET_PDEATHSIG)` / macOS 进程组 + atexit；`main.py:_port_in_use()` 绑定探测防僵尸；限流（通用 120/60 s、重负载 20/60 s）；认证中间件（MCP/user/legacy token）；冥想熔断（连续 3 次失败 → 24 h 禁重试）；经验自动入库门（applied≥2 ∧ rating≥4 → vetted）；`kb_project_update` → `ragctl update` 查 GitHub release；httpx 一律 `trust_env=False`。
- **检索阈值与升级路径**：`kb_search_vector` 宽网 top_k 50–100；`kb_search_two_stage` 为主通道（BM25 → 向量）；候选来自 **<2 个不同 KB** 时升级为企业级三路并行（kb_list / two_stage / 纯向量跨库）→ 去重 → `<50 字符` 降 P2 → 内容重排 0–8 分 → P0/P1 融合；经验可信度 P0 `vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1`、P1 `vector≥0.45 ∧ content≥4`、P2 `vector≥0.35 ∧ content≥3`（默认抑制），disputed（≥3 reviews ∧ rating<2.0）封顶 P2，unvetted（0 reviews ∧ 0 applied）封顶 P1。
- **父库检索 workaround（写 §5.1/§6 时注意）**：子库文档的向量 chunk 实际存在**父库 collection** 下；检索须 `kb_search_vector(kb_id=<父库>)`，而非 two_stage 或子库 UUID。

### D-3 检索与验证器证据（支持 E4／E6，全部为已落地 JSON）

- **exp6 复述网格**（16 复述题 × 9 配置，`paper-kbs/experiments/results/exp6_paraphrase.json`）：bm25 Hit@5 **0.875**／R@5 0.875／MRR 0.755208；dense 0.9375／0.9375／0.833333；rrf 0.875／0.875／0.8125；graph 0.5625／0.5／0.5625；twostage 0.9375／0.90625／0.90625；fusion_only 0.9375／0.9375／0.833333；**judged 0.5／0.46875／0.188542**；filter_only 0.9375／0.9375／0.833333；rrf_fuse 0.875／0.84375／0.629167。（对照原题面：bm25＝1.00 → 复述后 0.875；判卷崩塌在复述下依旧，filter 与 fusion 保持 0.9375。）
- **exp6 LOO 边际**（`exp6_loo_margin.json`）：16 折；`loo_gold_survival 0.9375`；`fixed_020_gold_survival 1.0`；`m_star_values ["0.15","0.18"]`；15/16 折选 m*=0.18 且保住金标（holdout_kept_n 7–12）；唯一例外 Q11（m*=0.15，未保住，固定 0.20 保住）。→ **固定 0.20 垫层优于 LOO 选出的边际**，必须标注为工程经验值而非样本内标定。
- **exp7 第二信号**（191 对，IDEA-CCNL/Erlangshen-Roberta-330M-NLI，`exp7_second_signal.json`）：nli_hit5 **0.3125**／nli_mrr 0.1375；laya_hit5 0.4375／laya_mrr 0.226042；**nli 金标中位 0.0113 < 非金标中位 0.05285（反分离）**；Mann–Whitney p=0.120243225159967；Cliff's δ 0.22853279242731575；Spearman ρ −0.13420631455001675；OOD 四主题 max/median/n>0.5/n>0.8：O1 0.9973/0.2761/18/9、O2 0.9956/0.3414/17/10、O3 0.9967/0.18275/12/7、O4 0.9957/0.24685/12/9；Q6 符号检查 gold_contains_3135 1/1、非金标 0/11（NLI 把 Q6 金标排第 1/12，而判卷排第 10）。
- **exp8 分级探针**（`exp8_graded_probes.json`，工具层 n=6：PA1–PA3 partial、AB1–AB3 absent）：PA1 merged 12/kept 12，0.954→0.666，7.83 s；PA2 12/12，0.876→0.511，1.44 s；PA3 12/11，0.965→0.55，0.68 s；AB1 12/10，0.983→0.5，0.67 s；AB2 12/11，0.968→0.813，0.64 s；AB3 12/11，0.944→0.592，0.79 s。→ 即便是"absent"级探针，闸门仍保留 10–12/12、最高 0.983 分：**工具层自身从不拒答**。agent 层 n=3（PA1 47.9 s/724 字符；PA2 65.9 s/840；PA3 155.7 s；turns 全为 null=未记录）。
- **exp8b 越界 agent**（`exp8b_absent_agent.json`，n=3）：AB1 73.3 s/536 字符；AB2 113.5 s/640；AB3 47.9 s/494；turns null；三条均为显式 NOT_FOUND 并列出检索范围（5 库/42 文档：薄膜工艺知识库 3、aw-industrial 31、生产值守条款 1、光伏组件失效分析库 2、光伏电站运维知识库 5）。AB2：vector 11 + catalog 42，判卷存活 9；AB3：vector 16 + catalog 42，merged 43（重叠 15），judged 12，survived 11。
- **exp9 span/NLI**（191 对，≈320 字符 span，3,489 次 span 推理，`exp9_span_nli.json`）：laya 0.4375／0.226042；nli_head 0.3125／0.1375；**nli_span 0.1875／0.09375**；ensemble_rank 0.3125／0.111458；span 分离度 gold 中位 **0.4728** vs 非金标中位 **0.91855**（反向），gold_min 0.0002、nongold_max 0.999，Mann–Whitney p=0.007414975017999724。→ span 级分离显著但方向错误，max-pooling 放大假阳性，秩融合无补救。
- **exp10b 第二语料工具层**（`exp10_papers_toollayer.json`，n_docs 79，BQ01–BQ10）：除 graph 外所有配置 Hit@5 **0.9**；graph **0.2**（仅 BQ08 rank2、BQ10 rank1 命中）；BQ03（2212.13138）8 个配置全错；单题延迟 0.171–2.253 s，hybrid 1.261–3.763 s；候选 5–12，存活 5–11。

**必须在 Threats 中显式承认的证据边界（来自清点）**：① 采集计数只存在于笔记与正文，JSON 无 attempted/failed 计数器与错误文本；② exp7/exp9 是对同一批 191 条已记录候选对的**回放**，非重新检索；③ NLI 为单一 330M checkpoint、单一模板、tokenizer 后约 500 字符截断（59/191 触顶）；④ exp8 的 agent 层只有 PA1–PA3 且轮次未记录；⑤ exp8 曾把 PA2 事后改判（"PA2意外发现语料含二次交联返工闭环案例(改判covered并注明)"，`review-round4-2026-10-09.md:236-237`），新稿若沿用须标注；⑥ 主语料为 n=16 题 / 42 文档 / 5 库。

### D-4 跨语言三模块基准（`benchmark-web/benchmark/`）——存量 Module B 结果**不可用于任何方向**

- **语料**：`wikimedia/wikipedia 20231101`，经 datasets-server `/rows` 顺序采样，每语 400 页 × {en, zh, ja}；每语 40 道抽取式 cloze 题（年份 span → `____`，答案逐字取自正文），`{"qid":"mqa-<lang>-NNN", ...}`。指纹：corpus sha256_16 en `a73b0036d110ea38` / zh `7da277ed473e64dc` / ja `b6935e3bae573980`；queries `75b468dd5c7eae37` / `65f494e30eb0c36f` / `a5f9be94b660ad25`；采于 2026-09-12。文件：`benchmark-web/benchmark/data/benchmarks/crosslang-manifest-{en,zh,ja}.json`、`cloze-{en,zh,ja}-dev.jsonl`；采集脚本 `benchmark-web/benchmark/scripts/fetch_crosslang_corpus.py:153,178-185`。
- **Module A（入库）——可用且强**：`ingest_success_rate` = **1.0 × 3 语 × 2 轮**（每语每轮 400 篇）；`membership_accuracy` en **0.875** / zh 1.0 / ja 1.0（n=400）；`storage_completeness_mean`（大文档分片求和）en 0.975 / zh 0.9559 / ja 0.9402（n_sampled 40）；`self_retrieval_hit1` en 0.975 / zh 1.0 / ja 1.0（n=40）；第 2 轮与第 1 轮**逐位一致**。出处 `benchmark-web/benchmark/results/benchmark/benchmark_ingestion_{en,zh,ja}_20260912T1300{04,24,41}Z.json`（第 1 轮）与 `..._20260912T1301{01,17,34}Z.json`（第 2 轮），键位 :7-11；分母实现 `benchmark-web/benchmark/scripts/benchmark_ingestion.py:254-255,264-272,279-284`。→ 这是"知识采集"章最硬的跨语言证据，且 en 的 0.875 归属准确率正好是需要诚实报告的组织类缺陷。
- **Module B（检索）——数字自相矛盾且与主张相反，禁止引用**。待验臂 = `staged`（`meta.policy` = "QDCVR deterministic: status→kb_list→two_stage→thr0.35+dedup→doc_read×3"）；基线 = `vector`（`kb_search_vector` top-10，BGE-M3）——`benchmark_content_en_20260912T133147Z.json:1053-1057`。staged：recall@1/@5/@10 = 0.025/0.025/0.025（en，两轮）、0.0/0.0/0.0（zh）、0.225/0.275/0.275（ja）；nDCG@5 0.025/0.0/0.2515；MRR 0.025/0.0/0.2437；stage 命中分布 `{"miss":39,"stage1":1}`（en）/ `{"miss":40}`（zh）/ `{"miss":29,"stage1":9,"stage2":2}`（ja）；**stage3 从未出现，`verification_boost_delta_mean` 六次运行全为 0.0**。基线：recall@1 0.975/0.95/0.95、nDCG@5 0.8885/0.882/0.8853、MRR 0.975/0.9708/0.9708、hit 0.975/1/1、延迟 0.597/0.64/0.657 s（staged 4.216/4.12/4.104 s，工具调用 5.9/5.9/5.62）。
  **不可用的四条理由**：① 度量实现不一致——基线 recall@5/@10 是**原始计数**（3.8、6.875、3.775、6.425、3.4、5.7）而 recall@1 是比率，同一臂出现 recall@5 < recall@1（`benchmark-web/benchmark/scripts/benchmark_content_mcp.py:71`）；② 另有两个 en 运行整体为死值（staged 与 baseline 全 0.0，`hit_dist {"miss":40}`）：`benchmark_content_en_20260912T132330Z.json`、`benchmark_content_en_20260912T132645Z.json`；③ 流水线在 502 处中断——`benchmark-web/benchmark/results/crosslang-final.log:36-74` 抛 `urllib.error.HTTPError: HTTP Error 502: Bad Gateway`（`benchmark_ingestion.py:339/332` → `reindex_kb:217` → `bench_http.py:105`），`final-run.log` 仅 18 行且停在 reindex 中途；④ 40 题里 39 题零命中、仅 1 题 stage1 命中，是**臂失效**的指纹而非管线测量值。
  → **写稿处置**：只用 Module A。不得把 Module B 跨语言数字当作支持**或**反驳；跨语言主张只能由 Module A + `paper-kbs` 单语实验支撑，并在 Threats 写明"跨语言检索战役中途中断，其部分数字不可解释"。修复重跑列为决策项 H-1。
- **Module C（冥想）——零数据**：`benchmark-web/benchmark/results/benchmark/benchmark_meditation_en_r{1,2}.json` 不存在，该树内无任何 `*meditation*.json`；`run_success_rate`/`kb_coverage`/`structural_mean`/`grounded_ratio_mean`/`ablation_exp_hit3_mean`/`ablation_kb_top1_mean` 全部**无值**（脚本 `benchmark_meditation.py:164-180` 定义了键但从未产出）。`results/benchmark-report.html` 从未生成；`docs/BENCHMARK.md:10` 引用的 `docs/benchmark-audit-2026-09-12.md` 不存在。
- **该套件的 agent 臂用的是 HotpotQA/MIRACL 题号**（`dev_10`/`dev_100`/`dev_1003`，`benchmark_content_agent.py:81-91`），**不是** cloze 题集：en hit@1 1 ± 0.0、zh 0.3333 ± **0.4714**、ja 0 ± 0.0（n = 3 题 × 2 次）；zh 的标准差是 `docs/BENCHMARK.md:49` 声称容差 ±0.1 的 4.7 倍。不能用来支撑跨语言主张。
- **该套件唯一的口径文字**在从未运行的报告生成器里（`benchmark-web/benchmark/scripts/make_benchmark_html.py:123-163`），且与存量数字相反（它断言 Module A"三语均为 1.0"、断言 stage3 可证"内容裁决优于相似度排序"）。
- 注意与 `benchmark-suite/results/` 区分：`benchmark-suite/results/BENCHMARK.md:83` 的 "Overall: PASS" 是 50 篇冒烟套件（其 :6-7 自述 "No IR metrics, no LLM judge, no baseline comparison"），不是本三模块基准。

### D-5 运行环境实测快照（2026-10-12，决定补测可行性）

- **活服务**：backend **8771 LISTEN**、web **6789 LISTEN**（8765/6789 中 6789 在听、8765 空闲；6790 空闲）。目录 `web/storage` **不存在**（存储根在别处，由配置决定），`web/storage/tree-file-system` 为空目录。
- **活库目录（`GET /api/kb/catalog`，需 `MCP_AUTH_TOKEN`；本次以 HTTP 只读兜底，因本会话无 MCP 工具）**：**19 个库**，其中
  - **100 篇论文语料仍在，已按内容归置为 5 个领域库**（合计 322 篇/分片）：`计算机与人工智能` b1199132-e4d4-4305-8c2e-82dc1753b0ba（131）· `自然科学与地球科学` 1e6199ea-f380-44e2-94fc-d431f0f9bb6b（75）· `生命科学与医学` b28f0a25-1e1d-40ad-96b8-61bd2b093a28（53）· `工程与能源` 8fa4db59-adde-4d6d-9fdb-2c375400e631（39）· `经济与社会` f5770687-6b05-4a8d-8645-af31686ca87e（24）→ 与 `R2-SCALING-20260921.md` 的 322 docs / 5 KBs 完全对应。
  - 其他：`aw-industrial` 3aea5973-1d8a-4db6-b415-6d4432f514bb（29 篇；**UUID 与 paper-kbs 的 aw-industrial 不同**）· `Corpus-Chunks800`（0，DeepRead 基线索引）· `Novel-PridePrejudice` b4c48237-6937-440a-9696-cc1e66bed5c1（28 篇，30000 字符窗 → 26 part）· `e2e-demo-0923-022632`(3) · `demo-qa-20260927`(5) · `soul-*` 4 个 · `e2e-flow-*`/`ZZ跨库复现库`/`ZZ跨库复现库2`(1) · `AI 基础设施` 5bc21b9b-2a05-470a-9cd6-eaafedfb87a2（3）。
- **⚠ 两个原实验语料已不在活库中**：① `paper-kbs` 主语料的 5 个库（薄膜工艺知识库 84207617…、aw-industrial 2c353c50…、生产值守条款 df2a6584…、光伏组件失效分析库 6c14dfbf…、光伏电站运维知识库 a6eb3fae…）**均不在目录里**；② `KB-CrossLang-{EN,ZH,JA}` **不在目录里**（仅有 `benchmark-web/benchmark/results/ingest-checkpoint-KB-CrossLang-*.json` 残留）。
  → 直接后果：**E-A 关闸对照/E-B 组织反事实无法按原设计在 paper-kbs 主语料上重跑**（语料需重建）；跨语言 Module B 若要重跑必须**先重新入库 1,200 页**（每语 400）。**替代方案**：把补测放到**仍活着的 322 篇 / 5 领域库**上，用 `exp10` 的 BQ01–BQ10 与 R2 的 15 条检索回归探针作为题面（同语料、同指标、可即时执行）。
- **写稿影响**：活体环境本身即"系统在运行中"的证据（19 库、内容路由后的 5 领域库、长文档 30000 字符窗分包）；但任何引用活体状态的地方须写明快照时间与"运行中系统、非冻结快照"。

---

## E. 证据缺口与处置建议

### E-1 已有充分证据的功能（可直接写实测数字）
采集与解析（100 篇流水线审计）、去重、标签治理、三源一致性、图谱写查、经验库与冥想、检索（工具层/智能体层/跨语言）、拒答、稳定性与并发、成本对照。

### E-2 证据薄弱或缺失的功能（需降格表述或补测）
| 功能 | 缺口 | 处置选项 |
|---|---|---|
| 库生命周期操作（合并/拆分） | 有实现与操作记录，缺**受控评测**（合并前后一致性/检索影响） | ① 用已有 `threeway_qa.md`/`SKILL-AUDIT` 记录做**案例式证据**并明确标注为案例；② 或补做一次受控合并实验 |
| 内容路由归置的**反事实**（内容路由 vs 目录路由） | 无对照 | ① 降格为"覆盖与一致性证据 + 设计论证"；② 或补做小规模对照（同批文档按目录名 vs 按内容路由，比较自检索 Hit@1） |
| 闸门端到端消融（关闸对照） | 缺（现稿 §threats 自认为"最重要的下一个实验"） | **建议补做**：4 题 × 1 臂（Lane C 关判）/ × 2 轮 ≈ 8 次运行，复用 `review/fulltest-20261012/run_fulltest.py` 的 SSE 客户端；预计 30–60 min 机时与少量 API 成本 |
| 管理者的外部有效性（读者侧） | 缺（现稿已声明为主要外部效度缺口） | 保留为 Threats，不补测 |

### E-3 建议补测（需用户确认，默认不自动执行）
**E-A 关闸对照实验**：Lane C（`enable_judge=false`）× 4 题（Q2/Q4/Q6/Q7）× 2 轮，指标与 §8.6 完全一致，用来把端到端收益归因到验证组件本身 → 直接回应 KBS"消融必须隔离知识组件"的要求。
**E-B 组织反事实**（可选）：同批 20–30 篇文档，条件 A 按目录名归置、条件 B 按内容路由，比较自检索 Hit@1 与跨库检索 Recall → 把 §5 的组织设计从"设计论证"升为"测量结论"。

---

## F. 迁移映射（旧标签 → 新位置）

| 现稿 | 新稿 | 动作 |
|---|---|---|
| §1 Introduction（含 RQ 与一览表） | §1 | 重写，RQ 换为 RQ1–RQ5 |
| §2 Related work（5 小节） | §2（7 小节） | 增 2.1/2.2，压缩 2.3–2.6，重做定位表 |
| §3.1 Design principles | §3.2 | 原则 5→6 条（MCP 移入 §7） |
| §3.2 Ingestion pipeline | §4 | 扩为独立章（6 小节） |
| §3.3 Storage and service layers | §3.4 + §5 + §7 | 拆分：数据模型、组织管理、实现 |
| §3.4 一次查询追踪 | §6（保留 `sec:trace`） | 改造为"采集→组织→检索"三段时间线 |
| §4 多通道验证检索（6 小节） | §6 | 压缩 |
| §5 Implementation | §7 | 扩写（+工具面治理、部署配置） |
| §6 Experimental setup | §8.1 | 重构（三语料、七组） |
| §7 Results（6 小节） | §8.5–§8.7 | 重编号并前插 E1–E3 |
| §8 Discussion / Threats | §9 / §10 | 改写扩写 |
| §9 Conclusion / 声明 / 附录 A | §11 / 声明 / 附录 | 改写 |
| 图 1–9 | 图 1–10 | 图 1 重绘（+组织与生命周期）；新增 1 张功能证据图 |
| 表：modules/questions/retrieval/agentic/lanes/failures/appendix | 保留并重编号 | 新增 6 张（功能表、数据模型、门控、可信度分级、流水线审计、跨语言） |

---

## G. Phase 3–7 执行计划

1. **Phase 3 论证蓝图**：为 RQ1–RQ5 各写"主张 → 证据 → 反证 → 边界"四元组，落成 `paper-kbs/notes/argument-blueprint-2026-10-12.md`。
2. **Phase 4 起草**：按 §C.1 分节重写 `main.tex`；新章节用真实构件名与实测数字；每节结束自检"claim ↔ citation ↔ evidence"。
3. **Phase 5a 引用**：新增约 10–12 条参考文献（KBMS/KM、Document AI、去重、溯源、知识图谱、RAG 评测等），**逐条 DOI 核验**（Crossref/DOI 解析），写入 `refs.bib` 并更新 `refs_verified.json`；跑 `paper-kbs/tex/check_refs.py`。
4. **Phase 5b 摘要**：重写英文摘要（≈250 词）＋中文摘要；关键词 6 个；`highlights.tex` 5 条 ≤85 字符。
5. **Phase 6 自评**：以 `academic-paper-reviewer` 视角做一轮结构化自审（KBS 编辑视角 + 方法学 + 定位），最多 2 轮修订；Critical 问题必须清零。
6. **Phase 7 排版**：`pdflatex → bibtex → pdflatex ×2`，零错误、零未解析引用；更新 `main.md` 预览与图版本；核对图表编号与交叉引用；生成投稿包清单（图独立文件、声明齐全）。
7. **验收**：① 全篇无 QDCVR-only 叙事残留；② 每条系统功能都有构件名 + 证据编号；③ 每个 RQ 有对应证据组与消融；④ 所有数字可回溯到 JSON/日志路径；⑤ 无编造引用。

---

## G-3 压缩预案（若需降至 ≈9,500 词）
- 合并 §4.6 与 §7.3；§5.3/§5.4 合并；§6 的三通道小节并为 1 节 + 表；E7 并入 E1/E2；相关工作 7 小节并为 4；删去附录逐题表（改为仓库链接）。

---

## H. 用户裁决（2026-10-12 已答复，进入 Phase 3）

| 项 | 用户选择 | 落地动作 |
|---|---|---|
| H-1 跨语言 Module B | **只用 Module A（三语入库），Module B/C 弃用并在 Threats 声明** | §4「知识采集」写三语入库四指标 + 逐位可复现；§10 增一条"跨语言检索战役中途中断，其部分数字不可解释"；不引用任何 Module B 数字 |
| H-2 经验闭环 | **降为案例式证据** | §5.5 用 `review/fulltest-20261012` A6（经验沉淀 + 全局检索 top1）与 `experience_smoke.json`（13 条候选草稿）；正文明确标注 n=1 场景 / 13 候选，不作效果验证 |
| H-4 补测 | **两项都做（关闸消融 + 组织反事实）** | 已启动后台实验任务：E-A 关闸消融（`kb_hybrid_search` enable_judge true vs false，10 题，统一证据包 + 闭卷作答 + 同评分器）→ `paper-kbs/experiments/exp11_gate_ablation.py`、`results/exp11_gate_ablation.json`、`notes/exp11-gate-ablation-report.md`；E-B 组织/分区消融（pinned-gold / pinned-other / flat / catalog-only）→ `exp12_partition_ablation.py`、`results/exp12_partition_ablation.json`、`notes/exp12-partition-ablation-report.md`。均跑在活的 322 篇 / 5 领域库上，只读 |
| H-6 篇幅 | **≈13,000 词 / 11 章** | 按 §C.0 预算执行；§G-3 压缩预案仅作备份 |

**仍未答复 / 硬阻塞**：H-5 投稿元数据（作者姓名、单位、ORCID、CRediT 真实姓名、基金号、通讯作者邮箱、建议审稿人）——现稿仍为 `AUTHOR ACTION` 占位符，Phase 7 生成投稿包前必须填入。

## H-0 原裁决清单（保留备查）

**H-1 跨语言 Module B 的处置**（三选一）
- **(a) 弃用并在 Threats 声明（推荐）**：仅用 Module A（三语入库）＋ `paper-kbs` 单语检索实验；不引用 Module B 任何数字。零额外机时。
- (b) **重跑修复版**：先修 `benchmark_content_mcp.py:71` 的归一化缺陷，再在健康服务上重跑 Module B（需 backend:8771 + web:6790 + `RAG_BENCH_TOKEN`，且先确认 `KB-CrossLang-*` 库仍在）；en/zh/ja × 40 题 × 2 轮，预计 1–3 h 机时。
- (c) 原样引用：**不推荐**——数据自相矛盾，且与核心主张方向相反。

**H-2 Module C（冥想）的处置**
- **(a) 弃用（推荐）**：经验闭环用 `review/fulltest-20261012` A6 场景（经验沉淀 + 全局检索 top1）与 `experience_smoke.json` 作**案例式**证据，明确标注规模（n=1 场景 / 13 候选草稿）。
- (b) 补跑 `benchmark_meditation.py`（2 个 KB，ablation ≤10 条经验，需 agent harness 可用）。

**H-3 采集会计不一致的写法**：按 §D-1 建议报告"提交 100 篇 / 评测时 KB 内 79 篇 / 21 篇未进入可检索状态"，并把 91 vs 79 的差额写成**可观测性缺口**（推荐）。若要更强证据需重跑带计数的采集（见 H-4 的 E-D）。

**H-4 补测授权**（默认不自动执行）：**E-A** 关闸对照（Lane C `enable_judge=false` × 4 题 × 2 轮，复用 `review/fulltest-20261012/run_fulltest.py`，30–60 min）；**E-B** 组织反事实（同批文档按目录名 vs 按内容路由，比自检索 Hit@1）；**E-D** 带计数的采集重跑。

**H-5 投稿元数据（AUTHOR ACTION，硬阻塞）**：作者姓名 / 单位 / ORCID / CRediT 真实姓名 / 基金号 / 通讯作者邮箱 / 建议审稿人名单。当前仍为占位符。

**H-6 篇幅目标**：默认 ≈13,000 词正文（§C.0 预算）；若需 ≤9,500 词按 §G-3 压缩。

---

*本方案待用户确认 §A 的四个确认项与 §H 的六项裁决后进入 Phase 3。*
