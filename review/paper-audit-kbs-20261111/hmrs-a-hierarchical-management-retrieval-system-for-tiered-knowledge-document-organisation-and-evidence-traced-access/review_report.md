# Deep Review Report

**Paper**: `D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\main_20p.tex` | **Language**: EN | **Mode**: deep-review
**Generated**: 2026-11-11 13:26
**Artifacts**: `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\paper-audit-kbs-20261111\hmrs-a-hierarchical-management-retrieval-system-for-tiered-knowledge-document-organisation-and-evidence-traced-access`

## Overall Assessment

Deep review found 1 major, 0 moderate, 0 minor issues. The highest-priority concerns are: Abstract and conclusion claims need explicit evidence traceability.

- **Major**: 15
- **Moderate**: 31
- **Minor**: 20

## Academic Pre-Review Committee

### Editor (Desk Reject Screen)

## Editor Pre-Screen (1-10)

Score: 4.0/10
Verdict: Desk Reject

### Desk-Reject Triggers (if any)
- Abstract and conclusion claims need explicit evidence traceability

### Top 3 Reasons (no hedging)
1. Abstract and conclusion claims need explicit evidence traceability

### Fast Fixes (within 1-2 days)
- Clarify abstract to address abstract and conclusion claims need explicit evidence traceability.

### Reviewer 1 (Theory Contribution)

## Theory Contribution Review

### 3 Fatal Theory Holes
1. (abstract) "These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support." — At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

### Concrete Moves
- Tighten the paper's theoretical positioning in abstract to resolve abstract and conclusion claims need explicit evidence traceability.

### Reviewer 3 (Literature Dialogue)

## Literature Dialogue Review

### Closest Prior Work Risks
- No literature-grounding risk was surfaced by the fallback pass.

### Gap Claim Risks
- No selective-citation concern was surfaced.

### Fast Fixes
- Add one sentence identifying the closest prior work and the exact novelty delta.

### Reviewer 2 (Methodology & Transparency)

## Methodology Transparency Review (SRQR-aware)

### MUST-FIX (submission blockers)
- No methodology blocker was surfaced by the fallback pass.

### SHOULD-FIX (quality improvements)
- No secondary methodology issue was surfaced.

### SRQR Checklist Deltas
- Sampling rationale: clarify how the evidence base supports the paper's strongest claims.
- Data collection details (time/place/duration): add context when results depend on specific settings.
- Coding process (stages, coders, disagreement resolution): specify if qualitative or hybrid analysis is used.
- Saturation: state whether the evidence scope is exhaustive or bounded.
- Triangulation: explain whether multiple evidence sources were reconciled.
- Reflexivity: acknowledge researcher choices that shape interpretation.

### Reviewer 4 (Logic Chain)

## Logic Chain Review

### Breakpoints
- (abstract) "These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support." — At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

### Structural Fix Moves
- Add one explicit bridge sentence in abstract so the argument chain closes cleanly.

### Committee Consensus

## Committee Consensus

Overall Score: 4.0/10
Editor Verdict: Desk Reject

### Score Formula
- base 9.0
- minus 1.5 * major (1)
- minus 0.7 * moderate (0)
- minus 0.2 * minor (0)
- floor 1.0
- desk reject cap 4.0

### Top 3 Issues To Fix First
1. Abstract and conclusion claims need explicit evidence traceability

## Paper Summary

# Paper Summary: HMRS: A hierarchical management retrieval system for tiered knowledge document organisation and evidence-traced access

## Research Question
- A document collection becomes a knowledge base only when its documents are parsed, classified into the owning collection, kept consistent as it changes, and searched there

## Core Thesis
- We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and answers along a tiered path narrowing from the catalogue of collections, through document descriptions, to the segment carrying the evidence.

## Headline Claims
- We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and answers along a tiered path narrowing from the catalogue of collections, through document descriptions, to the segment carrying the evidence.

## Section Map
- abstract (88-112): 248 words

## Closure Targets
- No closure target was extracted automatically.

## Major Issues

### M1: 管理主张所依赖的头对头对照（A0h vs PD）不显著，核心架构论点无阳性证据支撑
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: evaluation/E2c (n8a_eval.tex)
- **Related Sections**: evaluation/E2c (n8a_eval.tex), intro/contributions, evaluation/E2b routing-audit, evaluation/E8
- **Root Cause Key**: `management-claim-rests-on-nonsignificant-contrast`
- **Quote Verified**: yes
- **Quote**: `The head-to-head contrast is the one the management claim rests on: A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample.`
- **Explanation**: 作者亲口承认分层导航对放弃导航（precise/flat）的对照是管理贡献所系的关键检验，而该检验 p=0.0703 不达显著。叠加路由审计的混杂（脚本探针且 fallback 未记录，'This was a scripted route-card probe, not an LLM agent selecting a library.'）与 E8 中不限库检索与钉死金库结果相同的事实，论文的核心命题——决定查询哪个 collection 的管理层带来可测收益——在其自身证据中从未被正面确立。引言仍宣称 'The contribution claimed here is the management structure that decides which collection is consulted, not a new ranking function.'，即贡献陈述与证据状态不匹配：边界声明诚实，但贡献清单仍然把未确立的命题作为核心贡献出售。应重跑具备足够样本量的三臂对照或把贡献降格为系统+审计报告。

### M2: 集成价值缺少任何阳性测量：旗舰混合配置输给纯词法基线，层级机制在自家数据中零正向贡献
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: evaluation/E4 (n8b_eval.tex)
- **Related Sections**: evaluation/E4 (n8b_eval.tex), related/gap, evaluation/E8, evaluation/E2c
- **Root Cause Key**: `integration-contribution-lacks-positive-measurement`
- **Quote Verified**: yes
- **Quote**: `Nothing here is a retrieval advance: three configurations tie at Hit@5 1.00, and the one using only words leads on MRR.`
- **Explanation**: 论文把贡献定位为集成（'The gap this study addresses is one of integration and of role separation rather than of missing capabilities.'），而集成类贡献必须展示组合产生的可测收益。但评估显示：工业语料上 BM25 Hit@5 1.00 vs HMRS-Hybrid 0.44（旗舰配置是九配置中最弱者）；E8 唯一触及 scope 价值的消融中 'searched the 20 live libraries, including 15 outside the five-library evaluation corpus, and matches the gold-pinned result in this ten-question setup'（限定正确库相对不限库无可测收益）；E2c 阶梯对照不显著。三处合观，管理/分层结构在论文自己的测量里没有产生一次可检出的正向贡献，集成为贡献的命题停留在架构描述层面。这是声称贡献与交付内容的核心错位。

### M3: 引言贡献第4条断言风险在排序而非过滤，与E4正文承认过滤未被测试直接矛盾
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: intro/contributions item 4 (n1_intro.tex)
- **Related Sections**: intro/contributions item 4 (n1_intro.tex), evaluation/E4, discussion
- **Root Cause Key**: `ordering-not-filtering-contradicts-untested-filter-replay`
- **Quote Verified**: yes
- **Quote**: `score-based ordering lowers Hit@5 from 0.94 to 0.44, while fusion order among recorded survivors restores 0.94, and all 191 recorded scores exceed the configured 0.5 threshold, so the measurable risk lies in ordering rather than in filtering`
- **Explanation**: E4 正文明确说明 filter replay 因所有候选都通过 0.5 阈值而与 fusion order 构造性恒等：'Because every logged candidate survived the configured 0.5 threshold, the filter replay is identical to fusion order by construction and does not test filtering.'，并另处承认 'it does not show a retrieval benefit from thresholding'。因此 'rather than in filtering' 是把未观测到危害写成排除性结论：过滤的排异能力根本未被检验，不能被反证为无风险。可检验的正确表述是 ordering 在本池被证明有害、filtering 在本池未被激活因而未受检。该矛盾出现在贡献清单这一读者最常引用的位置，与讨论节 'the measured failure concerns ordering, not filtering' 的措辞一脉相承，应统一改为与 E4 一致的有界表述。

### M4: 三条管理契约被称为 hypotheses 却无一可证伪，管理级模型是对工程实践的命名而非理论
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: overview/contracts (n3_overview.tex Sec 3.2)
- **Related Sections**: overview/contracts (n3_overview.tex Sec 3.2), intro/contributions, related/gap
- **Root Cause Key**: `management-contracts-not-falsifiable`
- **Quote Verified**: yes
- **Quote**: `The three management contracts are hypotheses about where the managed collection should govern the workflow, implemented at different layers: some checks are mechanically enforced by server-side tools, whereas classification and answer abstention also depend on the calling workflow, which is where the hypotheses are weakest.`
- **Explanation**: 三条契约（content classifies / a tier narrows / scope is reported）没有给出适用总体、判据与推翻条件，因此不是可检验假设而是对本系统工作流的描述；第三条更被作者自己承认为 prompt 指令（'This is not a server-side semantic classifier.'）。'management-level model' 的构件——三层对象、四层访问路径、三源对账、准入门控——分别对应目录树+元数据、目录导航、一致性审计和重排/验证等标准实践，论文也未声称有新排序算法（'It proposes no new ranking algorithm and does not claim that the underlying retrieval problem is solved.'）。把这些实践命名为契约/模型构成伪创新风险：若删除命名而保留机制描述，知识内容不变。建议要么把契约形式化为可证伪命题并用数据检验，要么放弃理论化包装、以系统+审计报告定位。

### M5: 核心机制 tier narrowing 没有形式化安全性质，自家数据显示收窄丢失证据（35/72 miss）
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: overview/levels (n3_overview.tex Sec 3.1)
- **Related Sections**: overview/levels (n3_overview.tex Sec 3.1), evaluation/E2b routing-audit, evaluation/E2c
- **Root Cause Key**: `tier-narrowing-lacks-formal-safety-property`
- **Quote Verified**: yes
- **Quote**: `Every step narrows the scope the next step must consider, and each step has a denominator`
- **Explanation**: 逐层收窄是分层的核心机制，但论文从未给出收窄保持召回的条件或任何形式性质；而其自身数据显示分层基线 A0 的金串 containment 仅 51.4%（37/72），且 'An attribution of the 35 A0 misses locates five in window truncation and thirty in judge or candidate-selection failure'——收窄丢金是架构性行为，却被作为轶事而非 narrowing 代价加以分析。论文反复强调的 'denominator'/可审计性（每层报告未覆盖范围）是真实的工程优点，但可审计不等于低丢失：一个每层都如实报告'我没找到'的系统仍然可能系统性丢证据。核心机制缺少形式刻画，使 management model 名不副实。

### M6: 全文无任何已发表的外部系统基线,所有对比均为自身组件或自身消融
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `issue`
- **Quote Verified**: yes
- **Quote**: `Nothing here is a retrieval advance: three configurations tie at Hit@5 1.00, and the one using only words leads on MRR.`
- **Explanation**: 论文相关工作引用了 GraphRAG、LightRAG、RAPTOR 等层次化/结构化 RAG 方案,但 E4 的九个配置与 E2c 的全部内容层臂都是 HMRS 自身组件或其消融,没有任何已发表的层次化管理或层次化检索系统被运行作对照。论文自己承认 BM25 在工业语料上 Hit@5=1.00、arXiv 语料上除 Graph 外全部 0.90,即新增管理层在检索质量上无可测增益;唯一直接检验分层优于扁平/精确的对比 A0h vs PD 也不显著(p=0.0703)。在内部简单基线已经封顶、外部基线缺席的情况下,论文核心的管理结构贡献无法相对现有技术被量化定位,基线完备性不足。应至少运行一个已发表的层次化基线,或将贡献定位收缩为审计方法学与失效分析。

### M7: 对检索式层级的性质断言'usually produced once and left unchanged'无任何引用支持
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `usually-produced-once-and-left-unchanged`
- **Quote Verified**: yes
- **Quote**: `Its hierarchy is a management structure over collections and documents---which collection exists, which document belongs to it, which description explains it---and it is written to and reconciled after every lifecycle operation, whereas a retrieval-time hierarchy is an index over content that is usually produced once and left unchanged.`
- **Explanation**: HMRS 与 RAPTOR/GraphRAG 的差异化主张全部压在'检索时层级通常一次性生成、之后不再更新'这一断言上，但该断言没有任何引用支撑（RAPTOR/GraphRAG 原文是否如此需要证据，且增量构建/更新是相关系统的活跃议题）。这是对被比较对象的性质刻画缺少文献佐证，属于以未验证的对比前提支撑 novelty 的典型模式。建议要么补引用并限定范围，要么把对比改写为'本文所测配置下'的可查事实。

### M8: 承载收集层与 ladder 核心证据的 11 月轨迹不公开,逐题复核不可能
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `ladder-11`
- **Quote Verified**: yes
- **Quote**: `November 2026 route traces are not public; the authors retain them for requests subject to source-document restrictions.`
- **Explanation**: E2b 路由审计(2026-11-02/03)、A1b/A2 重跑(11-10)与 E2c ladder 优化(11-11)正是论文收集层与管理层主张的主要证据,而数据可用性声明恰恰规定 11 月路由轨迹不公开。读者无法独立复核 A0h vs PD 的 7-1 discordance、A0 35 个 miss 的归因(5 truncation/30 judge)或 A3 的 11 个零字节用例;42 文档工业语料同样 not deposited publicly,仅提供替代配方。核心证据不可复核是可复现性的实质缺口,应在投稿前存放去标识化轨迹,或把相应结论标注为仅聚合统计可核。

### M9: 最近邻先行工作 DeepRead 仅一句带过，且在定位表中被压平为'接口稳定性'问题
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `deepread`
- **Quote Verified**: yes
- **Quote**: `DeepRead demonstrates structure-aware navigation for agentic search \citep{deepread}; HMRS similarly exposes a catalogue-first librarian lane, alongside dense and hybrid alternatives, under explicit call and tool policies.`
- **Explanation**: DeepRead（文档结构感知的 agentic 检索推理）是本论文最近邻的先行工作：其结构与 HMRS 的 catalogue/shelf/document 层级导航高度重叠。但 related work 仅给一句、且用 'similarly' 断言亲缘而无任何差异对比句；定位表（tab:positioning）把它与 ReAct、MCP 并入 'Agentic tool use' 行，'What it optimises' 列写作 'Access to retrieval tools behind a stable interface'，这是对 DeepRead 实际贡献的压平式刻画。同段对 GraphRAG/LightRAG/RAPTOR 各有一句准确刻画并做了正面对比，唯独最强对手没有获得同等剖析，导致集成性 gap 未在 closest prior work 上经受检验。建议仿照 RAPTOR 的三句式（它做什么→层级管辖对象差异→剩余问题）补一段，并修正定位表该行。

### M10: 核心动机句依赖'集合选择'文献线，但参考文献中该线索完全缺席（federated IR resource selection 传统）
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `federated-ir-resource-selection`
- **Quote Verified**: yes
- **Quote**: `A collection can be perfectly indexed and still answer wrongly, because the first decision a question requires---which collection should be consulted---is made without consulting the collection structure at all.`
- **Explanation**: '先选集合再检索'正是分布式/联邦式 IR 中 resource selection（database selection）研究的经典问题，而 refs.bib 与 refs_new_verified.bib 中没有任何一条该传统的条目。引言以'前人未咨询集合结构'的全称式断言开题，却在参考文献中看不到支撑或反驳该断言的文献，gap 存在被选择性引用制造的风险。由于本审阅为离线审阅、不得点名 bib 外论文，建议启用 --literature-search 核实该传统与 HMRS 集合层（catalogue 路由、E2b 路由审计）的重叠程度，再决定 gap 措辞是否需要收窄。

### M11: 被称为论文端到端证据的 E5 网格只有 10 题、单次运行且指标已在天花板
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e5-10`
- **Quote Verified**: yes
- **Quote**: `answer-layer checks per question and abstention (Section~\ref{sec:e5}, the paper's end-to-end evidence)`
- **Explanation**: E5 被冠以 the paper's end-to-end evidence,但它只有 10 个开发者编写的问题、每臂单次运行、单一模型,gold-ID 检查在两网格共 60 格全部命中(threats 亦承认 grounding is at ceiling)。检索端在小语料上近乎完美(BM25 Hit@5=1.00),该网格几乎不可能暴露检索到答案层的退化。相反,唯一检索不完美的十域语料(72 题,containment 51.4%-72.2%,35 个 A0 miss)从未进入答案层评估,只有 containment 诊断。端到端证据集中在最不可能失败的语料上,而最容易失败的路径没有答案层数据,证据布局与承载语言的强度不匹配。

### M12: 路由审计 52/72 问题为自动扩展且扩展来源未披露,叠加三个域占 47/72 的失衡
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `52-72-47-72`
- **Quote Verified**: yes
- **Quote**: `The question set is unbalanced across domains (52/72 questions were automatically expanded, with 47/72 drawn from three domains), so it does not estimate performance on a balanced domain sample.`
- **Explanation**: 收集层核心正面结果 A0=72/72(Wilson CI [0.949,1.000])来自脚本化 route-card 探针而非部署时的 agent 工作流,且运行器带有一个未记录是否触发的回退匹配器(traces do not record whether the fallback ran)。论文已声明这不是对描述移除的因果估计,但仍有未处理的混杂:52/72 问题被 automatically expanded,扩展种子(域标签?gold 文档?)完全未披露,存在问题构造向 gold 域标签泄漏的风险;47/72 集中于三个英语域且无分层分析。作为贡献列表第二条证据,其问题构造过程必须完整披露,否则应降低 72/72 的表述强度。

### M13: KBS 命题未闭合：摘要与结论以全盘自我否定收尾，正面贡献缺乏可评估的陈述
- **Type**: missing_information
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: abstract; also conclusion (n11) and related work gap (n2)
- **Related Sections**: abstract; also conclusion (n11) and related work gap (n2), abstract, sec:conclusion, sec:gap, sec:ladder-opt
- **Root Cause Key**: `venue-fit-pitch-disclaims-all-benefit-novelty-integration-only`
- **Quote Verified**: yes
- **Quote**: `These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support.`
- **Explanation**: 摘要末句（以及结论 "They do not establish system-level superiority, general retrieval effectiveness, semantic answer quality or reliability." 与相关工作 "The gap this study addresses is one of integration and of role separation rather than of missing capabilities."）把论文定位为仅集成、无能力主张。对 KBS 而言，编辑需要在 desk 阶段看到知识型系统层面的可评估贡献；当前正面证据仅有方向一致但不显著的 A0h-vs-PD 对照（"exact McNemar $p=0.0703$ ... does not reach the 0.05 threshold on this sample"），而检索层的正面结果由现成基线拿走（Table tab:retrieval-design："BM25 and RRF 1.00 vs HMRS-Hybrid 0.44"）。这不是要求夸大结论，而是要求把真实卖点（可审计的三层管理契约、collection 层可独立测量、verifier-as-ranker 负结果的部署警示、传输层失效分析）在摘要首句与结论中明写为正面命题，把限定语降为从句。否则存在 desk 阶段以 "insufficient advance over prior art" 定性拒稿的实质风险。

### M14: Abstract and conclusion claims need explicit evidence traceability
- **Type**: claim_accuracy
- **Source**: [LLM] via `claims_vs_evidence`
- **Confidence**: unverified
- **Section**: abstract
- **Related Sections**: abstract, results, conclusion
- **Root Cause Key**: `abstract-and-conclusion-claims-need-explicit-evidence-traceability`
- **Quote Verified**: yes
- **Quote**: `These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support.`
- **Explanation**: At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

### M15: 讨论章把 E2c 已完成的『阶梯 vs 平坦』同语料对照列为尚缺的后续工作
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: discussion
- **Related Sections**: discussion, eval_ladder_opt, threats
- **Root Cause Key**: `e2c-not-propagated-discussion`
- **Quote Verified**: yes
- **Quote**: `Broader claims require independent questions, repeated trials, claim-level support checks, controlled hierarchy comparisons in which the tiered path is contrasted with a flat baseline over the same corpus, operator studies and crash-recovery tests.`
- **Explanation**: 位置：Discussion 末段（n9_discussion.tex）。另一侧（Section 8.5 E2c，2026-11-11 新增）原文：『A follow-up campaign on the same 72 in-domain questions therefore varied the content layer while holding routing fixed, and added a precise per-document arm that abandons navigation』；『The scoped flat union without a judge (A1b) reached 39/72 (54.2%, p=0.6875)』；『A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar p=0.0703)』。讨论章要求的实验（同语料上 tiered vs flat baseline）正是 8.5 节已报告的实验：A1b 即 flat baseline，PD 即弃导航对照臂。Threats 章已同步（『reported in Section~\ref{sec:ladder-opt}; the ladder-versus-precise contrast (A0h vs PD) is directional (p=0.0703)』），讨论章未同步——同一事实在三个后章呈现三种状态。应改写为『8.5 节初步对照方向性支持阶梯路径但未达显著；更广主张需显著且重复的版本』。

## Moderate Issues

### M1: 编译稿正文出现损坏的交叉引用："Section efsec:ladder-opt" 与 "Section efsec:e5"
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: evaluation (Section 8.5/E4 prose, compiled page 15)
- **Related Sections**: evaluation (Section 8.5/E4 prose, compiled page 15), n8b_eval.tex, sec:ladder-opt, sec:e5
- **Root Cause Key**: `broken-cross-references-rendered-as-efsec-in-compiled-pdf`
- **Quote Verified**: no
- **Quote**: `precise alternatives is reported in Section efsec:ladder-opt, and Section efsec:e5 measures what the verification and answer layers add on top of retrieval.`
- **Explanation**: 编译后 PDF 第 15 页将两处交叉引用打印为 "Section efsec:ladder-opt, and Section efsec:e5"。字节级检查确认源文件 D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\n8b_eval.tex 第 134-135 行的 \ref 已损坏为孤立回车控制符 + "ef"（原始字节为 Section~^Mef{sec:ladder-opt} 与 Section~^Mef{sec:e5}；pdflatex 把回车当空格，于是渲染出 "Section efsec:..."）。这是全部 tex 源中仅有的两处行内 CR 损坏（grep -nP '\r.' 仅命中这两行）。投稿包中出现可见乱码引用属于必须修复的呈现缺陷，且提示当前 PDF 由损坏/过期源编译，需修复后整体重编译并复核全部引用。

### M2: 作者区与 CRediT 为占位符："Author Name"、"author@example.com"、"Affiliation Department, University, City, Country"
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: frontmatter (page 1); CRediT statement (page 23)
- **Related Sections**: frontmatter (page 1); CRediT statement (page 23), frontmatter, n_back
- **Root Cause Key**: `placeholder-author-block-and-credit`
- **Quote Verified**: no
- **Quote**: `Author Name*, Co-author Name`
- **Explanation**: PDF 第 1 页标题下方为占位作者（"Author Name*, Co-author Name"、邮箱 author@example.com、单位 "Affiliation Department, University, City, Country"）；第 23 页 CRediT 同样为 "Author 1: Conceptualisation, Methodology, Software, Investigation, Data curation, Writing – original draft. Author 2: Validation, Writing – review & editing, Supervision."。main_20p.tex 源码注释表明作者有意保留这些值（AUTHOR ACTION 块），但以现状投出必然被 Elsevier 编辑部行政退回。须在投稿前替换为真实信息，或按期刊评审版式要求匿名化，二者取一。

### M3: 摘要/讨论/结论未与新增 E2c 节同步：同语料受控对照已在 8.4 节报告，讨论仍将其列为缺失的未来工作
- **Type**: missing_information
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: discussion (n9_discussion.tex, closing paragraph)
- **Related Sections**: discussion (n9_discussion.tex, closing paragraph), sec:discussion, sec:conclusion, abstract, sec:ladder-opt
- **Root Cause Key**: `abstract-discussion-conclusion-not-updated-for-e2c-ladder-vs-precise`
- **Quote Verified**: yes
- **Quote**: `Broader claims require independent questions, repeated trials, claim-level support checks, controlled hierarchy comparisons in which the tiered path is contrasted with a flat baseline over the same corpus, operator studies and crash-recovery tests.`
- **Explanation**: 讨论（n9）与结论（n11："controlled hierarchy comparisons, larger multi-collection corpora in which the collection tier can be contrasted against flat and per-collection baselines"）都把"分层 vs. 平坦/精确的同语料受控对照"列为尚缺的未来工作；但 E2c 节（n8a，标注日期 2026-11-11）已经报告了该对照："The head-to-head contrast is the one the management claim rests on: A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample."。摘要同样只报告 route audit（72/72、37/72），完全未提 E2c 的 A0h 72.2% vs. PD 63.9%。同一事实在 8.4 节是"已做、方向一致但不显著"，在讨论/结论里是"待做"，属框架层面的内部不一致——新增实验后摘要/讨论/结论三层文本未同步更新。

### M4: 管理主张的证据锚点孤立于 8.5 节内部，主张链上下均无承载
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_ladder_opt
- **Related Sections**: eval_ladder_opt, abstract, introduction, discussion, conclusion
- **Root Cause Key**: `management-claim-anchor-orphaned`
- **Quote Verified**: yes
- **Quote**: `The head-to-head contrast is the one the management claim rests on`
- **Explanation**: 位置：Section 8.5。另一侧（全篇主张陈述处）：摘要『These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support』；引言『The contribution claimed here is the management structure that decides which collection is consulted, not a new ranking function』；讨论『The evidence supports a bounded management-system and audit contribution』。E2c 声明管理主张依赖 A0h vs PD 对照，但对该对照（72.2% vs 63.9%，p=0.0703）的引用在摘要、贡献、RQ、讨论、结论中全部缺席（对 A0h/PD/A0f/A1b/ladder 的字符串检索在这些文件中零命中）。论文声明主张 rests on 的证据与主张被陈述的每一处脱节，主张-证据绑定在链两端同时断开。修订时应让摘要/贡献/讨论至少各有一处带限定地引用该对照。

### M5: 相对作者自己 demo 论文的增量是审计证据而非新知识，期刊级增量偏薄
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: intro (n1_intro.tex prior-demo paragraph)
- **Related Sections**: intro (n1_intro.tex prior-demo paragraph), evaluation/E4, evaluation/E6, discussion, conclusion
- **Root Cause Key**: `thin-increment-over-own-demo-paper`
- **Quote Verified**: yes
- **Quote**: `The architecture and access path build on that version; the contribution claimed here is the additional evidence and failure analysis, not a wholly new system.`
- **Explanation**: 作者明确声明系统架构与访问路径均为已发表的 demo 论文（hmrs-demo）所有，期刊版增量是测量与失败分析。逐一检验这些增量：21/100 失败不可归因；60/60 饱和；路由对照混杂；A0h-vs-PD 不显著；verifier ordering 失败单语料且 'The collapse did not recur on a second corpus.'。增量证据几乎全部为零结果、饱和结果或混杂结果。以增量检验衡量（本文消失后什么知识消失），答案是单语料的 verifier-as-ranker 否定诊断加若干部署失败轶事——对 KBS 期刊文章而言偏薄。建议强化唯一可迁移发现的多语料复现，或在定位上转向部署审计方法论贡献。

### M6: 贡献清单把不可归因的内部失败计数与天花板饱和指标包装为编号贡献
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: intro/contributions item 2 (n1_intro.tex)
- **Related Sections**: intro/contributions item 2 (n1_intro.tex), abstract, evaluation/E5, discussion
- **Root Cause Key**: `contribution-inflation-internal-audits`
- **Quote Verified**: yes
- **Quote**: `Collection-level evidence. A 100-paper campaign produced 322 stored parts in five libraries, of which 79 were retrievable and 21 were not with incomplete failure attribution`
- **Explanation**: 贡献第2条以 'Collection-level evidence.' 领衔，其主体是无法归因的内部失败计数与单基准分类精度——这是对系统本身的问责数据，不构成他人可复用的知识（无基线、无外部系统对比、16/10 题量级）。贡献第3条的主体是天花板饱和的 60/60 金 ID 覆盖，正文自认 'These saturated deterministic measures do not establish semantic support.'。两条合观，四条编号贡献中有两条是'我们审计了我们自己'的有界记录；把它们升格为编号贡献稀释了真正可迁移的发现（同池 verifier 归因诊断），也放大了贡献清单与实际知识增量之间的落差。建议把贡献清单压缩为两条：verifier 角色归因 + 部署失败边界分析。

### M7: E8 scope 消融显示钉死金库无可测收益，直接削弱'选对 collection 是关键决策'的论点
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: evaluation/E8 (n8c_eval.tex)
- **Related Sections**: evaluation/E8 (n8c_eval.tex), conclusion, overview/levels
- **Root Cause Key**: `scope-ablation-shows-no-pinning-benefit`
- **Quote Verified**: yes
- **Quote**: `searched the 20 live libraries, including 15 outside the five-library evaluation corpus, and matches the gold-pinned result in this ten-question setup`
- **Explanation**: 这是全文唯一 controlled 触及 collection-selection 收益的消融：把金库作为 scope（Hit@5 1.0）与不限定库（搜索 20 个库、其中 15 个在评估语料之外）结果相同。若'决定查询哪个 collection'是系统的决定性管理决策（conclusion: 'the tier that decides which collection is consulted is a management decision rather than a ranking result'），则在该设置中该决策的收益为零。作者注明该结果受文件名前缀混杂影响、不能作为放置准确性的测量，但混杂解释不了'钉死金库无增益'这一方向——它说明在足够小的语料上，选库这一层的价值本身未被证明。该证据应被纳入贡献陈述的边界，而非仅作为 E8 的脚注。

### M8: 定位句声称获取与分类是可靠检索的 prerequisites，与自家 BM25 全文基线 Hit@5 1.00 相抵
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: related work (n2_related.tex Sec 2.1)
- **Related Sections**: related work (n2_related.tex Sec 2.1), evaluation/E4, evaluation/E1
- **Root Cause Key**: `prerequisites-claim-contradicted-by-fulltext-baseline`
- **Quote Verified**: yes
- **Quote**: `HMRS treats acquisition quality, automatic classification and traceable indexing as prerequisites for reliable retrieval rather than as preprocessing assumptions.`
- **Explanation**: 这是一个因果性前提主张，但论文从未建立获取质量与检索/答案质量之间的因果链：E4 的 BM25 基线 'runs in process over the fetched full texts' 并 'hits Hit@5 1.00 at about a millisecond per in-process call'——不经任何管理层机制的全文词法检索在本文数据中已经完美；0.875 的英文分类错误率与 21/100 不可召回也未被连接到任何下游质量退化。'prerequisites rather than preprocessing assumptions' 是论文把自己与 RAG 预处理假设区分开的关键定位句，但它自身只是一个未检验的预处理假设的否定式重述。

### M9: 摘要对 72/72 路由结果的表述省略 scripted 关键边界，读者会归因于系统选库能力
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: abstract
- **Related Sections**: abstract, evaluation/E2b routing-audit
- **Root Cause Key**: `abstract-omits-scripted-probe-qualifier`
- **Quote Verified**: yes
- **Quote**: `In a 72-question route audit, the collection-selection arm returned the gold collection for 72/72 and name-only for 37/72, though an unlogged fallback could use descriptions.`
- **Explanation**: 摘要披露了 fallback 混杂（好），但 5.3 节才揭示 'This was a scripted route-card probe, not an LLM agent selecting a library.'——路由选择是确定性脚本探针而非系统代理行为。摘要中 'the collection-selection arm' 的措辞会让只读摘要的读者把 72/72 归因于系统的 collection-selection 能力。鉴于该结果正是论文核心卖点的唯一大样本证据，scripted 这一限定应进入摘要；这不是严重的过度声称（正文诚实），但属于摘要层面的边界透明度不足。

### M10: 摘要结果清单未包含新增的 E2c 阶梯-vs-precise 对照
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: abstract
- **Related Sections**: abstract, eval_ladder_opt
- **Root Cause Key**: `e2c-not-propagated-abstract`
- **Quote Verified**: yes
- **Quote**: `Exact-string containment was 37/72 and 33/72; a read-all script found them in 72/72 cases after 879 parts (24.3 MB, 253.7 s) without answering.`
- **Explanation**: 位置：Abstract（main_20p.tex）。摘要逐项列出 route audit（72/72 vs 37/72）、containment（37/72 与 33/72）、read-all（72/72）、answer grids（60/60）、verifier（0.94→0.44）等全部战役，唯独缺失 2026-11-11 新增的 E2c。另一侧（Section 8.5）原文：『adding a vector chunk-window union to the judge pack (A0h) raised it further to 52/72 (72.2%, p=6.1e-05)』；『The head-to-head contrast is the one the management claim rests on』。摘要中阶梯路径的 containment 停留在修订前状态（A0 51.4%），读者无法得知修订后的核心对照（72.2% vs 63.9%，方向性、非显著）。摘要数字本身与正文一致（非虚假陈述），问题是清单不完整且与 E2c 的自我定位（管理主张所依赖的对照）冲突。建议在 containment 句后补一句带非显著限定的 E2c 结果。

### M11: 结论章同样把 E2c 已提供的 controlled hierarchy comparisons 列为缺失需求
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: conclusion
- **Related Sections**: conclusion, eval_ladder_opt
- **Root Cause Key**: `e2c-not-propagated-conclusion`
- **Quote Verified**: yes
- **Quote**: `Broader evaluation needs independently authored questions, repeated agent trials, claim-level support review, controlled hierarchy comparisons, larger multi-collection corpora in which the collection tier can be contrasted against flat and per-collection baselines, and crash-recovery tests.`
- **Explanation**: 位置：Conclusion 末段（n11_conclusion.tex）。另一侧（Section 8.5）原文：『Ladder matches or exceeds precise at ~1/10 the search calls; not significant at 0.05』（表 tab:retrieval-design E2c 行）。结论把『对照本身』整体列为未来需要，而 E2c 已在同一 72 题语料上给出 tiered (A0h 72.2%) vs flat (A1b 54.2%) vs precise (PD 63.9%) 对照。后半句『larger multi-collection corpora...』只覆盖规模需求，不改变『对照已存在却被说成尚缺』的陈旧表述。建议改为『需要 8.5 节对照的更大规模、可重复版本』。

### M12: 头条成本比例『~1/10 the search calls』在全文无调用计数数据支撑
- **Type**: claim_accuracy
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_ladder_opt
- **Related Sections**: eval_ladder_opt, routing_audit
- **Root Cause Key**: `one-tenth-search-calls-unsupported`
- **Quote Verified**: yes
- **Quote**: `Tiered navigation plus the chunk union therefore matches or exceeds abandoning navigation while issuing roughly a tenth of the search calls, but the sample is too small to claim a significant advantage.`
- **Explanation**: 位置：Section 8.5 正文；同比例写入表 tab:retrieval-design 的 supports 列：『Ladder matches or exceeds precise at ~1/10 the search calls』。全文唯一报告调用次数处是 Section 8.4：『31.4 KB and 16.3 s across four calls for A0. A3 averaged 23.5 KB and 7.8 s across 4.1 calls』及 A1 的『897 tool calls per question』——A0h 与 PD 的每题调用次数均未报告，『十分之一』无法从文中核验。而该对照恰是论文自称『the one the management claim rests on』的比较，其成本优势作为头条结论应给出两侧调用计数或标明补充材料中的具体表号。

### M13: 引言贡献清单与 journal-extension 列表均未纳入 E2c；RQ 清单亦无对应问题
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: introduction
- **Related Sections**: introduction, eval_ladder_opt
- **Root Cause Key**: `e2c-not-propagated-contributions`
- **Quote Verified**: yes
- **Quote**: `The journal extension adds acquisition and lifecycle measurements, a paired collection-selection audit, the operational-knowledge case study, and the verifier-placement and transport-failure analyses.`
- **Explanation**: 位置：Introduction（n1_intro.tex）。四条 Contributions 分别绑定 route audit、lower tiers、answer grids、segment-tier 诊断，没有一条对应 E2c；期刊扩展清单同样缺失；RQ1–RQ5 中没有任何一条问『阶梯导航是否优于放弃导航』。另一侧（Section 8.5）原文：『The head-to-head contrast is the one the management claim rests on』，而引言自己的贡献定义是『The contribution claimed here is the management structure that decides which collection is consulted, not a new ranking function』。论文自称管理主张所依赖的关键对照在贡献声明中缺位，主张-证据绑定在上游断裂。建议在贡献 2 或 3 中补一句 E2c 概括（含非显著限定），并在 RQ2/RQ3 中补入该问题。

### M14: 与最接近先行工作（RAPTOR/GraphRAG/DeepRead）的区分停留在重新定义，无实验交锋
- **Type**: missing_information
- **Source**: [LLM] via `committee_theory`
- **Confidence**: unverified
- **Section**: related work (n2_related.tex Sec 2.2)
- **Related Sections**: related work (n2_related.tex Sec 2.2), evaluation/E2
- **Root Cause Key**: `positioning-by-redefinition-no-empirical-engagement`
- **Quote Verified**: yes
- **Quote**: `HMRS differs in what the hierarchy governs.`
- **Explanation**: 论文正确承认 'Hierarchical representation is therefore already an established retrieval concern'，其区分是概念性的：RAPTOR/GraphRAG 的层级是一次性生成的检索索引，HMRS 的层级是每次生命周期操作后重写并对账的管理结构。这个区分成立，但全文没有任何实验把管理结构与其替代方案（例如每次变更后重建检索层级）比较，管理性质（对账、生命周期一致性）的收益从未被测量。对最相近的 DeepRead（'DeepRead demonstrates structure-aware navigation for agentic search'，HMRS 'similarly exposes a catalogue-first librarian lane'），delta 只有 similarly 一词，未说明也未测量。基于重新定义的定位无法支撑集成性 gap 主张。

### M15: 'research has largely treated them separately'前提与自引综述 modular-rag/gao-ragsurvey 相互抵触，矛盾被定位表抹平
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `research-has-largely-treated-them-separately-modular-rag-gao-ragsurvey`
- **Quote Verified**: yes
- **Quote**: `The two capabilities required for this operate on different parts of the lifecycle, and research has largely treated them separately.`
- **Explanation**: 引言的核心前提是检索研究与知识管理研究'大体各自为政'，但参考文献中的 modular-rag（'Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks', ACM TOIS 2026）与 gao-ragsurvey 恰恰把数据摄取/索引（data indexing、pre-retrieval）作为 RAG 管线的一等模块讨论——n2 自己也引用它们为 'Modular RAG and agentic-retrieval surveys describe reconfigurable retrieval pipelines'。定位表将 Retrieval 线索的刻画写作 'Rank quality over a corpus that is assumed indexed'，与自引综述的内容冲突且全文从未正面调和。建议把集成贡献收窄到自引综述确实未覆盖的部分：集合生命周期治理（move/rename/delete/forced re-index 后的三源对账）。

### M16: 21 篇不可检索论文的失败归因缺失,采集失败诊断停留在语料级聚合
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `21`
- **Quote Verified**: yes
- **Quote**: `neither attempts against failed papers nor per-paper parse status is recorded, so the 21 cannot be attributed to parsing alone`
- **Explanation**: RQ1 承诺回答采集与分类 where that process fails,但 E1 只有聚合计数(91 in state file、79 retrievable、12+9=21 不可归因),重试次数与逐篇 parse 状态均未记录,失败模式仅两句轶事(formula-dense scans and one tool-layer crash)。一个以可审计状态为核心卖点的系统,其采集层自身的失败审计不完整,这一自反性缺口应在 threats 中显式承认,并给出逐篇失败记录的改进方案。

### M17: \cite{graphrag} 被错挂到系统自身弱图检索工具的结果句上
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `cite-graphrag`
- **Quote Verified**: yes
- **Quote**: `This single miss coincides with a crowded candidate set but cannot isolate its cause; graph search \cite{graphrag}, limited to node-name and tag matching, is the weakest standalone signal.`
- **Explanation**: 该句描述的是 HMRS 自己的 kb_graph_search 工具（n8b 同节定义为 'a keyword match over node names, paths and tags in the document graph'），与 n2 对 GraphRAG 的准确刻画（'GraphRAG adds entity-relation graphs and community summaries'）完全不同。把 GraphRAG 的引用直接附在'受限的节点名/标签匹配'后面，既误传了 GraphRAG 的方法内容，又会让读者误以为评测对象是 GraphRAG 类系统，从而把负面结果外溢到文献上（对原论文作者不公平的刻画）。建议改为引用系统自身实现（Neo4j 文档图谱的构建描述）或降格为 '(cf.~\cite{graphrag})' 的体裁对比。

### M18: A1b/A2 于 2026-11-10 更换协议后与 11-02/03 的 A0/A0f/A0h/PD/A3 同图比较
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `a1b-a2-2026-11-10-11-02-03-a0-a0f-a0h-pd-a3`
- **Quote Verified**: yes
- **Quote**: `The flat and no-gate arms (A1b, A2) were re-run on 2026-11-10 as scoped per-library directed searches merged by score, replacing an earlier unscoped protocol`
- **Explanation**: fig:ladder 与 E2c 把 11-02/03 运行的臂与 11-10 按新协议重跑的 A1b/A2 并置同一比较框架;问题集相同,但臂的检索协议在日期之间被替换,且最初设计为 unscoped。重跑已披露,但跨日期、跨协议的可比性风险未讨论——尤其论文在其他处强调快照差异不可合并(a different snapshot, and the two grids are not pooled)。应说明两日期间语料与索引快照是否逐位一致。

### M19: E2c 效率主张只计搜索调用次数,不计判官 token 与字节预算,维度选择有利己偏置
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e2c-token`
- **Quote Verified**: yes
- **Quote**: `matches or exceeds abandoning navigation while issuing roughly a tenth of the search calls`
- **Explanation**: ladder 臂与 PD 的取舍维度不止搜索次数:A0h 给判官喂入全窗口加 chunk-window 并集,每题判官输入 token 很可能接近甚至超过 PD 的全窗口判读;containment 指标本身偏向把更多原文送进证据包的臂(read-all 机械上限 72/72 即为证)。路由审计报告了字节数与工具秒数,最关键的 E2c 对比却只报告调用数这一个对自己有利的成本维度,无 token、字节或 wall-clock。效率口径不完整构成维度选择性偏置。

### M20: E5b 设计汇总表与正文不一致(3 臂×6 题 vs 3 题×3 臂),file-tree 结论错行,臂标签映射缺失
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e5b-3-6-vs-3-3-file-tree`
- **Quote Verified**: yes
- **Quote**: `Three arms $\times$ six questions, public API & Cost, latency, refusal behaviour & Platform arm slower and dearer than the file-tree arm`
- **Explanation**: 正文定义 E5b 为 Three questions (an English methodology question, a Chinese clinical question and an out-of-corpus probe) crossed three deployment arms,即 3 题×3 臂;六个问题属于 honesty battery,file-tree arm 是 E5 的对照臂而非 E5b 的任何臂(S1/S2/S3 都是 pinned/unpinned/hybrid 变体)。tab:retrieval-design 的 E5b 行混入了另两个实验的设计与结论。此外正文先定义 S1/S2/S3,成本却按 (A)、(B)、(C) 报告(Mean cost was \$0.182 (A), \$0.300 (B) and \$0.219 (C)),映射全文未给出。设计汇总表是读者建立实验地图的主要入口,此处失真必须修正。

### M21: hmrs-demo 条目作者仍为占位符 'Author Name'（bib 内含未完成的 AUTHOR ACTION 注释）
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `hmrs-demo-author-name-bib-author-action`
- **Quote Verified**: no
- **Quote**: `%% AUTHOR ACTION: fill real author list before submission. @inproceedings{hmrs-demo, title     = {{HMRS}: Content-Routed Organization and Layered Agent Retrieval with Inspectable Evidence}, ... author    = {Author Name},`
- **Explanation**: hmrs-demo 是本文的先行演示版引用（n1：'A prior demonstration version introduced the organisation and retrieval layers \cite{hmrs-demo}'），是 novelty 定位的基线锚点，但 bib 条目的 author 字段仍是 'Author Name' 占位符，且条目上方保留着 'AUTHOR ACTION: fill real author list before submission' 的待办注释。'To appear'（CIKM '26 Demo Track）本身可接受，但投稿前必须补齐真实作者与确认卷期，否则该条目不可核验。

### M22: threats 一节与实验缺口的四处错配:多重比较、评分噪声、退役 wrapper 外推、E3 近零证据
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `threats-wrapper-e3`
- **Quote Verified**: yes
- **Quote**: `One scenario and thirteen candidates cannot support an effectiveness claim; scheduled distillation, review and approval at scale, application feedback and credibility decay went unexercised.`
- **Explanation**: threats 总体罕见详尽,但与实验实际留下的缺口仍有四处错配:(a) 全文十余个配对检验无校正,threats 未提;(b) E8 显示的 LLM 评分 0→5 摆动量级未进 threats;(c) E4 负结果被限定于退役 wrapper,但现行 composed lane 未被基准化这一泛化限制未进 threats;(d) E3 经验子系统批准路径从未行使(draft-approval path was never exercised)、仅一个场景,threats 完全未提及该子系统的证据近零状态。若声称 limitations 与实验缺口对齐,这四项应补入。

### M23: 从不显著的 A0h-PD 检验写出 matches or exceeds 的等同式结论
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `a0h-pd-matches-or-exceeds`
- **Quote Verified**: yes
- **Quote**: `A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample.`
- **Explanation**: 论文诚实地报告 p=0.0703 不显著,但同段随后写 Tiered navigation plus the chunk union therefore matches or exceeds abandoning navigation。n=72、仅 8 个 discordant 的检验不显著只能支持未检测到差异,不能支持 matches or exceeds 这类等同主张;等效性需要等效边际与功效分析,均未提供。建议改为数值上更高但不显著(7-1 discordant),并给出该对比的最小可检差异或功效估算。

### M24: 单次运行的非确定 agent 泳道配 Wilson 比例区间,系统性低估总不确定性
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `agent-wilson`
- **Quote Verified**: yes
- **Quote**: `The tool-layer retrieval lanes, grading rule, audits, duplicate adjudication and cross-lingual ingestion pipeline are deterministic; agent lanes and text-derived results are not.`
- **Explanation**: 论文明确区分确定性泳道与非确定 agent 泳道,又承认 30-cell answer grid is a single run per arm on one model;但报告的 Wilson 95% 区间只把题目当作随机来源,题目×运行两个方差成分中运行成分完全未估计,而 E8 的 0→5 评分摆动证明该成分不可忽略。所有 agent 层比例的区间因此系统性偏窄。至少应声明区间条件于该次运行,或补小规模重复运行给出运行间方差下界。

### M25: 同一 72 题上十余个配对 McNemar 检验无多重比较控制
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `72-mcnemar`
- **Quote Verified**: yes
- **Quote**: `All rates are gold-string containment over the 72 questions, with Wilson 95\% intervals and exact paired McNemar tests against the tiered baseline A0`
- **Explanation**: E2c 对 6 个臂各做一次对 A0 的配对检验,再加 A0h vs PD 头对头、E2b 的两个配对检验、E5 两网格间的多个 McNemar,检验 family 总数约十余个;全文未提及任何校正(如 Holm/Bonferroni),threats 亦未讨论。最小的 p(6.1e-5)对任意校正稳健,但 PD p=0.0039、A0f p=0.0078、A2 p=0.0227 这类边缘显著支撑着 A0f repairs eight, A0h fifteen 的递进叙述,未必能存活;应声明未校正并做敏感性说明。

### M26: 同一输入下 LLM 评分摆动 0→5、3→0,该噪声量级未推广为对评分类结论的测量误差警告
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `llm-0-5-3-0`
- **Quote Verified**: yes
- **Quote**: `downstream LLM grades varied in both directions (QK01 $0\to5$ and QK03 $3\to0$ under the same twelve-document, 4{,}000-character pack; sign test $p=1.0$, $n=10$)`
- **Explanation**: 候选集与证据包完全固定时,下游 LLM 评分在量表两端翻转,说明答案级 LLM 评分的运行间噪声可达满量程;该量级超过 E8 报告的全部组间效应,也波及依赖 LLM 评分与 E5b answer gate 的所有单次比较。threats 只写 each arm was run once,未把该噪声量级写入,评分信道的方差从未被量化。应将此噪声量级明确列为对一切答案级评分比较的测量误差来源。

### M27: 文本分块/结构切分文献线缺失，而结构切分是系统的核心机制之一
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `issue`
- **Quote Verified**: yes
- **Quote**: `At the segment level a document is split at recognised structural markers and its parts are indexed for dense and lexical search`
- **Explanation**: 结构化切分（structural-marker split、30,000 字符档位、800 字符 chunk 复现）贯穿采集与评估（E1/E4/E5），但两份 bib 中没有任何分块/切分策略文献条目。面向 KBS 读者的 RAG 系统论文通常需要引用切分文献来定位自己的切分选择（哪些标记、什么粒度、对检索的影响），否则该设计显得无文献坐标。离线审阅不点名 bib 外论文，建议启用 --literature-search 补齐该线索并在 n4/n5 或 related work 中定位切分决策。

### M28: 核心验证器 Laya 仅有模型卡出处，related work 的 judge 可靠性文献从未反观这一具体选择
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `laya-related-work-judge`
- **Quote Verified**: yes
- **Quote**: `The gate is the local Laya evidence classifier \cite{laya}, exposed as \path{kb_laya_judge}.`
- **Explanation**: Laya（E4–E6 的主角）唯一出处是 HuggingFace 模型卡（bib 注明 'Model card'）。n2 的 2.3 节专门综述了 LLM-as-a-judge 的偏好偏差、自偏好与验证器 gaming（zheng-llmjudge、sun-urara、panickssery-selfpref、lightman-verify），但从未把这些警告与'选择 Laya 作为 0-1 判分器'这一具体设计决策连接起来——这层呼应直到 E6 失败分析才隐式出现。对 KBS 读者而言，论文的核心机制建立在一个无同行评审评估的组件上，related work 应当显式承认该选择落在其引用的 judge 可靠性警告的覆盖范围内，并说明为何仍值得一测。

### M29: 答案网格的任务契约、harness prompt 与模型标识不可复现
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `harness-prompt`
- **Quote Verified**: yes
- **Quote**: `recorded in the run timeline as claude-opus-4-8[1m] with seed~0 and harness prompt v4-neutral`
- **Explanation**: E5 两网格 under one task contract,但该契约的 prompt 文本、harness prompt v4-neutral 的内容与版本在正文与可见补充材料中均未给出;claude-opus-4-8[1m] 是运行时间线内部标签而非可引用的模型版本(无快照日期);对托管模型声明 seed 0 不能保证可复现。E8 已证明结论对 prompt 与评分高度敏感(同包 0→5 摆动),缺失 prompt 文本使答案层实验在严格意义上不可复现。

### M30: 索引维护/增量更新文献线缺失，而'生命周期后对账'恰是论文宣称的关键区分轴
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `issue`
- **Quote Verified**: yes
- **Quote**: `which is the sharpest illustration of why an explicit re-index operation belongs in the management contract rather than in an implicit side effect of renaming.`
- **Explanation**: E2 的重命名-索引失步缺陷（rename 后向量索引保留旧名 chunks，仅 force re-index 可修复）是论文最强的管理层发现之一，n2 也把 'written to and reconciled after every lifecycle operation' 作为与检索式层级的核心区分。但参考文献中没有任何索引维护/增量更新/陈旧索引检测的文献条目，区分轴落在一个未被引用的文献线上，'usually produced once and left unchanged' 的对比因此显得是为制造差异而设。建议启用 --literature-search 检索该线索（增量索引维护、索引一致性），并在 Sec. 2.2 或 E2 中给出文献坐标。

### M31: 被评估的 hybrid wrapper 已退役,在售混合通道从未做工具层检索质量基准
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `hybrid-wrapper`
- **Quote Verified**: yes
- **Quote**: `The evaluated hybrid wrapper is no longer registered in the current tool layer, whose hybrid lane is the composed chat configuration of Section~\ref{sec:twostage}, so the negative ordering result below is bounded to that retired wrapper.`
- **Explanation**: 把 HMRS-Hybrid 0.44 的负结果限定在已退役 wrapper 上是诚实的,但这同时意味着系统当前的 hybrid lane 只在 10 题答案网格中出现过,从未在 E4 的两个语料上接受工具层检索质量测量。表 tab:retrieval 的 HMRS-Hybrid 行描述的是作者自己已移除的组件,读者若据表推断在售系统的混合检索质量会被误导。应在表内显著标注 retired,并给出现行 composed lane 的等价测量或说明其不可测的原因。

## Minor Issues

### M1: Section 8 开篇评估路线图漏列 sec:ladder-opt，与其自身表 5 不一致
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_intro
- **Related Sections**: eval_intro, eval_ladder_opt, tab_levels
- **Root Cause Key**: `e2c-missing-from-eval-roadmap`
- **Quote Verified**: yes
- **Quote**: `verifier failure (Section~\ref{sec:e6}), non-functional behaviour (Section~\ref{sec:e7}) and the gate and search-scope ablations (Section~\ref{sec:e8}) are measured.`
- **Explanation**: 位置：Section 8 开篇路线图段（n8a_eval.tex）。该段按管理层次枚举 E1/E2/routing audit/E4/E5/E5b/E6/E7/E8，未提新增的 8.5 节；但同段引用的表 tab:retrieval-design 已含 E2c 行：『E2c & Ten-domain 72 q; content-layer arms & Containment; tiered vs flat vs precise & A0h 72.2% vs PD 63.9% (7--1, p=0.0703); A1b 54.2%』。同一节内散文路线图与表格不同步；表 tab:levels 的 Evidence 列亦未把 E2c 计入任何管理层级。建议在路线图中补入 content-layer optimisation arms（Section 8.5）。

### M2: 正文使用未定义的内部专名 SOUL 与 persona-distillation 工作流
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: system overview (n3_overview.tex, sec:architecture); implementation (n7)
- **Related Sections**: system overview (n3_overview.tex, sec:architecture); implementation (n7), sec:architecture, sec:impl-tools
- **Root Cause Key**: `undefined-internal-proper-nouns-soul-persona-distillation`
- **Quote Verified**: yes
- **Quote**: `Experience retrieval and SOUL reuse knowledge-base infrastructure but follow their own retrieval and filtering paths; neither is described here as invoking Laya, and neither was evaluated at scale.`
- **Explanation**: n3_overview.tex 中 "SOUL" 全文无任何展开或定义即被引用（正文中仅此一处出现该名称）；n7_implementation.tex 另提到 "plus persona-distillation workflows that are outside the scope of this evaluation and use their own retrieval and synthesis path"。对 KBS 读者而言这些是未定义的内部系统名，且与论文的知识文档管理主线无功能关联，第一遍阅读即造成困惑。建议展开为可理解的描述（或给出引用），或删除这类超范围提及。

### M3: 标题为四层名词堆叠，难以解析："A hierarchical management retrieval system for tiered knowledge document organisation and evidence-traced access"
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: title (page 1)
- **Related Sections**: title (page 1), title, abstract
- **Root Cause Key**: `title-stacked-modifiers-hard-to-parse`
- **Quote Verified**: yes
- **Quote**: `HMRS: A hierarchical management retrieval system for tiered knowledge document organisation and evidence-traced access`
- **Explanation**: 标题中 hierarchical、management、retrieval、tiered 四个修饰成分连续堆叠且无连词（"hierarchical management retrieval system"），"tiered knowledge document organisation" 再叠两层修饰。与摘要中的系统定位（"a self-hosted knowledge document management system" + "serves a matching tiered access path"）相比，标题未能传达"管理 + 检索双能力"的结构。建议改为显式并列（如 "...a hierarchical management-and-retrieval system for tiered knowledge-document organisation and evidence-traced access" 或等效形式），使读者在第一屏即可解析系统是什么。

### M4: E5b 小节实验臂标签不一致：先定义 S1/S2/S3，成本却按未定义的 (A)/(B)/(C) 报告
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: E5b (n8c_eval.tex, sec:sysarms)
- **Related Sections**: E5b (n8c_eval.tex, sec:sysarms), sec:sysarms
- **Root Cause Key**: `e5b-arm-labels-s1s2s3-vs-abc-mismatch`
- **Quote Verified**: yes
- **Quote**: `S1 pinned the target shelf, S2 left the library unpinned, and S3 pinned it with a hybrid-retrieval directive.`
- **Explanation**: n8c_eval.tex 的 E5b 段先用 "S1/S2/S3" 定义三个部署臂并在后文复用该记号（"S1 and S3 returned answers containing the gold identifiers for both in-corpus questions"、"The campaign also surfaced a transport failure: S2 falsely refused the computer-science question"），但同一小节的成本句使用从未定义的记号："Mean cost was \$0.182 (A), \$0.300 (B) and \$0.219 (C); a retrieval-only comparison returned the gold in 6/6 cells."。读者无法将 \$0.182/\$0.300/\$0.219 映射到具体臂。属编辑即可发现的符号不一致，统一为一套标签即可修复。

### M5: 摘要第二句平行结构断裂且不成句（"managing ... and answers along a tiered path"）
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: abstract (page 1)
- **Related Sections**: abstract (page 1), abstract
- **Root Cause Key**: `abstract-parallelism-broken-managing-and-answers`
- **Quote Verified**: yes
- **Quote**: `We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and answers along a tiered path narrowing from the catalogue of collections, through document descriptions, to the segment carrying the evidence.`
- **Explanation**: 摘要第 2 句（PDF 第 1 页）中 "a ... system managing documents ... and answers along a tiered path" 平行结构断裂（managing 与 answers 不能并列），且 "answers along a tiered path narrowing from ..." 本身不成句（answers 缺宾语，narrowing 悬挂）。摘要还密集罗列约 19 个数值（79/21、0.875/1.0、72/72、37/72、37/72 与 33/72、879 parts、24.3 MB、253.7 s、60 cells、0.94→0.44、0.94），第一屏信息负担过重。建议改为 "...system that manages documents at three levels (collection, document, segment) and answers questions along a tiered path..."，并压缩数字密度。

### M6: arXiv 实例库数 19 与 20 两种表述未加说明
- **Type**: claim_accuracy
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_ablations
- **Related Sections**: eval_ablations, eval_setup
- **Root Cause Key**: `nineteen-vs-twenty-libraries`
- **Quote Verified**: yes
- **Quote**: `The unscoped call (\texttt{kb\_id=""}) searched the 20 live libraries, including 15 outside the five-library evaluation corpus`
- **Explanation**: 位置：Section 8.8 E8。另一侧（Section 8.1 实验设置，arXiv 语料条目）原文：『Ten gold questions (BQ01--BQ10) target papers referenced by those papers, keyed by arXiv identifier; the running instance then held 19 libraries』。两处相差 1 且无快照时间说明（可能实例在两次测量间新增了一个库），读者无法确认 E8 的 unscoped 检索范围与 BQ 题集所用实例处于同一状态。应为两处标注快照日期或统一计数并说明差异。

### M7: E4 指向 E2c 的交叉引用在源码中损坏（Section~ef{...}）
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_retrieval
- **Related Sections**: eval_retrieval, eval_ladder_opt
- **Root Cause Key**: `broken-ref-to-ladder-opt`
- **Quote Verified**: yes
- **Quote**: `the current comparison of the tiered path against flat and precise alternatives is reported in Section~ef{sec:ladder-opt}, and Section~ef{sec:e5} measures what the verification and answer layers add on top of retrieval.`
- **Explanation**: 位置：n8b_eval.tex 第 134–135 行（E4 小节）。两处 \ref 丢失反斜杠-r（源码字面为 ~ef{...}），编译后渲染为乱码文本而非节号。另一侧：E2c 标签确实存在——『\subsection{E2c: Content-layer optimisation and the ladder-versus-precise contrast (2026-11-11)}\label{sec:ladder-opt}』。E4『旧六方法 lane matrix 已被取代、新对照见 8.5 节』这一论证交接在成稿 PDF 中断裂，读者无法从 E4 跳到新的 ladder-vs-precise 对照。应恢复为 \ref{sec:ladder-opt} 与 \ref{sec:e5}。

### M8: 参考文献被压至 7.2 pt、条目间距 0 pt 以满足页数预算，排版基线低于常规投稿
- **Type**: presentation
- **Source**: [LLM] via `committee_editor`
- **Confidence**: unverified
- **Section**: main_20p.tex preamble lines 138-147; rendered pages 23-24
- **Related Sections**: main_20p.tex preamble lines 138-147; rendered pages 23-24, references
- **Root Cause Key**: `references-compressed-to-7.2pt-for-page-budget`
- **Quote Verified**: no
- **Quote**: `Tight item separation and 7.2 pt type keep the current list within this local 20-page preview budget while staying above the 7 pt finished-type floor`
- **Explanation**: main_20p.tex 导言区（第 138-147 行）将参考文献设为 7.2 pt 字号、bibsep 0 pt、baselineskip 7.4 pt，并以注释自述目的是保住本地 20 页页数预算；渲染 PDF 第 23-24 页的参考文献实际观感远小于正文。Elsevier 初审后会重新排版，但投稿预览稿以压缩字号制造页数预算属于呈现基线问题；若按 5p final 版式直接投稿，该排版会被保留。建议恢复 elsarticle 默认参考文献字号，页数通过正常排版参数与内容取舍解决。（锚点为源文件精确位置而非正文语句。）

### M9: E2c 由 p=0.0703 的 7–1 差异以 therefore 推出 matches or exceeds
- **Type**: claim_accuracy
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_ladder_opt
- **Related Sections**: eval_ladder_opt
- **Root Cause Key**: `therefore-from-non-significant`
- **Quote Verified**: yes
- **Quote**: `The head-to-head contrast is the one the management claim rests on: A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample.`
- **Explanation**: 位置：Section 8.5。紧接着的一句以『therefore』从未达显著的方向性差异推出比较性结论：『Tiered navigation plus the chunk union therefore matches or exceeds abandoning navigation』。同句自带限定（『but the sample is too small to claim a significant advantage』），表 5 亦标注『not significant at 0.05』，处理算克制，故降为 minor；残余问题是『rests on』措辞把论文核心主张架在亚显著结果上，而全篇任何主张陈述处都不引用该结果（另见孤立锚点条目），两处张力应在措辞上统一（如改为 is directionally consistent with / is informed by）。

### M10: 『holding routing fixed』与 PD 弃用导航的表述冲突，夸大了对照的控制度
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_ladder_opt
- **Related Sections**: eval_ladder_opt
- **Root Cause Key**: `holding-routing-fixed-overstated`
- **Quote Verified**: yes
- **Quote**: `A follow-up campaign on the same 72 in-domain questions therefore varied the content layer while holding routing fixed, and added a precise per-document arm that abandons navigation`
- **Explanation**: 位置：Section 8.5 设计句。另一侧（同节）原文：『The precise per-document arm PD, which searches the ten libraries as a directed union and judges full windows without navigation, reached 46/72 (63.9%, p=0.0039)』。标题性对照 A0h vs PD 同时改变内容层与路由层（PD 完全不做路由选择），并非『固定路由』下的单因子隔离；『holding routing fixed』的措辞会误导读者以为该对照 isolates 内容层。『the ladder-versus-precise contrast』的命名本身是诚实的。建议改述为：在保持 A0 路由的系列臂之外另加一个放弃导航的 precise 臂，A0h vs PD 因此同时涉及两层。

### M11: E5b 费用标签 (A)/(B)/(C) 与同小节定义的臂名 S1/S2/S3 不匹配
- **Type**: missing_information
- **Source**: [LLM] via `committee_logic`
- **Confidence**: unverified
- **Section**: eval_sysarms
- **Related Sections**: eval_sysarms
- **Root Cause Key**: `e5b-arm-label-mismatch`
- **Quote Verified**: no
- **Quote**: `Mean cost was $0.182 (A), $0.300 (B) and $0.219 (C); a retrieval-only comparison returned the gold in 6/6 cells.`
- **Explanation**: 位置：Section 8.7 E5b。同小节先定义『Three deployment arms through the external chat API: S1 pinned the target shelf, S2 left the library unpinned, and S3 pinned it with a hybrid-retrieval directive』，随后费用却按旧稿标签 (A)/(B)/(C) 报告，属概念漂移；读者无法把三个成本值绑定到具体部署臂。按上下文推测 A=S1、B=S2、C=S3，而 S2 恰是假拒绝臂（131 文档目录超出工具输出预算），成本归属直接影响『部署成本』结论的解读。应统一为 S1/S2/S3。

### M12: \cite{siren,gao-ragsurvey} 对'相似度≠证据'的概念区分支撑力偏弱
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `cite-siren-gao-ragsurvey`
- **Quote Verified**: yes
- **Quote**: `Semantic similarity measures topical relatedness, not whether a passage contains evidence for the requested claim \cite{siren,gao-ragsurvey}.`
- **Explanation**: 两篇引用均为综述（幻觉综述、RAG 综述），它们支持'检索无关性导致幻觉'一类宏观命题，但并不直接给出'语义相似度只测量题旨相关、不测量证据包含'这一概念区分本身。该区分是证据门（evidence gate）的全部动机，值得更精确的文献支撑（如相关性/效用与证据性的区分研究），或在措辞上降格为'见综述中的失败模式讨论'。当前写法把强主张挂在了弱支撑上。

### M13: Controls 段称 honesty battery carry repeats,threats 段却称每臂最终只有一次观测
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `controls-honesty-battery-carry-repeats-threats`
- **Quote Verified**: yes
- **Quote**: `the 27-cell stability suite (Section~\ref{sec:e7}) and the eighteen-arm honesty battery (Section~\ref{sec:sysarms}) carry repeats`
- **Explanation**: threats 写 The refusal battery has one final observation per arm after two MCP-mount interruptions were rerun,与 Controls 段的 carry repeats 表述不一致:repeats 指失败重跑还是重复观测并不清楚。应统一口径,说明哪些臂有真正的重复观测、哪些只是失败后重跑。

### M14: cyberbot（CIKM'25 五页短文）被用作 ontology-grounded retrieval 线索的代表，分量不足
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `cyberbot-cikm-25-ontology-grounded-retrieval`
- **Quote Verified**: yes
- **Quote**: `Other work studies selective prediction under domain shift, ontology-grounded retrieval and citation verification \citep{kamath,cyberbot,liu-verifiability,gao-citations}.`
- **Explanation**: 四个引用簇中，kamath（ACL 2020 长文）、liu-verifiability 与 gao-citations（EMNLP 2023 长文）分量相当，而 cyberbot 是 CIKM 2025 的 5 页短文（pp. 6752–6756，应用领域为网络安全教育）。用它代表 ontology-grounded retrieval 这一与本文集合/本体结构直接相关的线索，为期刊级 gap 定位作支撑，代表性偏薄；且该簇的压缩（三个话题四个引用一条子句）使读者无法分辨每篇到底支撑哪个主张。建议扩充该线索或改用更核心的代表作（若经 --literature-search 确认），并在行文中一一对应话题与引用。

### M15: E6 把四篇 judge 可靠性文献挂在对本文自身跨语料对比的谨慎限定句上
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e6-judge`
- **Quote Verified**: yes
- **Quote**: `These studies also differ in domain, language and corpus size, so they do not isolate confuser density as the cause; the cross-corpus pattern is descriptive, not causal \cite{zheng-llmjudge,panickssery-selfpref,lightman-verify,yin-knowwhat}.`
- **Explanation**: 该句限定的对象是本文自己两个语料（工业语料 vs arXiv 语料）之间的不可归因性，与所引四篇文献（MT-Bench judge 偏差、自偏好、Let's Verify、LLM 自知之明）的主张没有直接支持关系——四篇文献谈的是 judge/验证器的可靠性，不是跨语料因果推断的方法学。引用被用作给一个 hedge 加权威。建议删除该处引用，或将其移到本小节确实对应文献主张的句子（如 'The verdict is a model' 对 judge 局限的讨论处）。

### M16: E7 缓存修复后只重测部分读路径,完整 sweep 与超时率未声明复测
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e7-sweep`
- **Quote Verified**: yes
- **Quote**: `A later cache repair lowered the 30-client read-ladder \emph{p50} from 1577 to 65.8\,ms and repeated-query \emph{p50} from 3743 to 2.1\,ms; distinct queries remained near 4--5 requests per second under a process-wide lock.`
- **Explanation**: 41% 超时的结论来自修复前的完整 270 请求 sweep;修复后只引用 read-ladder 与 repeated-query 两个选定指标的 p50,未说明是否重跑了同一 sweep、超时率是否下降。同一小节内前后两个系统状态的测量协议不同,容量结论的时间一致性应予声明。

### M17: nDCG@5 已计算但不报告,构成轻度选择性报告
- **Type**: methodology
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `ndcg-5`
- **Quote Verified**: yes
- **Quote**: `nDCG@5~\cite{jarvelin-cumulated-gain-2002} was computed only inside one exploratory arm we do not report.`
- **Explanation**: 披露本身正确,但先计算、后选择不报且不给结果方向的写法留下选择性报告的疑问;一句关于该探索臂结果方向或弃用原因的说明即可消除。

### M18: 延迟列混合进程内基线与工具层通道,表格层面未隔离
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `issue`
- **Quote Verified**: yes
- **Quote**: `neither is the platform's keyword tool, so the millisecond latencies are in-process measurements rather than a server round trip.`
- **Explanation**: BM25/RRF 的 0.9/11 ms 是作者进程内实现,其余行(18-542 ms)是工具层调用;同一列并排呈现会诱导跨 substrate 的延迟比较。正文已作区分,但表格未按 substrate 分组或对 in-process 行加注(衍生行有 dagger 脚注而 BM25/RRF 行没有)。建议表内分组或加脚注,避免 0.9 ms 对 542 ms 的表观对比被直接引用。

### M19: 测量前修复的两处故障恰属于 E2 所测失效类别,自然失效率未报告
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `e2`
- **Quote Verified**: yes
- **Quote**: `Before measurement we repaired two corpus-integrity faults through the platform's own operations: one document missing from its vector collection was re-indexed, and one library whose collection had been lost was rebuilt, the same failure class that Section~\ref{sec:e2} measures.`
- **Explanation**: 披露值得肯定,但它同时说明被测期间自然发生的失效在正式测量前被清除:E2 报告的一致性结果条件于无未修复自然失效的状态,自然失效率(该类故障在 campaign 期间自发出现的频率)从未报告;修复与被测行为同源,均通过平台自身操作执行,无独立对照。

### M20: 评估章节形成'权威背书式'引用模式：综述被用来支撑对自身系统的观察
- **Type**: missing_information
- **Source**: [LLM] via `review`
- **Confidence**: unverified
- **Section**: unknown
- **Related Sections**: —
- **Root Cause Key**: `issue`
- **Quote Verified**: yes
- **Quote**: `so the 21 cannot be attributed to parsing alone \cite{missier-prov-2013}.`
- **Explanation**: 同类问题多处出现：(1) n8a 用 W3C PROV 综述为'本文管线无逐阶段记录故无法归因'背书；(2) n8a 'Descriptions and tags are checked against content before storage~\cite{park-metadata-quality-2009}' 用 metadata 质量综述为系统自身操作背书（综述描述的是问题，不是本系统的核查方法）；(3) n8c E5 'consistent with model turns dominating latency \cite{singh-agentic-rag}' 用 agentic RAG 综述支撑延迟构成观察。单条均可辩解，但合起来是把文献用作自身观察的权威背书，而非对话。建议将这类引用移到能被文献主张直接对应的句子（如相关工作的挑战陈述处），或删除。

## Decision Signals

- **Committee Score**: 4.0/10
- **Editor Verdict**: Desk Reject
- **Reviewer Recommendation**: Reject
- **Issue Bundle**: 15 major / 31 moderate / 20 minor

## Revision Roadmap

### Priority 3 --- Optional Improvements

- [ ] Abstract and conclusion claims need explicit evidence traceability ([LLM]; abstract)
