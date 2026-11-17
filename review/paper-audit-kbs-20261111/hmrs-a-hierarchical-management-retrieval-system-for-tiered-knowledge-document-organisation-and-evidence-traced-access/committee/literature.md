# Committee Reviewer 3 — Literature Dialogue Review (HMRS, KBS submission)

审阅范围：文献对话质量（离线审阅，未做在线检索）。依据 `n2_related.tex`、`n1_intro.tex`、`refs.bib` + `refs_new_verified.bib`，并交叉核对 `n3/n6/n8a/n8b/n8c/n9` 的 `\cite` 使用。

**文献质量评分：7 / 10**

**综合式 vs 罗列式判定**：总体属于**综合式（synthesis-oriented）**。Related work 按"知识管理→检索与agentic搜索→验证与弃答"三条主题线组织，每段结尾都有定位句（如 "HMRS treats acquisition quality, automatic classification and traceable indexing as prerequisites for reliable retrieval rather than as preprocessing assumptions"），并配有定位表（每行分"optimises / leaves to deployment"两列），这是真正的对话结构而非论文堆叠。扣分点在于：个别段落退化为引用簇压缩（一条子句挂四篇文献），以及最重要的近邻工作（DeepRead）只有单句带过、未做正面对比（见下）。

**Gap 真实性判定**：本文的 gap 陈述罕见地诚实——它不宣称"前人没有做 X"，而是明确把贡献定位为集成与角色分离："Prior work already studies selective question answering, citation verifiability and retrieval correction; the distinction here is not that abstention or evidence checks are absent from prior research. The gap this study addresses is one of integration and of role separation rather than of missing capabilities."（n2, Sec. 2.4），并以 "It proposes no new ranking algorithm and does not claim that the underlying retrieval problem is solved" 收尾。这种自我限定的 gap 推导方式基本经得起 closest-prior-work 检验。但 gap 的**前提**仍有两处被引用选择性削弱的疑点（见 Straw-Man 小节第 1、2 条），且三条与核心主张直接相关的文献线索在参考文献中完全缺席（见 Missing 段），需靠 `--literature-search` 证实或排除。

## Literature Dialogue Review

### Gap Derivation Audit

- Claimed gap (quote + location):
  - n2, Sec. 2.4（\label{sec:gap}）："The gap this study addresses is one of integration and of role separation rather than of missing capabilities."
  - n2："HMRS differs in what the hierarchy governs. Its hierarchy is a management structure over collections and documents…whereas a retrieval-time hierarchy is an index over content that is usually produced once and left unchanged."
  - n1, Sec. 1："The question we study is therefore not how to rank passages better, but how a document collection should be *managed* so that a query can be served tier by tier."
- Why the gap is (not) logically established:
  - **成立的部分**：作者主动否定弱命题（"the distinction here is not that abstention or evidence checks are absent from prior research"），把 Table 1（positioning）明确定位为 "compares representative strands rather than every system in the literature"，并用 "What it leaves to the deployment" 列给每条文献线索留出真实的剩余问题。gap 由"集成/角色分离"承担，而集成类贡献在文中确有对应证据（E2 生命周期、E4 判分角色分解、E5b 传输失败），逻辑闭环成立。
  - **不成立/受削弱的部分**：
    1. 前提句 "research has largely treated them separately"（n1）与作者自己引用的 modular-rag（ACM TOIS 2026, "Transforming RAG Systems into LEGO-like Reconfigurable Frameworks"）和 gao-ragsurvey 相互抵触——这两篇综述恰恰把数据摄取/索引（data indexing、pre-retrieval）当作 RAG 的一等模块来讨论。定位表给 Retrieval 线索的刻画 "Rank quality over a corpus that is assumed indexed" 把这一矛盾抹平了：按作者自己的引用，索引并非"assumed"。全文从未正面回应这一张力。
    2. 与 RAPTOR/GraphRAG 的区分依赖一个无引用支持的断言："a retrieval-time hierarchy is an index over content that is usually produced once and left unchanged"。这是对被比较对象的**性质刻画**，没有任何文献佐证（RAPTOR/GraphRAG 原文是否"produced once and left unchanged"需要证据），而它恰是 HMRS 差异化主张（"written to and reconciled after every lifecycle operation"）的支点。
    3. 最接近的先行工作 DeepRead 只得到一句 "DeepRead demonstrates structure-aware navigation for agentic search \citep{deepread}; HMRS similarly exposes a catalogue-first librarian lane…"，随后在定位表中被归入 "Agentic tool use" 行，其"optimises"栏写的是 "Access to retrieval tools behind a stable interface"。DeepRead 的实际贡献（文档结构感知的 agentic 检索推理）与 HMRS 的 shelf/document 层导航高度重叠，把它压平成"稳定接口背后的工具访问"是对近邻工作的最坏刻画（straw-man 风险），gap 未在最强对手身上做过检验。
    4. 参考文献中完全没有"集合选择/资源路由"文献线（federated/distributed IR 的 resource selection 传统），而 n1 的核心动机句恰是 "the first decision a question requires---which collection should be consulted---is made without consulting the collection structure at all"——这是一个对未引用文献线的全称否定式断言，gap 有被选择性引用制造出来的风险。

### Pseudo-Innovation / Straw-Man Signals

1. **DeepRead 被压平（最主要信号）**：定位表 "Agentic tool use | ReAct, MCP, DeepRead | Access to retrieval tools behind a stable interface"。同段对 GraphRAG/LightRAG/RAPTOR 各有一句准确刻画并随后做了对比（"Hierarchical representation is therefore already an established retrieval concern…"），DeepRead 却只作为"similarly"的类比对象出现，没有"它不做/HMRS 多做什么"的对比句。最近的先行工作应获得与 RAPTOR 同等的正面剖析。
2. **"assumed indexed" 与 "largely treated them separately" 的抹平**：如上，作者引用的 modular-rag/gao-ragsurvey 已把摄取与索引纳入 RAG 管线研究，定位表却把整条 Retrieval 线索刻画为"假设已索引"。这一矛盾未被 reconcile，属于用引用簇掩盖反例的选择性引用。
3. **无引用支持的性质断言**："usually produced once and left unchanged"（指向 RAPTOR/GraphRAG 一类系统）无出处；同理 "Public knowledge bases organise facts under explicit ontologies…whereas enterprise content management emphasises governance" 的二分铺垫尚可，但 Nonaka SECI（1994/2000）两句之后直接跳到 "These strands motivate reliable placement and governance, but do not by themselves connect those controls to evidence-checked answers"——"do not by themselves" 的否定是安全的（作者限定了范围），此处不算 straw man。
4. **评估章节中的"权威背书式"引用**（不属于 straw man，但属于对话质量问题）：n8a 用 W3C PROV 综述支撑自己管线无法归因的事实（"so the 21 cannot be attributed to parsing alone \cite{missier-prov-2013}"）；n8a 用 metadata 质量综述为系统自身的描述核查背书（"Descriptions and tags are checked against content before storage~\cite{park-metadata-quality-2009}"）；n8c E6 把四篇 judge 可靠性文献挂在一个关于**本文自身**跨语料对比的谨慎限定句上（"the cross-corpus pattern is descriptive, not causal \cite{zheng-llmjudge,panickssery-selfpref,lightman-verify,yin-knowwhat}"）；n8c E5 用 agentic RAG 综述支撑延迟构成观察（"consistent with model turns dominating latency \cite{singh-agentic-rag}"）。单条均可辩解，但合起来形成"用文献给自身观察加权威"的模式。
5. **值得表扬的诚实信号**：gap 一节主动写明 "not a universal claim that earlier systems lack reusable verification or inspectable evidence"；对图检索的负面结果也如实报告（"graph search…is the weakest standalone signal"）。这些使 pseudo-innovation 风险显著低于同类系统论文。

### Citation-Usage Issues（带精确引文）

见配套 `artifacts/comments/committee_literature.json`（12 条）。要点摘录：

- **\cite{graphrag} 错位**（n8b, E4）："graph search \cite{graphrag}, limited to node-name and tag matching, is the weakest standalone signal."。该句描述的是系统自己的 `kb_graph_search`（n8b 定义为 "a keyword match over node names, paths and tags in the document graph"），与 n2 自己对 GraphRAG 的刻画（"adds entity-relation graphs and community summaries"）完全不同。把 GraphRAG 的引用挂在自家弱工具的结果句上，会让读者误以为被评测的是 GraphRAG 类方法。应改为引用自身实现（Neo4j 图谱的构建描述）或明确 "(cf.)"。
- **hmrs-demo 条目作者为占位符**（refs.bib）："%% AUTHOR ACTION: fill real author list before submission." / "author = {Author Name}"。先行演示版是本文的基线引用，条目本身尚未可投。
- **laya 仅以模型卡为据**（n6）：'The gate is the local Laya evidence classifier \cite{laya}, exposed as \path{kb_laya_judge}. ' 核心验证器（E4–E6 的主角）唯一出处是 HuggingFace 模型卡，而 related work 2.3 节引用的 judge 可靠性文献（zheng-llmjudge、panickssery-selfpref 等）从未被用来反观这一具体选择——文献对话在这里断开：E6 的失败发现恰恰印证了 2.3 节的警告，但正文没有把这层呼应写出来。
- **\cite{siren,gao-ragsurvey} 支撑力偏弱**（n1）："Semantic similarity measures topical relatedness, not whether a passage contains evidence for the requested claim \cite{siren,gao-ragsurvey}."。两篇均为综述，支持"幻觉/RAG 失败"大命题，但不直接支撑"相似度≠证据"这一概念区分本身。
- **cyberbot 代表性偏薄**（n2）："Other work studies selective prediction under domain shift, ontology-grounded retrieval and citation verification \citep{kamath,cyberbot,liu-verifiability,gao-citations}."。用一篇 CIKM'25 五页短文（poster 级，pp. 6752–6756）作为"ontology-grounded retrieval"线索的代表，为期刊级 gap 定位作支撑，分量不足。
- **\cite{craswell-msmarco-2021} 与 \cite{jarvelin-cumulated-gain-2002} 的度量出处引用是恰当的**（n8a：Hit@5/MRR@5 溯源 MS MARCO passage-ranking 惯例、nDCG 溯源 Järvelin & Kekäläinen）；bib 35+23 条中**无孤儿条目、无重复条目**（refs_new_verified 头部记录了 hnsw 去重、sun-urara/rankgpt 合并），条目级卫生状况良好——本次问题集中在**使用层**而非条目层。

### Missing Citation Strands（离线限制说明）

以下三条文献线在两份 bib 中均无任何条目，而它们与论文的三处核心主张直接相邻。按审阅规程不做在线检索、不点名具体论文，建议启用 `--literature-search` 验证：

1. **集合/资源选择（federated IR 的 resource selection 传统）**——对应主张："the first decision a question requires---which collection should be consulted---is made without consulting the collection structure at all"（n1）。若该传统已有"先选库再检索"的成熟工作，gap 第 4 点的全称断言需要改写。
2. **文本分块/结构切分**——对应机制："a document is split at recognised structural markers and its parts are indexed for dense and lexical search"（n3）及 30,000 字符切分档位。RAG 系统论文通常需引用切分策略文献来定位自己的切分选择。
3. **索引维护/增量更新**——对应差异化主张 "written to and reconciled after every lifecycle operation"（n2）与 E2 的重命名-索引失步缺陷发现（"a stale-index rename defect that only forced re-indexing corrected"，n9）。HMRS 的关键区分轴恰恰落在一个未被引用的文献线上，目前"通常一次性生成、之后不再更新"的说法无文献支撑也无对照。

### Fix Plan (3 concrete edits)

1. **给 DeepRead 一个正面段落**（n2, Sec. 2.2）：仿照 RAPTOR/GraphRAG 的三句式（它做什么→它与 HMRS 的层级差异→剩余问题），并修正定位表 "Agentic tool use" 行的 "What it optimises" 列，使 DeepRead 的刻画不与 ReAct/MCP 的"接口稳定性"混为一谈。
2. **reconcile "separately treated" 前提**（n1 第 2 段 + 定位表 Retrieval 行）：明确承认 modular-rag/gao-ragsurvey 已把摄取/索引作为 RAG 模块研究，把本文的集成点收窄到"集合生命周期治理（move/rename/delete/re-index 后的三源对账）不在这些模块的覆盖范围"，并删除或加注 "assumed indexed" 的全称刻画。
3. **清理使用层引用**：将 n8b 中 "graph search \cite{graphrag}…" 的 graphrag 改为系统实现出处（或 "(cf.~\cite{graphrag})"）；为 "usually produced once and left unchanged" 补充对照性引用或弱化为限定句；落实 refs.bib 中 hmrs-demo 的真实作者名单（AUTHOR ACTION 注释当前仍在）；将 E6/E5 的四篇背书式引用移至与文献主张直接对应的句子（judge 可靠性警告处），或删除。

---

*评分理由：主题式组织 + 诚实 gap 陈述 + 干净的条目卫生（近满分的下半段），被三个使用层问题拉低：近邻工作 DeepRead 压平、"separately treated" 前提与自引综述的未调和矛盾、三条核心相邻文献线完全缺席（federated-IR 资源选择、分块、索引维护）。综合 7/10：良好的对话骨架，gap 推导在最强对手面前尚需一次加固。*
