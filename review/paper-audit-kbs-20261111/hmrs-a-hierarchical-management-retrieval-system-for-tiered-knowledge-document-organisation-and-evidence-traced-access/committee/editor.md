# Editor Pre-Screen — HMRS (Knowledge-Based Systems submission)

Manuscript: "HMRS: A hierarchical management retrieval system for tiered knowledge
document organisation and evidence-traced access" (24 compiled pages, elsarticle 5p two-column).
Screen basis: title, abstract, keywords, full section headings, and a desk-level pass over the
submitted sources and the rendered PDF (pages 1, 6, 14, 15, 23, 24 inspected visually).

## Editor Pre-Screen (1-10)

Score: 5/10
Verdict: Conditional Pass

条件性通过：不构成立即退稿（desk reject），但下列必须修复项若在正式投稿前未处理，将大概率被
Elsevier 编辑部行政退回（unbuild/return），或送审后因定位问题被第一批拒掉。

### Desk-Reject Triggers (if any)

无硬性触发（scope 属于 KBS 覆盖的知识管理/知识型系统范畴；语言整体可读；篇幅正常；非重复投稿，
先前的 demo 版本已在正文中披露：`A prior demonstration version introduced the organisation and
retrieval layers \cite{hmrs-demo}`）。但存在三个"近似触发"项，若不修复即投稿，行政退回或第一批
拒稿的概率很高：

1. **编译稿正文存在可见的引用损坏**（第 15 页）：正文打印出 "Section efsec:ladder-opt, and
   Section efsec:e5"。这不是渲染误差——源文件 `n8b_eval.tex` 第 134–135 行的 `\ref` 被损坏为
   换行控制符 + `ef`（字节级核实：`Section~^Mef{sec:ladder-opt}`）。交付稿中出现乱码式引用是
   编辑一眼即见的负信号，表明投稿包由过期/损坏源编译。
2. **作者区为占位符**（第 1 页："Author Name*, Co-author Name"、"author@example.com"、
   "Affiliation Department, University, City, Country"；第 23 页 CRediT 亦为 "Author 1 / Author 2"）。
   源码注释表明作者有意保留这些值（AUTHOR ACTION），但以现状投出必然被退回补全。
3. **新颖性自述为"仅集成"**（详见 Top 3 第 1 条），叠加摘要末句的全盘自我否定，存在被编辑以
   "insufficient advance over prior art" 一审拒稿的实质风险。

### Top 3 Reasons (no hedging)

1. **KBS 命题/卖点未闭合（venue fit，最大风险）。** 摘要以全盘否定收尾："These results show
   selected implemented management paths and failure boundaries, not general retrieval
   superiority, semantic answer quality or citation support."；结论同样："They do not establish
   system-level superiority, general retrieval effectiveness, semantic answer quality or
   reliability."；相关工作一节把差距定性为 "The gap this study addresses is one of integration
   and of role separation rather than of missing capabilities."。诚实值得肯定，但一篇期刊论文的
   摘要/结论若只回答"本文没证明什么"，编辑无从判断 KBS 读者获得何种可复用的知识。支撑管理层
   主张的关键对照（tiered A0h vs. precise PD）自身不可显著："A0h versus PD differs on eight
   questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction
   that does not reach the 0.05 threshold on this sample."，而检索层正面结果由现成基线拿走
   （"BM25 and RRF 1.00 vs HMRS-Hybrid 0.44"）。当前的卖点实为：可审计的管理契约 + verifier
   作为 ranker 的负结果 + 传输层失效分析。投稿前必须把这一正面命题在摘要首句和结论里明写，
   否则 desk 阶段就有"系统报告而非知识型系统贡献"的定性风险。

2. **交付稿的呈现基线不合格（presentation）。** 除上述第 15 页引用乱码外：(a) 摘要第二句语法
   失败——"a self-hosted knowledge document management system managing documents at three
   levels---collection, document and segment---and answers along a tiered path narrowing from
   the catalogue of collections"，"managing ... and answers" 平行结构断裂，且"answers along a
   tiered path"不成句；(b) 标题 "A hierarchical management retrieval system for tiered knowledge
   document organisation and evidence-traced access" 是四层名词堆叠（hierarchical × management ×
   retrieval × tiered），无连词，难以解析；(c) E5b 小节先定义 "S1 pinned the target shelf, S2
   left the library unpinned, and S3 pinned it with a hybrid-retrieval directive"，随后成本却按
   未定义的 "Mean cost was \$0.182 (A), \$0.300 (B) and \$0.219 (C)" 报告，读者无法对号；(d)
   正文使用未定义的内部专名 "Experience retrieval and SOUL reuse knowledge-base infrastructure"
   （SOUL 全文无展开）与 "persona-distillation workflows that are outside the scope of this
   evaluation"；(e) 参考文献被手工压到 7.2 pt、条目间距 0pt（`main_20p.tex` 导言区自述：
   "Tight item separation and 7.2 pt type keep the current list within this local 20-page preview
   budget"），第 23–24 页实际观感极小，属于为页数预算操纵排版，投稿版应恢复正常字号。

3. **摘要/讨论/结论与新加入的 E2c 节脱节（internal consistency）。** E2c（标注日期 2026-11-11，
   即本次审计当日）报告了全文唯一一次"分层路径 vs. 放弃导航"的同语料受控对照（A0h 72.2% vs.
   PD 63.9%），并自称 "The head-to-head contrast is the one the management claim rests on"；
   但摘要、讨论与结论均未提及该对照，讨论反而仍把它列为缺失的未来工作："Broader claims
   require independent questions, repeated trials, claim-level support checks, controlled
   hierarchy comparisons in which the tiered path is contrasted with a flat baseline over the
   same corpus, operator studies and crash-recovery tests."；结论同样写 "controlled hierarchy
   comparisons, larger multi-collection corpora in which the collection tier can be contrasted
   against flat and per-collection baselines"。同一件事在 8.4 节是"已做、方向一致但不显著"，
   在讨论/结论里是"尚缺、需要做"——叙事未随新增实验更新，编辑阶段即可判定为内部不一致。

### Fast Fixes (within 1-2 days)

- 修复 `n8b_eval.tex` 第 134–135 行损坏的 `\ref`（现为孤立 CR + `ef`），重编译并全文检查其余
  交叉引用；交付 PDF 不得含 "Section efsec:..." 类乱码。
- 摘要第二句改为平行结构（例如 "...system that manages documents at three levels (collection,
  document, segment) and answers questions along a tiered path..."），并通读摘要压缩数字密度
  （现摘要约 19 个数值）。
- 重写摘要首句与结论首段，明写正面命题：可审计的三层管理契约、collection 层可独立测量、
  verifier-as-ranker 负结果对部署者的警示；把"未证明什么"降为限定从句。
- 同步摘要/讨论/结论与 E2c：三层文本均应出现 A0h-vs-PD（72.2% vs. 63.9%，McNemar p=0.0703，
  方向一致未达显著），并删除/改写"缺 controlled hierarchy comparisons"的过时表述。
- 填入真实作者、单位、通讯邮箱与 CRediT 姓名（现为占位符），或按 KBS 双盲要求做匿名化——
  两者取一，不可保留 "Author Name / author@example.com"。
- 统一 E5b 臂标签（S1/S2/S3 与 (A)/(B)/(C) 取一套）。
- 展开 SOUL 与 persona-distillation 为可理解的术语，或移入附录/删除。
- 参考文献字号恢复到 elsarticle 默认（约 8–9 pt），页数预算问题交由排版微调而非压字号。

### Score Justification

- 加分项：研究问题在引言中可辨识（"The question we study is therefore not how to rank passages
  better, but how a document collection should be \emph{managed} so that a query can be served
  tier by tier---selecting a collection, then a document, then a segment---and so that each tier
  can be audited independently."）；五个 RQ 有映射；评价披露的诚实度远高于常见投稿；图表基础
  良好（图 4/5/6 可读，表 3/4 结构清晰）；有 highlights、CRediT、数据可用性、GenAI 声明等
  Elsevier 要件。
- 扣分项：可见引用乱码（-）；摘要语法与名词堆叠标题（-）；venue-fit 命题未闭合（-）；摘要/
  讨论与 E2c 脱节（-）；占位作者区（-）；为页数预算压缩参考文献字号（-）。
- 综合：5/10 —— 修复上述机械性问题并重构正面命题后，可送审；否则行政退回或第一批拒稿风险高。

### Lane Boundary

本审查仅覆盖 desk-reject 筛查面（pitch、venue fit、呈现基线、标题/摘要/关键词完整性、框架
一致性）。数字已对照冻结实验工件核验，不在本轮重审；方法论与文献面对由其他评审负责。
