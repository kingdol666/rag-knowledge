# KBS 本刊参考文献包 —— HMRS 专用

> **生成日期 / 最后更新**：2026-11-14  
> **服务对象**：投稿正本 **`paper-kbs/tex/journal_20p/main_20p.tex`**（*HMRS: A hierarchical management-and-retrieval system for tiered knowledge document organisation and evidence-traced access*，投 Knowledge-Based Systems, ISSN 0950-7051）。根目录 `paper-kbs/tex/` 是历史稿件，本次未改。  
> **交付规模**：**29 个已验证 PDF（约 59.2 MB）** = 28 篇 KBS 正式文章 + 1 篇 CEUR-WS 配套前驱论文；`kbs_refs.bib` **29 条 BibTeX**（28 × `@article` + 1 × `@inproceedings`）  
> **筛选漏斗**：OpenAlex 全刊扫描 1787 篇（2023+，OA）→ 191 篇主题匹配且有可下载 PDF → 121 篇初筛候选 → 36 篇 KBS shortlist（+1 篇 CEUR 配套）→ **28 篇 KBS + 1 篇配套下载成功，8 篇 KBS 未获取**  
> **整合状态（2026-11-14 已完成）**：29 条中 2 条与正本已有 DOI 重复，净并入 **27 条**；27 条**全部在正文引用并出现在参考文献列表**；`main_20p.pdf` 完整编译为 **20 页 / 0 错误 / 0 未定义引用**。详见第 5 节。  
> **第二轮复核（同日）**：按 29 篇 PDF 摘要逐条核验引用的**内容、位置与时机**，查出 1 组位置错配 + 5 处描述不符并已全部修正，重新编译验证 15/15 检查通过。报告见 `paper-kbs/notes/CITATION-CONSISTENCY-AUDIT-2026-11-14.md`。  
> **绘图风格核查（2026-11-14）**：全量扫描 29 篇图注与图像密度，导出 88 张真实图页并逐张视觉核对，产出 `FIGURE-GALLERY.html`（20 张方法图精选）与 `KBS-FIGURE-STYLE-ANALYSIS-2026-11-14.md`；校验 7/7 PASS。  
> **引言/相关工作配图（2026-11-17）**：按章节标题定位出 42 张 Intro/Related 候选，新增 39 张 `_intro*.png`，产出 `INTRO-RELATED-FIGURE-GALLERY.html`（13 张模板精选）与分析报告；校验 8/8 PASS。这两轮均**未改动投稿正本、未 commit/push**。

---

## 0. 为什么专门补这一批

审计起点是历史稿 `paper-kbs/tex/refs.bib`（39 条，无 KBS 本刊文章）。**口径更正（2026-11-14）**：当前投稿正本是 `paper-kbs/tex/journal_20p/main_20p.tex`，其 `refs.bib` + `refs_new_verified.bib` 共 70 条，**已含 5 篇 KBS 本刊文章**（`yang-kbs-llm-2025`、`ghali-kbs-retrieval-2025`、`li-kbs-rmrsst-2026`、`shen-kbs-teierag-2026`、`kinalioglu-kbs-eprag-2026`）。所以本包的价值不是"从零补本刊引用"，而是把本刊近三年**系统 / 平台 / 架构 / 部署类**工作成体系补齐，让参考文献列表真正反映稿件"知识管理系统"的文体归属——这正是 KBS 审稿人判断 fit 的依据。

这批文献按**两个筛选条件**挑，正好对应用户的要求：

1. **与 HMRS 主题近似**：内容验证门、检索车道、诚实弃答、知识库组织、Agent 原生接口、评测/负结果；
2. **属于"软件系统设计开发"文体**：提出并实现系统/平台/框架/参考架构、给出模块契约与部署案例，而非只报告一个算法在 benchmark 上的分数。

**Tier 命名规则**（也就是文件名前缀）：

| 前缀 | 含义 | 数量 |
|:--|:--|:--|
| `A_` | **系统 / 平台 / 架构 / 部署型**论文——"我们设计并实现了 X 系统" | 15（含 1 篇配套 companion） |
| `B_` | **方法 / 检索 / 评测 / 综述型**论文——用于 Related Work 定位与基线 | 14 |

---

## 1. 交付清单与验证方式

| 路径 | 用途 |
|:--|:--|
| `paper-kbs/reference/kbs/*.pdf` | 29 个全文 PDF |
| `paper-kbs/reference/kbs/kbs_refs.bib` | **可直接合并**进 `tex/refs.bib` 的引用条目，每条 `note` 指向本地 PDF |
| `paper-kbs/reference/kbs/README.md` | 本文件：分组、精读顺序、Related Work 写法、版本与缺口说明 |
| `paper-kbs/reference/kbs/FIGURE-GALLERY.html` | **方法图画廊**：20 张精选核心架构图/执行流程图，附原文图注、论文解读与风格点评，可点击放大 |
| `paper-kbs/reference/kbs/INTRO-RELATED-FIGURE-GALLERY.html` | **引言/相关工作图画廊（2026-11-17）**：13 张精选动机图、失败案例图、范式对比图、分类结构图，可作 Figure 1 模板 |
| `paper-kbs/notes/KBS-INTRO-RELATED-FIGURE-ANALYSIS-2026-11-17.md` | 引言配图定位方法与 5 类模板骨架、对 HMRS 的 P0–P2 落地建议 |
| `paper-kbs/reference/kbs/figures/*.png` | 88 张渲染图页（`__pNN.png` 整页 144 dpi / `__pNN_crop.png` 图区裁剪 216 dpi） |
| `paper-kbs/notes/KBS-FIGURE-STYLE-ANALYSIS-2026-11-14.md` | 15 篇重点论文解读、核心图精确定位表、KBS 绘图风格 8 条规律、对 HMRS 的 P0–P2 画图建议 |
| `paper-kbs/notes/kbs_download_manifest.json` | 37 个 shortlist 候选中每一篇的 DOI / 引用数 / 下载状态 / 失败原因 |
| `paper-kbs/notes/kbs_verified.json` | 29 篇的页数、首页文本、来源 URL（验证证据） |
| `paper-kbs/notes/kbs_guide_data.json` | 29 篇的 bibkey、作者全名、卷号、页码（本指南的数据来源） |
| `paper-kbs/notes/kbs_downloadable_scan.json` | 191 篇主题匹配且可下载的全刊候选（后续想扩参考文献时从这里挑） |
| `paper-kbs/notes/{find_kbs_oa,scan_kbs_downloadable,download_kbs_refs,retry_kbs_misses,make_kbs_bib}.py` | 全部检索 / 下载 / 验证 / 生成脚本，可复现 |

**每个 PDF 都过了三道验证**：`%PDF` 文件头、≥ 30 KB、`pypdf 6.14.2` 能读出页数与首页文本（首页文本已存入 `kbs_verified.json`，可肉眼核对是不是标题对得上的那篇）。29 篇全部通过，**invalid = 0**。

---

## 2. 优先精读 10 篇（按与 HMRS 的贴近度排序）

| # | 文件 | bibkey | 年份 / 引用数 | 为什么先读它 |
|:--|:--|:--|:--|:--|
| 1 | `A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf` | `ocaa2023software` | 2023 / 12 | **与"软件系统设计开发"最贴合**：提出知识平台的**软件参考架构**、模块职责、架构原则 + PoC 原型，与 HMRS §3 的 P1–P5 设计原则 / 模块契约表几乎是同一文体。第三轮才拿到的正式 Elsevier VoR 版（16 页） |
| 2 | `B_RAG_EngineeringDesignKnowledge_2024.pdf` | `siddharth2024retrieval` | 2024 / **105** | 工程设计知识上的 RAG 部署案例；HMRS 自称 "deployed industrial case study"，这是本刊内最直接可比的先例 |
| 3 | `A_LLM_IR_System_BankSupervisors_2024.pdf` | `aarab2024system` | 2024 / 6 | 面向银行监管者的**部署型 IR 系统**，同样是"高可信领域 + 真实用户 + 检索系统"叙事 |
| 4 | `A_KG_Orchestra_OpenSource_MultiAgent_Framework_2026.pdf` | `mohamed2026orchestra` | 2026 / 0 | **开源多智能体框架 + 证据驱动知识图**：技术形态（多 Agent、工具化）和文体（开源框架）双重贴近 HMRS 的 MCP 优先架构 |
| 5 | `A_MSDiagnosis_Benchmark_Framework_MultiStepClinical_2025.pdf` | `hou2025msdiagnos` | 2025 / 15 | "**benchmark + 框架 + 多步评测**"的分层评测设计，与 HMRS 工具层 / Agent 层 / 稳健性层三层实验同源 |
| 6 | `A_Coordinated_LLM_MultiAgent_QA_2025.pdf` | `saadaoui2025coordinat` | 2025 / 24 | 多智能体协同问答系统；对应 P2 MCP 优先接口与 P5 可插拔 harness |
| 7 | `B_Survey_LLM_KnowledgeBasedMethods_2025.pdf` | `yang2025comprehen` | 2025 / **109** | **KBS 本刊** LLM × 知识方法综述，用作 §2 Related Work 的定位锚点（"我们属于哪一支"） |
| 8 | `B_PrivateLibrary_CodeGeneration_LLM_2025.pdf` | `zan2025private` | 2025 / 44 | 私有库检索增强生成；与 HMRS "自托管语料 + 库内证据"设定最接近 |
| 9 | `B_LGMT_ReasoningReliability_Testing_2026.pdf` | `zhou2026lgmt` | 2026 / 4 | 推理可靠性的逻辑接地测试；对标 §7.3「**验证器自身的失效**」这一负结果的写法 |
| 10 | `A_Building_OpenQA_LowResource_2024.pdf` | `budur2024building` | 2024 / 12 | "**构建 X 系统**"类论文的系统实现 + 评测章节模板，可直接借鉴谋篇 |

> 引用数为 OpenAlex `cited_by_count`（检索日 2026-11-14），**只用于排阅读优先级，不要写进论文正文**。

---

## 3. 全量分组索引（29 篇）

### 3.1 软件系统 / 平台 / 架构 / 部署型（12 篇 KBS + 1 配套 = 13 个文件）

| 文件 | bibkey | 与 HMRS 的对应点 |
|:--|:--|:--|
| `A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf` | `ocaa2023software` | 参考架构 + 架构原则 + PoC ↔ §3 P1–P5 / 模块职责表 |
| `A_COMPANION_Developing_SoftwareRefArch_JKP_CEUR2021.pdf` | `gallofr2021jkpdesign` | 同一作者团队的设计科学方法前驱；**非 KBS 文章**，只作方法学旁证 |
| `A_LLM_IR_System_BankSupervisors_2024.pdf` | `aarab2024system` | 部署型 IR 系统工业案例 ↔ "deployed case study" |
| `A_KG_Orchestra_OpenSource_MultiAgent_Framework_2026.pdf` | `mohamed2026orchestra` | 开源多 Agent 框架 + 证据驱动 ↔ P2 MCP 优先 |
| `A_Coordinated_LLM_MultiAgent_QA_2025.pdf` | `saadaoui2025coordinat` | 协同问答系统 ↔ P5 引擎无关的可插拔 harness |
| `A_Building_OpenQA_LowResource_2024.pdf` | `budur2024building` | 系统实现 + 评测文体范本 |
| `A_Building_KnowledgeGrounded_Dialogue_2024.pdf` | `yang2024building` | 知识接地对话系统 ↔ 内容驱动组织 |
| `A_HELIOT_LLM_CDSS_2025.pdf` | `vito2025heliot` | 领域知识库 + 可信输出 ↔ P3 晋升前验证 / P4 诚实弃答 |
| `A_Practical_PrivacyPreserving_Framework_LLM_Services_2026.pdf` | `liao2026practical` | 真实服务工程约束 ↔ §5 实现章节 |
| `A_Enhancing_LLM_Systems_CircuitAnalysis_2026.pdf` | `chen2026enhancing` | 端到端系统增强 ↔ 系统工程方法 |
| `A_Automating_EngineeringModeling_LLM_Agents_2026.pdf` | `liu2026automatin` | 工程应用中的 LLM Agent 自动化 ↔ 工业部署视角 |
| `A_SigOpt_Mulch_IntelligentSystem_AutoML_2023.pdf` | `sorokin2023sigopt` | 智能系统构建 + 自动化评测 ↔ 系统工程文体 |
| `A_GOFAI_Meets_GenerativeAI_ExpertSystems_2026.pdf` | `garridomer2026gofai` | 用 LLM 开发专家系统 ↔ 知识系统工程化 |

### 3.2 RAG / 知识检索 / 知识层 / 内容组织（10 篇）

| 文件 | bibkey | 与 HMRS 的对应点 |
|:--|:--|:--|
| `B_RAG_EngineeringDesignKnowledge_2024.pdf` | `siddharth2024retrieval` | 工程设计知识的 RAG 部署（105 引，必引） |
| `B_KnowledgeRetrieval_InContextLearning_SemanticSearch_2025.pdf` | `ghali2025enhancing` | 知识检索 + 语义搜索 ↔ 三车道召回层 |
| `B_SoftPrompt_DenseRetrieval_2024.pdf` | `peng2024soft` | 稠密检索增强 ↔ 向量召回基线讨论 |
| `B_QueryExpansion_SemanticRelations_RetrievalSystems_2023.pdf` | `massai2023evaluatio` | 查询扩展对检索系统的影响 ↔ 查询改写层 |
| `A_FineGrained_StatefulKnowledgeExploration_2025.pdf` | `tao2025fine` | 图检索 + 细粒度知识探索 ↔ Librarian 分层导航 |
| `B_GeoFuB_OperatorFunction_KnowledgeBase_2025.pdf` | `hou2025method` | 领域知识库自动构建 ↔ 内容派生标签 / 元数据 |
| `B_LLM_Oracles_OntologyInstantiation_2025.pdf` | `ciatto2025large` | LLM 实例化领域本体 ↔ 知识层构建 |
| `B_LLM_Understand_KnowledgeGraphs_2025.pdf` | `dai2025large` | LLM 与知识图交互 ↔ 图存储只做候选扩展的设计 |
| `B_Prompting_LLM_KG_LongTailFacts_QA_2025.pdf` | `huang2025prompting` | 长尾事实问答 ↔ 跨库检索 |
| `B_PrivateLibrary_CodeGeneration_LLM_2025.pdf` | `zan2025private` | 私有库检索增强 ↔ 自托管语料 + 库内证据 |

### 3.3 可信性 / 评测 / 验证器失效 / 记忆（4 篇）

| 文件 | bibkey | 与 HMRS 的对应点 |
|:--|:--|:--|
| `B_LGMT_ReasoningReliability_Testing_2026.pdf` | `zhou2026lgmt` | 逻辑接地变形测试 ↔ §7.3 验证器失效诊断 |
| `A_MSDiagnosis_Benchmark_Framework_MultiStepClinical_2025.pdf` | `hou2025msdiagnos` | 基准 + 框架 + 分层评测 ↔ §6/§7 实验结构 |
| `B_InformationTheoretic_DualMemory_System_2025.pdf` | `wu2025informati` | 双记忆系统 ↔ 经验层 / 长期记忆 |
| `B_FinBloom_KnowledgeGrounding_RealtimeData_2026.pdf` | `sinha2026finbloom` | 实时数据知识接地 ↔ 证据新鲜度 / 来源可追溯 |

### 3.4 综述与定位锚点（2 篇）

| 文件 | bibkey | 与 HMRS 的对应点 |
|:--|:--|:--|
| `B_Survey_LLM_KnowledgeBasedMethods_2025.pdf` | `yang2025comprehen` | KBS 本刊 LLM × 知识方法综述（109 引），§2 定位锚点 |
| `B_XAI_MetaSurvey_2023.pdf` | `saeed2023explainab` | XAI 元综述（**945 引**），支撑 "inspectable evidence" 论证 |

---

## 4. 已写入正文的引用布局（2026-11-14 实施）

> **叙事口径提醒**：投稿正本已改版为「层级管理 + 分层访问 + 可审计状态」，不再是早期
> QDCVR / 内容验证门三车道的叙事（本包初版按旧评估文档写的"验证门平台级原语"句式
> **已作废**）。所有新增段落按新论点落地：HMRS 的差异化是
> **collection membership、derived descriptions、lifecycle state 可审计**，
> 而非"检索算法更优"或"验证门是原语"。

27 条净新增按论证逻辑写入 `n2_related.tex`，每处都是「本刊已有工作分类 → HMRS 差异」的连贯段落，不堆砌文献。**布局经过第二轮引用一致性审计修正**（见下方），不是初版的三组硬塞：

| 位置 | 落地论点 | 实际引用键 |
|:--|:--|:--|
| §2.1 Knowledge management and document acquisition（新增段） | 本刊已有软件参考架构 + 早期 workshop 版与 PoC、完整知识接地系统、部署约束、领域知识库构建，以及**完整系统类贡献**（多 Agent 框架 / 工程建模 / 电路分析 / GBT 超参 AutoML）；HMRS 把集合归属、派生描述、生命周期状态作为可审计对象 | `ocaa2023software`, `gallofr2021jkpdesign`, `yang2024building`, `budur2024building`, `vito2025heliot`, `aarab2024system`, `liao2026practical`, `garridomer2026gofai`, `hou2025method`, `ciatto2025large`, `mohamed2026orchestra`, `liu2026automatin`, `chen2026enhancing`, `sorokin2023sigopt` |
| §2.2 Retrieval, organisation and agentic search（新增段） | 检索栈的工程化扩展（RAG 部署、软提示、查询扩展、私有库、KG prompt 理解、长尾 KG 提示、图导航、实时接地、多智能体）；HMRS 问的是"哪个受管集合权威、状态可否审计" | `siddharth2024retrieval`, `peng2024soft`, `massai2023evaluatio`, `zan2025private`, `dai2025large`, `huang2025prompting`, `tao2025fine`, `sinha2026finbloom`, `saadaoui2025coordinat` |
| §2.3 开头 agent memory 段 | 与 MemGPT / Mem0 / A-MEM 并列的持续学习双记忆系统 | `wu2025informati` |
| §2.3 Verification, correction and abstention（末段） | **纯可信性/评测**：XAI 元综述、逻辑接地变形测试、多步临床诊断基准；HMRS 只声称报告自身证据门的失效并转成配置规则 | `saeed2023explainab`, `zhou2026lgmt`, `hou2025msdiagnos` |

**第二轮审计修正（`notes/CITATION-CONSISTENCY-AUDIT-2026-11-14.md`）**：初版曾把 5 篇与验证/可信性无关的系统工程与持续学习文献塞进 §2.3 的 "trustworthiness side"，属**位置错配**，编译与引文脚本都查不出来；另有 4 处断言超出摘要证据（"reasoning substrate"、"automated model evaluation"、"design-science derivation"、"clinical reasoning"），以及并列引用误带 "under domain shift" 限定语。现已逐条按 PDF 摘要证据改写，并移动 `n8a_eval.tex` 那句到指标定义之后。**引用是否出现 ≠ 引用是否正确**。

**顺带修好的既有问题**：正本原有 6 条"定义了却从未 `\cite`"（因此根本不会出现在参考文献列表）的孤儿条目。其中 5 条已真实补进正文：

- `feng-abstain`, `yin-knowwhat` → §2.3 作为**独立并列项**（"identifying what LLMs do not know"），不再与 `kamath` 共享 "under domain shift" 限定语；
- `es-ragas-2024`, `saad-falcon-ares-2024`, `jarvelin-cumulated-gain-2002` → `n8a_eval.tex` 的 *Measures and controls*，紧跟指标定义句；RAGAs/ARES（生成答案语义质量）与 cumulated gain（排序 graded relevance）分开陈述，并明确写出**为什么不用**它们。

第 6 条 `hmrs-demo` 是本项目自己的前置 demo 论文，**匿名评审下故意保持未引用**，因此也不进入参考文献列表——这是唯一被允许的"定义了但未引用"条目，不要为了凑数把它引上。

**两条重复项**：`yang2025comprehen` 与 `ghali2025enhancing` 在正本中已分别以 `yang-kbs-llm-2025`、`ghali-kbs-retrieval-2025` 存在并被引用（DOI 完全相同），故**未并入**，避免同一文献在参考文献列表出现两次。

---

## 5. 整合结果与编译验证（2026-11-14 已完成）

整合目标**不是**根目录 `tex/refs.bib`（历史稿），而是投稿正本加载的
`paper-kbs/tex/journal_20p/refs.bib`（`main_20p.tex` 里是
`\bibliography{refs,refs_new_verified}`）。脚本
`paper-kbs/notes/integrate_kbs_refs.py` 幂等执行，产出
`paper-kbs/notes/kbs_integration_report.json`；包内 `kbs_refs.bib` 保持原样
（留着 `note` 本地路径便于阅读），投稿 bib 里的副本已做投稿级清洗：

| 处理 | 说明 |
|:--|:--|
| DOI 去重 | 去掉 2 条与正本重复者，净并入 **27 条** |
| 删 `note` | 避免本地 PDF 路径出现在投稿参考文献列表 |
| 字符转义 | `Gallofr{\'e}` / `Oca{\~n}a` / `{\i}` / `{\c{s}}` / U+2010→`-` 等，保证 pdflatex 不炸 |
| 页码 | Elsevier article number 已规范化为单个值 `{112410}`，不再是 `{112410--112410}` |

**编译链**（TeX Live 2025，在 `paper-kbs/tex/journal_20p/` 下执行）：

```bash
pdflatex -interaction=nonstopmode main_20p.tex
bibtex main_20p
pdflatex -interaction=nonstopmode main_20p.tex
pdflatex -interaction=nonstopmode main_20p.tex
```

| 验证项 | 结果 |
|:--|:--|
| 定义条目数 | 70 → **97** |
| 正文唯一引用键 | 64 → **96**（27 条新增 + 5 条孤儿全部落地） |
| 未定义引用 / LaTeX 错误 / >15pt overfull | **0 / 0 / 0** |
| `main_20p.bbl` 生成的 `\bibitem` | **96** 条，27 条新增**逐条核对全部在列表内** |
| `main_20p.pdf` | **20 页 / 4,004,525 B**（整合前 19 页；第二次编译为引用审计修正后） |
| 唯一未引用定义 | `hmrs-demo`（双盲，故意） |
| 第二轮引用一致性审计 | `verify_citation_fix.py` **15/15 PASS**；27 条新增 + 5 条孤儿仍全部引用，零未定义引用 |

BibTeX 仅余 5 条 `Warning--empty pages`（`raptor`、`react-yao`、`selfrag`、
`lightman-verify` 为**原有**；`gallofr2021jkpdesign` 为本次新增）。CEUR-WS
Vol-2978 官方目录不标页码，因此**不编造** `pages` 字段，保留该 warning；
它与既有 4 条同类，不影响输出。`supplementary.tex` 不含 `\bibliography`，
不受本次整合影响。

审计证据链：`notes/audit_citation_evidence.py` → `kbs_abstract_evidence.json`
（29 篇 PDF 摘要）、`bib_titles.json`（97 条题名）、`citation_contexts.json`
（88 个引用点上下文）→ `CITATION-CONSISTENCY-AUDIT-2026-11-14.md`
（逐条判定）→ `verify_citation_fix.py`（修正后约束复核）。

---

## 6. 版本诚实说明（**引用前必读**）

| 版本类型 | 数量 | 说明 |
|:--|:--|:--|
| Elsevier 正式排版（VoR） | 2 | `A_SoftwareRefArch_...2023.pdf`（16 页，含 `Knowledge-Based Systems 276 (2023) 110750` 页眉）、`B_Survey_LLM_KnowledgeBasedMethods_2025.pdf` |
| 明确标注预印本 | 1 | `B_XAI_MetaSurvey_2023.pdf` 首页写 "A PREPRINT" |
| 作者接受稿 / arXiv 版 / 机构库版 | 26 | 首页多为标题直排、无 Elsevier 页眉；内容对应正式文章，但**排版与页码不同** |

因此：**论文里一律用 `kbs_refs.bib` 的 DOI 指向 KBS 正式版，不要引用 PDF 内部页码，也不要把"预印本上的章节编号"写进正文**。如果某条论断必须精确到正式版页码，请先在订阅环境下核对 VoR。这批 PDF 的用途是**读内容、找定位、写 Related Work**，不是页码来源。

---

## 7. 未获取的 8 篇（诚实清单）

| 文献 | DOI | 失败原因 |
|:--|:--|:--|
| TreeQA: logic-tree RAG for multi-hop QA | `10.1016/j.knosys.2025.114526` | OpenAlex / S2 / arXiv / OpenAIRE 均只给出 DOI landing page，无合法 PDF 镜像 |
| Addressing hallucinations via observability + dual-memory KG | `10.1016/j.knosys.2026.115469` | Elsevier OA 全文仅挂在 ScienceDirect；无 arXiv / 机构库镜像 |
| Intermediate triple table (VKG architecture) | `10.1016/j.knosys.2025.113179` | `oa.upm.es` 触发 Anubis bot-check；OpenAIRE 也只指回同一地址 |
| Growing-window semantic chunking for RAG | `10.1016/j.knosys.2025.114896` | 仅 landing page |
| LLM-based harmonized data ingestion for dataspace | `10.1016/j.knosys.2026.115800` | 仅 landing page |
| DamageRAG: benchmark + diagnosis for multi-hop RAG | `10.1016/j.knosys.2026.117231` | 无 OA 文件位置 |
| QueCo: consensus over unverified evidence | `10.1016/j.knosys.2026.116771` | ScienceDirect `/pdf` 403 |
| Generating KG from news via multi-agent claim attribution | `10.1016/j.knosys.2026.116890` | `boa.unimib.it` / `oro.open.ac.uk` 均 403 |

**处理建议**：通过学校图书馆的 ScienceDirect 订阅下载，或直接向作者索取；`https://doi.org/<DOI>` 可直达正式版页面。仅凭摘要**不要**把这 8 篇写进 Related Work 的具体论断——引用它们而不读全文，正是审稿人最容易抓的问题。若确实需要其论点，可先用 DOI 引用并明确说明比较维度来自摘要/公开元数据。

其中前两篇（TreeQA、幻觉治理双记忆）与 HMRS 最贴近，值得优先人工补齐。

---

## 8. 合规说明

全部 PDF 来自**合法开放获取渠道**：arXiv、bioRxiv、CEUR-WS、机构知识库、作者/研究中心托管的 OA 副本（如 MediaFutures 的 `mediafutures.no/1-s2-0-s0950705123005002-main/`，901 kB，与 NVA 登记的 "Published version / Open / 901 kB" 一致）。**没有**绕过 ScienceDirect 403、Elsevier API 406 或机构库 Anubis 反爬验证；遇到阻拦一律记为 MISS 并停止尝试。下载脚本的候选 URL 解析顺序、失败原因均完整保存在 `kbs_download_manifest.json`，可逐条复核。
