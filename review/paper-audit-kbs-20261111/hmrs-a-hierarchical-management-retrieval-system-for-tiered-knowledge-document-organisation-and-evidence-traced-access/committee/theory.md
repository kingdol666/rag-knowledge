# Committee Reviewer 1 — Theory / Contribution 评审（HMRS）

## Theory Contribution Review

### Contribution Strength: 4 / 10

这是一篇诚实度罕见、但理论增量单薄的论文。它是真实实现、真实测过的系统（95 个 MCP 工具、三个语料、多组冻结工件），其声称的边界几乎每一处都自带否定式限定，这在系统类投稿中值得肯定。但以理论/贡献标准衡量：核心构件（"management-level model"、三条 management contracts、tiered narrowing）是描述性分类而非可证伪命题；论文自称贡献所系的那条证据链（collection-selection tier 的收益）在其自身的评估中要么被混杂污染、要么不显著、要么测出"无差异"；与最接近的先行工作（RAPTOR、GraphRAG、DeepRead）的区分停留在重新定义层面，没有任何实验性交锋；相对作者自己的 demo 论文（\cite{hmrs-demo}）的增量主要是审计证据而非新知识。若本文消失，随之消失的可迁移知识大致只有一条：在同池重放归因下，LLM verifier 分数作为 ranker 有害、作为阈值过滤器在一个混淆密集语料上未被检验——且该发现只在单一语料上成立。

### 3 Fatal Theory Holes

1. **论文自己承认"管理主张"所依赖的头对头对照不显著，全文因此没有任何一个阳性结果支撑其核心架构论点。**
   位置：n8a_eval.tex, Section E2c（第 5.4 节）。
   原文："The head-to-head contrast is the one the management claim rests on: A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample."
   这句话等于作者亲口承认：分层导航 vs 放弃导航（precise/flat）的对照——即"层级化管理结构优于扁平检索"这一贡献命题的唯一直接检验——方向一致但 $p=0.0703$，不达显著。叠加两个事实：(a) 路由审计是脚本探针且存在未记录回退混杂（"This was a scripted route-card probe, not an LLM agent selecting a library."；"traces do not record whether the fallback ran"）；(b) E8 唯一的 scope 消融显示不限定库与钉死金库结果相同（见弱点 4 的引文）。三处证据合起来，论文的核心命题——"决定查询哪个 collection 的管理层是系统价值所在"——在其自己的数据里从未被正面确立。论文的措辞诚实没有错，错在贡献清单仍然把未确立的命题作为贡献出售（"The contribution claimed here is the management structure that decides which collection is consulted"）。

2. **引言贡献第 4 条断言"风险在排序而非过滤"，而 E4 正文明确承认过滤从未被检验——贡献陈述与正文证据直接矛盾。**
   位置：n1_intro.tex Contributions 第 4 条 vs n8b_eval.tex Section E4。
   引言原文："score-based ordering lowers Hit@5 from 0.94 to 0.44, while fusion order among recorded survivors restores 0.94, and all 191 recorded scores exceed the configured 0.5 threshold, so the measurable risk lies in ordering rather than in filtering"
   E4 正文原文："Because every logged candidate survived the configured 0.5 threshold, the filter replay is identical to fusion order by construction and does not test filtering."
   "rather than in filtering" 是一个对比性排除结论：它暗示过滤已被检验且无罪。但正文说明 filter replay 因所有候选都过阈而与 fusion order 构造性恒等——过滤的排异能力根本未被测试（E4 另一处亦承认 "it does not show a retrieval benefit from thresholding"）。可检验的正确表述是"ordering 被证明有害、filtering 在本池上未被激活因而未受检"。这是典型的把"未观测到危害"写成"危害不在该处"的内部矛盾，且发生在贡献清单这一读者最常引用的位置。

3. **"三条管理契约"被称作 hypotheses，却没有任何一条被表述为可证伪的普遍命题；核心机制"逐层收窄"没有形式化安全性质，而论文自己的数据显示收窄会丢证据。**
   位置：n3_overview.tex Section 3.2；n3_overview.tex Section 3.1；n8a_eval.tex Section E2b。
   原文一："The three management contracts are hypotheses about where the managed collection should govern the workflow, implemented at different layers: some checks are mechanically enforced by server-side tools, whereas classification and answer abstention also depend on the calling workflow, which is where the hypotheses are weakest."
   原文二："Every step narrows the scope the next step must consider, and each step has a denominator"
   原文三："An attribution of the 35 A0 misses locates five in window truncation and thirty in judge or candidate-selection failure"
   三条"契约"（content classifies / a tier narrows / scope is reported）没有给出适用总体、判据和推翻条件——它们是对本系统工作流指令的命名（第 3 条更被作者自己承认只是 prompt：'This is not a server-side semantic classifier'）。"narrowing" 这一核心机制没有任何召回保持条件或形式性质；而 A0 分层基线的 containment 只有 51.4%（37/72），35 个 miss 中 30 个归因于 judge 或候选选择失败——收窄丢金是论文自己测出的架构性行为，却被当作轶事报告而非作为 narrowing 的代价加以分析。给工程实践起名为"契约/hypotheses"并不能使之成为理论。

### Main Strengths

1. **声明卫生（claim hygiene）是我近年所见最严格的之一。** 摘要即自我封顶："These results show selected implemented management paths and failure boundaries, not general retrieval superiority, semantic answer quality or citation support."；related work 主动拆掉自己的 gap："The gap this study addresses is one of integration and of role separation rather than of missing capabilities." 与 "It proposes no new ranking algorithm and does not claim that the underlying retrieval problem is solved."；实现节区分"实现了什么"与"campaign 用了什么"（"We distinguish implemented functions from functions exercised by the reported campaigns."）。这种诚实应被明确表扬，并应成为其他系统论文的模板。

2. **同池重放的 verifier 角色归因是全文唯一真正可迁移的发现，且方法学干净。** E4 用同一日志候选池、同一分数只变角色："All three see the same candidates and scores, so the comparison is an attribution, not a benchmark."；sign test $p=0.008$、Q2 解剖图（金文档从 fusion rank 1 降到 rank 8、跌出读窗）以及换 NLI 检查点复现失败（E6: "Replacing the judge checkpoint is not the repair."）共同构成对 verifier-as-ranker 文献（Self-RAG/CRAG 一系）一个有用的否定性数据点。其局限是单一语料且作者自认 "The collapse did not recur on a second corpus."

3. **失败记账与边界分析有真实工程价值。** 21/100 不可召回且归因不完整（"the missing 21 cannot be attributed to parsing alone"）、rename 陈旧索引缺陷、74.9 KB 货架目录超出工具输出预算导致的假拒绝及其修复（"The failure is a transport limit, not a ranking error"）——这些是社区少有人写下来的部署层真相。

### Main Weaknesses（三大致命伤之外）

4. **系统自身引以为傲的集成在检索端测出负收益或零收益，"integration as contribution" 缺少任何阳性测量。** E4："Nothing here is a retrieval advance: three configurations tie at Hit@5 1.00, and the one using only words leads on MRR."（工业语料 BM25 Hit@5 1.00 vs HMRS-Hybrid 0.44）；E8 唯一触及 scope 价值的消融："searched the 20 live libraries, including 15 outside the five-library evaluation corpus, and matches the gold-pinned result in this ten-question setup"（不限库 = 钉死金库）；E2c 阶梯对照不显著（见致命伤 1）。三处合观，管理/分层结构在论文自己的测量里没有产生一次可检出的正向贡献。

5. **与最接近先行工作的区分停留在"重新定义管辖对象"，没有任何实验性交锋。** related work 原文："HMRS differs in what the hierarchy governs." 以及 "DeepRead demonstrates structure-aware navigation for agentic search; HMRS similarly exposes a catalogue-first librarian lane"。RAPTOR/GraphRAG 的层级是"一次性生成的索引"，HMRS 的层级是"每次生命周期操作后重写的管理结构"——这个概念区分成立，但论文从未测试"管理结构"相对"每次变更后重建检索层级"的任何优势；DeepRead 作为最相近的 catalogue-first 导航先行者，delta 只有一句 "similarly exposes"，未说明也未测量。

6. **定位句提出了论文未检验的因果前提。** related work 原文："HMRS treats acquisition quality, automatic classification and traceable indexing as prerequisites for reliable retrieval rather than as preprocessing assumptions." 而 E4 的 BM25 基线 "runs in process over the fetched full texts" 并以约一毫秒一次的调用达到 Hit@5 1.00（"hits Hit@5 1.00 at about a millisecond per in-process call"）——即在本文自己的数据里，不经任何管理层的全文词法检索就已完美，"prerequisite" 的因果主张与自家结果相抵。

7. **贡献清单存在"审计即贡献"的包装膨胀。** 贡献第 2 条以 "Collection-level evidence." 领衔，其内容是 "A 100-paper campaign produced 322 stored parts in five libraries, of which 79 were retrievable and 21 were not with incomplete failure attribution"——一个无法归因的内部失败计数是问责数据，不是他人可用的知识；贡献第 3 条的主体是天花板饱和的 60/60 金 ID 覆盖（正文自认 "These saturated deterministic measures do not establish semantic support"）。两条合起来把有界内部审计升格为编号贡献，稀释了真正的发现。

8. **摘要对 72/72 结果的表述省略了"脚本探针"这一关键边界。** 摘要原文："In a 72-question route audit, the collection-selection arm returned the gold collection for 72/72 and name-only for 37/72, though an unlogged fallback could use descriptions." 摘要披露了回退混杂（好），但 "scripted route-card probe, not an LLM agent selecting a library" 这一限定只出现在 5.3 节；摘要读者会把 72/72 归因于系统的 collection-selection 能力。建议摘要加一个词（scripted）。

9. **相对作者自己 demo 论文的增量是审计证据而非新系统或新理论。** 原文："The architecture and access path build on that version; the contribution claimed here is the additional evidence and failure analysis, not a wholly new system." 结合上述"增量证据多为零/饱和/混杂/单语料"的事实，期刊级增量问题（increment test：本文消失后什么知识消失）的答案偏薄。

### What The Paper Is Actually Contributing (1 sentence, no marketing)

一个诚实记录的自托管文档管理系统，加上一条单语料同池重放诊断（LLM verifier 分数作为 ranker 有害、其阈值过滤未被激活因而未受检）和若干有价值的部署失败案例；其"管理级模型"是对标准工程实践（目录树+元数据+分块索引+准入门控）的命名，其架构主张在自身评估中未获阳性支持。

### How To Fix (2-4 concrete moves)

- **把管理主张做实一次**：在平衡问题集、足够样本量下重跑 tiered vs flat vs precise 三臂对照（并加入"每次生命周期操作后重建 RAPTOR 式索引"这一真正的层级基线），使 "management claim rests on" 的那条对照达到显著；做不到就应把贡献清单降格为"系统+审计报告"，删除以管理层为核心卖点的表述。
- **形式化三条契约与 narrowing 性质**：把每条 contract 写成可证伪命题（适用总体、判据、推翻条件），并给 tier narrowing 一个明确的召回保持条件；然后用 35 个 A0 miss 的数据检验该条件何时被违反。
- **修复路由审计的混杂并测真实代理**：记录 fallback 是否触发，并加一个真正的 LLM-agent 选库臂，使 collection-selection tier 有一个无混杂、非脚本的测量。
- **让"ordering 而非 filtering"成立**：在第三个语料/第二个 judge 家族上复现 ordering 失败，并补一个更高阈值的 answer-level 过滤测试；同时把引言贡献第 4 条的 "rather than in filtering" 改为与 E4 一致的表述（filtering 未被检验）。
