# KBS 文献包：论文解读、核心图定位与绘图风格分析

日期：2026-11-14 ｜ 项目：`rag-knowledge` ｜ 目的：回答「下载的 KBS 文章在哪、与 RAG 系统相关的几篇讲了什么、核心架构图/流程图长什么样、KBS 绘图风格如何」

---

## 1. 文献下载位置与产物清单

| 项 | 路径 / 值 | 说明 |
|---|---|---|
| PDF 目录 | `paper-kbs/reference/kbs/` | **29 篇 PDF，约 60 MB**，全部通过 `%PDF` 头、≥30 KB、pypdf 首页文本三重校验 |
| 文献包 BibTeX | `paper-kbs/reference/kbs/kbs_refs.bib` | 29 entries，含 `note = {OA PDF: ...}` 本地路径 |
| 阅读指南 | `paper-kbs/reference/kbs/README.md` | 筛选漏斗、精读建议、分组索引、合规说明 |
| **本次画廊（主交付）** | `paper-kbs/reference/kbs/FIGURE-GALLERY.html` | 20 张精选图，按 4 组分类，可点击放大、可跳整页排版 |
| 导出图页 | `paper-kbs/reference/kbs/figures/*.png` | **88 张 PNG，26 MB**；`__pNN.png` = 整页 144 dpi，`__pNN_crop.png` = 图区裁剪 216 dpi |
| 全量图索引 | `paper-kbs/notes/kbs_all_figure_index.json` | 29 篇逐页图注 + 图像/矢量对象密度 |
| 精选渲染报告 | `paper-kbs/notes/kbs_selected_figures.json` | 28 页渲染清单 |
| 图注全集 | `paper-kbs/notes/kbs_all_figure_captions.json` | 补抓脚本产出的 4 篇完整图注 |
| 校验结果 | `paper-kbs/notes/figure_gallery_verify.json` | 7/7 PASS |

**渲染工具链（本机实测）**：`backend/.venv/Scripts/python.exe` 缺 `fitz/pymupdf/pdf2image`；可用解释器是 `D:\anaconda3\python.exe`（PyMuPDF 1.28.2）。TeX Live 也提供 `pdftoppm`/`pdfimages`，本次未用。

**取证脚本链**（全部留在 `paper-kbs/notes/`，可复现）：

```
scan_all_kbs_figures.py       29 篇全量扫描：图注行 + 每页 image/drawing 计数
        ↓
render_selected_kbs_figures.py  28 页精选渲染 + 图形 bbox 并集裁剪
        ↓
refine_kbs_crops.py          5 张按实测 bbox / 图注 y0 精修（去掉混入的正文）
        ↓
ViewImage 逐张视觉核对（20+ 张）
        ↓
FIGURE-GALLERY.html + verify_figure_gallery.py (7/7 PASS)
```

---

## 2. 与「RAG / 知识库系统」最相关的论文：讲了什么

以下解读基于 PDF **真实摘要文本**（`paper-kbs/notes/kbs_abstract_evidence.json` + 对 4 篇 Elsevier 双栏稿补读的 `a b s t r a c t` 段）与图注原文，不是凭题名推测。

| # | 论文（文件短名） | 年份 | 真实摘要要点 | 与 HMRS 的关系 |
|---|---|---|---|---|
| 1 | `A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023` | KBS 276 (2023) 110750 | 新闻机构用了大量 AI/大数据/知识系统却难协同；用设计科学研究提出统一的「新闻知识平台」软件参考架构 SRA，把最佳实践固化为通用蓝图，并用 ArchiMate 3.1 表示、做原型实例化 | **最像**：同样是「知识库平台 + 按内容组织 + 分层组件」，不是单篇检索算法 |
| 2 | `B_KnowledgeRetrieval_InContextLearning_SemanticSearch_2025` | KBS 2025 | 通用 LLM 回答领域文档不准、微调成本高；用文档分块 → embeddings → ChromaDB → prompt context → LLM 免训练地做领域问答，支持任意语言查询与回译 | **最直接对标**：纯向量召回路线，正好衬托 HMRS 的「内容 Rubric 覆盖向量分数」 |
| 3 | `B_RAG_EngineeringDesignKnowledge_2024` | KBS 303 (2024) 112410 | 从专利描述抽取显式事实 `{head :: relation :: tail}`，37.5 万训练样本，在 4,870 项风扇专利上灌出 293 万条事实知识库，用显式事实引导 LLM | 同样主张「语料必须先被组织成显式知识」，可支持 Organize-then-Retrieve 的动机段 |
| 4 | `B_FinBloom_KnowledgeGrounding_RealtimeData_2026` | KBS 2026 | LLM 难处理需实时信息的金融问题；构建 5 万+ 查询的 Financial Context Dataset，让 Agent 从 News/Tabular 数据模块抽取实时上下文再交给 LLM | 「上下文接地 / 结构化数据模块」与 HMRS 五层模型对照 |
| 5 | `A_Automating_EngineeringModeling_LLM_Agents_2026` | KBS 2026 | 传统数据驱动建模需大量人工、难扩展；用 LLM 智能体流水线自动完成建模、脚本生成、执行与调参，含失败 debug→patch→重跑 | 与 SOUL / Agent 编排、MCP 工具调用链最像 |
| 6 | `A_Coordinated_LLM_MultiAgent_QA_2025` | KBS 2025 | LLM 在专业领域 QA 上下文召回低、事实不一致；CIR3 用 Classifier/Moderator/多 Writer/评审 Agent 多轮反思精炼直到收敛 | 「评审-反馈-收敛」闭环与经验生命周期 E0–E12 呼应 |
| 7 | `A_HELIOT_LLM_CDSS_2025` | KBS 2025 | 现有 CDSS 依赖静态库与规则、告警疲劳；HELIOT 用 LLM 处理自由文本临床信息做不良反应管理 | 规范的系统架构图 + 数据流水线成对出现，画法范本 |
| 8 | `A_LLM_IR_System_BankSupervisors_2024` | KBS 2024 | 银行监管者需让新措施与历史先例一致；系统摄取 findings，混合 lexical/semantic/CRR 特征检索历史措施 | 检索系统 + 验证方法论都有图，可借鉴评测章节 |
| 9 | `B_PrivateLibrary_CodeGeneration_LLM_2025` | KBS 2025 | LLM 没见过私有库 API；模拟程序员查文档写私有代码，拆成 APIFinder + APICoder 两级 | 与「Agent 原生工具接口」叙事接近 |
| 10 | `B_LGMT_ReasoningReliability_Testing_2026` | KBS 2026 | 静态 benchmark 高估 LLM 逻辑推理；用一阶逻辑等价导出蜕变关系做 oracle-free 缺陷检测 | 与本项目「诚实弃答 / 应拒答」的可信性评测同一脉络 |
| 11 | `B_Survey_LLM_KnowledgeBasedMethods_2025` | KBS 2025 | 综述 LLM 与结构化知识库的结合、实践应用及技术/运营/伦理挑战 | Related Work 的框架图来源 |
| 12 | `B_QueryExpansion_SemanticRelations_RetrievalSystems_2023` | KBS 2023 | 用分类法标签生成语义资源（同义/反义），接入分类器把 query 重述为 intent 并跟踪每种关系影响 | 算法级流程图的画法范本 |
| 13 | `B_InformationTheoretic_DualMemory_System_2025` | KBS 2025 | 持续学习中单记忆缓冲受限；提出 fast/slow 双记忆 + 信息论样本选择 | 高信息密度训练流程图的画法范本 |
| 14 | `A_GOFAI_Meets_GenerativeAI_ExpertSystems_2026` | KBS 2026 | LLM 幻觉/不可验证；限定领域 + 结构化 prompt 抽取生成符号化知识表示，可控透明地建专家系统 | 风格反例（手写体涂鸦） |
| 15 | `A_COMPANION_..._CEUR2021` | CEUR-WS 2021 | 2023 KBS 正式版的 workshop 前驱，已提出 JKP 需要软件参考架构 | 仅用于对比图演进，非 KBS 正式排版 |

> 说明：`A_KG_Orchestra_..._2026.pdf` 虽被下载（bioRxiv 预印本，62 页），但**正文中没有任何嵌入图形对象**（`get_image_info` / `get_drawings` 在 p1–p50 全为 0），图形集中在 p52–p62 附录，故不作为 KBS 绘图风格样本。

---

## 3. 核心架构图与执行流程图：精确定位

页码为 PDF 物理页码，`_crop.png` 为画廊中展示的图区裁剪。

### 3.1 架构设计图

| 论文 | 图号 / 页 | 原文图注 | 图型 | 裁剪文件（`figures/` 下） |
|---|---|---|---|---|
| Journalistic KP | Fig.3 / p08 | *The SRA for JKPs (represented with ArchiMate 3.1 notation).* | ArchiMate 组件-连接图，中心 Knowledge Base | `A_SoftwareRefArch_..._2023__p08_crop.png` |
| Journalistic KP | Fig.4 / p11 | *The instantiated architecture for the JKP prototype.* | 原型实例化 + 真实组件 logo | `...__p11_crop.png` |
| Journalistic KP | Fig.2 / p07 | *High-level view of the architecture.* | 单栏高层中心辐射图 | `...__p07_crop.png` |
| HELIOT | Fig.4 / p06 | *HELIOT CDSS Architecture.* | C4/UML 组件图 + 系统边界 | `A_HELIOT_LLM_CDSS_2025__p06_crop.png` |
| LLM Agents | Fig.2 / p09 | *Supervisor-centric architecture of the multi-agent system.* | 角色关系图 | `A_Automating_..._2026__p09_crop.png` |
| GTR | Fig.1 / p04 | *Methodology overview for GTR showing our embedding-based retrieval system using document chunking.* | RAG 双泳道 pipeline | `B_KnowledgeRetrieval_..._2025__p04_crop.png` |
| LGMT | Fig.3 / p05 | *Overview of the LGMT Framework.* | 四阶段卡片总览 | `B_LGMT_..._2026__p05_crop.png` |
| Survey | Fig.1 / p02 | *Overall structure of the paper organization.* | 三列分类树 | `B_Survey_..._2025__p02_crop.png` |
| APIFinder | Fig.4 / p05 | *Schematic diagram of our framework: APIFinder.* | 图标化双模型数据流 | `B_PrivateLibrary_..._2025__p05_crop.png` |
| COMPANION | Fig.1 / p04 | *The SRA for JKPs (ArchiMate 3.1 notation).* | LNCS 单栏前驱稿 | `A_COMPANION_..._CEUR2021__p04_crop.png` |

### 3.2 执行 / 数据流程图

| 论文 | 图号 / 页 | 原文图注 | 图型 | 裁剪文件 |
|---|---|---|---|---|
| LLM Agents | Fig.4 / p21 | *Workflow of the multi-agent system illustrating the handling of a code execution error.* | **UML 时序图**（6 生命线、实线请求/虚线返回、debug→patch→re-execute） | `A_Automating_..._2026__p21_crop.png` |
| CIR3 | Fig.1 / p10 | *CIR3 takes an input document (1) ... returns the final QAs (7).* | 编号 ①–⑦ + 判定菱形 + `<K`/`<L` 反馈回路 | `A_Coordinated_..._2025__p10_crop.png` |
| QueryExpansion | Fig.8 / p10 | *Main flowchart of the approach.* | 彩色算法流程图（5 菱形、TP/FP/TN/FN 出口） | `B_QueryExpansion_..._2023__p10_crop.png` |
| HELIOT | Fig.5 / p07 | *Overview of the Pharmaceutical Data Pipeline Process.* | ①②③ chevron 阶段带 + 数据/数据库形状 | `A_HELIOT_LLM_CDSS_2025__p07_crop.png` |
| DualMemory | Fig.1 / p09 | *The training procedure for the proposed dual memory system...* | 公式 + 黄色决策菱形 + 浅蓝子流程分区 | `B_InformationTheoretic_..._2025__p09_crop.png` |
| Bank IR | Fig.4 / p16 | *Birdview of the validation methodology.* | 集合符号流程树 + 虚线 `Repeat M times` 域 | `A_LLM_IR_..._2024__p16_crop.png` |
| RAG Design | Fig.4 / p09 | *Scenarios for usage of LLMs in the design process, including RAG.* | 黑白图标 + 3 种线型图例 | `B_RAG_EngineeringDesignKnowledge_2024__p09_crop.png` |
| FinBloom | Fig.6 / p19 | *Work flow and interoperability of the modules.* | 极简 5 步黑白流程 | `B_FinBloom_..._2026__p19_crop.png` |
| Journalistic KP | Fig.1 / p03 | *Construction process of the SRA for JKPs.* | 6 步方法论线性流程 | `A_SoftwareRefArch_..._2023__p03_crop.png` |
| GOFAI | Fig.3 / p09 | *Diagram flow with all the processes involved in the creation of the expert system.* | 手写体涂鸦（反例） | `A_GOFAI_..._2026__p09_crop.png` |

---

## 4. KBS 绘图风格：8 条规律（每条有图证）

| # | 规律 | 直接证据 |
|---|---|---|
| 1 | 用标准建模语言而非自由方框 | Journalistic KP Fig.3 图注直接写 ArchiMate 3.1；HELIOT Fig.4 写 `[Component: FastAPI]`、`[Container: TileDB]`、`[Software System] GPT-4 API` |
| 2 | 大虚线框 = 系统边界 / 泳道 | GTR 两个虚线框分 USER INPUT / MODEL FRAMEWORK；HELIOT 把 GPT-4 API 放在系统虚线框外 |
| 3 | 中心化布局，知识库居中 | Journalistic KP Fig.2/3：Knowledge Base 居中，Ingestor / Feeder / Retriever / Learner / Curator 环绕 |
| 4 | 箭头带语义标签 + 线型区分 | ArchiMate 图例：实线 Trigger direction / 虚线 Information flow；HELIOT 箭头写 `Makes API calls [JSON/HTTP]`；Supervisor 实线下发、虚线回传 |
| 5 | 配色克制：单色系 + 少量语义强调色 | ArchiMate 全篇青色；HELIOT 蓝+深蓝+灰；FinBloom 全灰阶；彩色只用于编码（GTR 红/蓝/黄/绿 = query/stored/retrieved vectors） |
| 6 | 流程靠编号、判定菱形与显式回路 | CIR3 ①–⑦ + `<K`/`<L`；QueryExpansion 5 菱形；DualMemory 黄色 `b < b*` 菱形 |
| 7 | 跨栏大图放主架构，单栏小图放概览 | 实测 bbox：Journalistic KP Fig.2 仅 `(369,560)-(495,695)` 是右栏小图；ArchiMate 主图占满页宽 |
| 8 | 图注写成小摘要 | CIR3 图注 5 行逐步解释 (1)–(7)；GTR 图注点明 `using document chunking` |

**反例与不适用样本**：`A_GOFAI` 手写体 + 曲线箭头 + 无图例（虽已发表但读图成本高）；`A_Practical_PrivacyPreserving_Framework_LLM_Services_2026` 有 23 个图注但全部是通信耗时/请求大小柱状对比，无一张架构图；`A_KG_Orchestra` 正文无图；`A_COMPANION` 是 LNCS 单栏而非 KBS 双栏。

---

## 5. 对 HMRS 论文画图的可执行建议

| 级别 | 动作 | 依据与落地方式 |
|---|---|---|
| **P0** | 主架构图改用 ArchiMate 或 C4 组件图 | 参照 Journalistic KP Fig.3 / HELIOT Fig.4：五层数据模型 L1–L5 各自画成组件框、框内列子组件、框上标 `[Component]`/`[Container]`，虚线大框圈出系统边界，把 embedding / LLM 外部服务放框外。系统类期刊评审更认这套 |
| **P0** | 补一张带编号的 QDCVR 执行流程图 | 参照 CIR3 Fig.1 / Supervisor 时序图：路由 → 召回 → 内容 Rubric 裁决 → `c≤4` 丢弃 / `c=5` fallback + librarian escalation / `c≥6` 采用 → not-found report，画成 ①–⑦ + 判定菱形 + 反馈回路。**当前稿件缺的正是「系统怎么跑一遍」这张图** |
| **P0** | 每张图配线型图例 + 箭头语义标签 | HMRS 的「写走 HTTP API / 读直连文件与索引」是两条完全不同的通道，必须靠实线/虚线 + 标签区分，否则读者会误读为同一条数据总线 |
| **P1** | 主图跨双栏、辅助概览图单栏 | 按实测坐标，复杂架构放页面上部占满 textwidth；避免硬塞单栏导致字号 < 8pt |
| **P1** | 统一单色系 + 1 个强调色 | 建议青/蓝（与 ArchiMate、HELIOT 一致），仅用一种强调色标「内容裁决」这一创新点；颜色用于编码语义，不用于装饰 |
| **P1** | 图注写成小摘要 | 像 CIR3 那样在图注里逐条解释编号步骤与判定条件，而不是 `Overview of our system` |
| **P1** | 加一张原型实例化图 | Journalistic KP Fig.4 用 DBpedia / Wikidata / Docker 真实 logo 证明可落地；HMRS 可放 ChromaDB、Neo4j、BGE-M3、MCP 等真实组件标识，强化 KBS 系统论文看重的「真的实现了」 |
| **P1** | 评测章节单独一张验证方法流程图 | 参照 Bank IR Fig.4 与 LGMT Fig.3，把 2×2 析因 / A2 对照轨 / 三层评分画成阶段图，而不是只放表格 |
| **P2** | 避免手写体、曲线箭头、无图例涂鸦 | 见 GOFAI 反例 |
| **P2** | 避免把彩色卡片堆叠用于组件架构 | LGMT 式卡片适合「框架总览」，不适合表达组件连接关系 |
| **P2** | 避免把实验结果图当架构图 | 见 PrivacyPreserving 框架的 23 张柱状图 |

---

## 6. 诚实边界与未完成项

1. **本次只做解读与出图，未改动投稿正本**：`paper-kbs/tex/journal_20p/*` 与 `main_20p.pdf` 均未触碰，也没有 commit/push（用户本轮未要求）。
2. **裁剪脚本是启发式的**：以图形 bbox 并集为界，5 张因混入正文已按实测坐标精修；`A_SoftwareRefArch__p11_crop.png` 右缘仍带少量相邻栏文字，主体完整。
3. **3 类样本非 KBS 正式排版**：CEUR companion、bioRxiv 预印本、以及已发表但低规范的 GOFAI 手写图；画廊已用徽章标注。
4. **文献包 8 篇 MISS 仍未获取**（ScienceDirect 403 / 机构库反爬），与本次找图任务无关，详见 `paper-kbs/reference/kbs/README.md` 第 7 节。
5. **3 篇既有 KBS 引用**（`li-kbs-rmrsst-2026`、`shen-kbs-teierag-2026`、`kinalioglu-kbs-eprag-2026`）只有题名/元数据，无全文 PDF，不在本画廊内。
6. 主工作区仍有大量未提交改动；本地分支落后远程，沿用此前「隔离 worktree 推送」策略如需提交。
