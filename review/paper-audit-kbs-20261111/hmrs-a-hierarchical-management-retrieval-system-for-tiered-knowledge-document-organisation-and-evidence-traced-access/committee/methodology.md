# 委员会评审人 2 —— 方法学透明度与评价公平性审查

论文:HMRS: A Hierarchical Management Retrieval System for Tiered Knowledge Document Organisation and Evidence-Traced Access(投稿 Knowledge-Based Systems)
审查范围:实验设计合理性、基线公平性与完备性、指标操作化、统计报告(Wilson CI、精确 McNemar)、样本量与多重比较诚实性、混杂与污染控制、可复现性披露、threats 与实验缺口的匹配度。数值已由冻结工件预核对,本审查只评判数值周围的方法学。

## Methodology Transparency Review (SRQR-aware)

### 总体评分(Methodology Score)

**6.5 / 10。**

理由:本稿在"披露诚实度"上属于罕见的第一梯队——指标逐一定义(MRR@5、⌈3n/5⌉ 多数规则、containment 与答案质量的区分)、跨语料数值明确不合并("Numbers are reported against the corpus that produced them, never merged")、推导行明确标注为归因而非基准、负结果(p=0.0703、E6 verifier 失败、E7 41% 超时)全部保留并冻结工件哈希。但**评价公平性与统计推断**两端有结构性缺口:(a) 全文没有任何已发表的外部系统基线,所有对比都是自身组件或自身消融;(b) 被称为 "the paper's end-to-end evidence" 的 E5 网格只有 10 题、单次运行、指标已在天花板;(c) 同一 72 题上十余个配对 McNemar 检验无多重比较控制;(d) 承载收集层核心证据的 11 月轨迹被数据声明宣布为不公开;(e) E8 暴露的 LLM 评分 0→5 摆动量级未被写入 threats。透明度高不能替代设计上缺失的对照与功效。

### 优势(Strengths)

1. **指标操作化罕见地精确。** 每个 family 的定义、单位与失效模式都被写出,且明确拒绝越界解读:"These checks support traceability and marker-presence claims, not semantic faithfulness or claim-to-source support, for which model-based measures such as RAGAS or ARES are designed." 对 containment 亦然:"it is a mechanical full-corpus containment upper bound, not a careful-agent retrieval or QA baseline."
2. **配对设计与配对检验总体正确。** 路由审计用同一 72 题做 A0/A3 配对并报精确 McNemar(p=5.82e-11,35–0 discordant);E4 的三配置同池归因用精确符号检验(8/8,p=0.008,数值与排列一致);比例配 Wilson 95% 区间且在 16 题上明确承认区间过宽("the decomposition below, not the point estimates, is the claim")。
3. **归因式对比与基准式对比被显式分开。** "All three see the same candidates and scores, so the comparison is an attribution, not a benchmark";filter-replay 的退化解("identical to fusion order by construction and does not test filtering")没有被当成过滤有效性的证据,这是很多系统论文会犯的错误,本稿主动规避了。
4. **负结果与失效分析完整保留。** verifier 作为 ranker 失败(E6)、gate 无答案级收益(E8)、平台臂更慢更贵(E5)、S2 传输失败(E5b)、E3 批准路径从未行使,全部如实报告且配工件路径;"Merge and split were never exercised under controlled conditions, so we claim nothing about them" 是模范句式。
5. **混杂自我诊断到位(多数情况下)。** 例如路由审计的回退混杂:"In A3, the route cards were created without descriptions, but the fallback could still read the original descriptions; traces do not record whether the fallback ran. Thus, the observed A0/A3 difference is not an isolated causal estimate of description removal." 以及放置正确性唯一无文件名混杂的测量被明确圈出:"the membership measurement of Section~\ref{sec:e1} is the only placement-correctness figure in this paper that avoids this confound"。

### MUST-FIX(投稿阻断项)

1. **【基线公平性 | major】无任何外部系统基线,管理层的增益主张缺乏参照系。**
   锚点(n8b, E4):"Nothing here is a retrieval advance: three configurations tie at Hit@5 1.00, and the one using only words leads on MRR."
   相关工作引用了 GraphRAG、LightRAG、RAPTOR 等层次化/结构化方案,但 E4 的九个配置与 E2c 的全部内容层臂都是 HMRS 自身组件或其消融;唯一直接检验"分层 vs 放弃导航"的对比 A0h vs PD 并不显著(p=0.0703),而简单 BM25 在工业语料上已经 Hit@5=1.00、arXiv 语料上除 Graph 外全部 0.90。在此条件下,标题所主张的分层管理结构相对于现有技术的净收益无法被量化。至少需要:(a) 运行一个已发表的层次化 RAG/知识管理基线,或 (b) 将论文的贡献定位收缩为"审计方法学与失效分析",并在摘要/贡献中移除任何比较优势的暗示。

2. **【方法学 | major】端到端证据承载在 10 题、单次运行、已封顶的网格上,而最难的语料从未进入答案层。**
   锚点(n8a, Sec. Eval 开篇):"answer-layer checks per question and abstention (Section~\ref{sec:e5}, the paper's end-to-end evidence)"
   E5 的 gold-ID 检查在两个网格共 60 格全部命中(threats 亦承认 "grounding is at ceiling"),检索端在小语料上近乎完美,因此该网格几乎不可能暴露任何层级退化;与此同时,唯一检索不完美的十域语料(72 题,containment 51.4%–72.2%,35 个 A0 miss)只有 containment 诊断,没有任何答案层评估。被冠以 "the paper's end-to-end evidence" 的实验恰好是最不可能失败的设计,要么在十域语料上补答案层评估,要么把该短语降格为"答案层行为观察"。

3. **【混杂 | major】路由审计的 72/72 由脚本化匹配器产生,且 52/72 问题为"automatically expanded"、扩展来源未披露。**
   锚点(n8a, E2b):"The question set is unbalanced across domains (52/72 questions were automatically expanded, with 47/72 drawn from three domains), so it does not estimate performance on a balanced domain sample."
   论文已正确声明 A0/A3 差异"不是对描述移除的因果估计",但扩展问题的构造来源(从域标签?从 gold 文档生成?)完全未披露,存在问题文本向 gold 域标签泄漏的可能;叠加 47/72 集中于三个英语域,贡献列表中"returned the gold knowledge base for 72/72 questions"这条证据的构造过程必须完整披露(扩展脚本、种子、是否接触 gold 标签),否则应降低该结果的表述强度。

4. **【可复现性 | major】承载收集层与 ladder 核心证据的 11 月轨迹不公开,逐题复核不可能。**
   锚点(n_back, Data availability):"November 2026 route traces are not public; the authors retain them for requests subject to source-document restrictions."
   E2b(11-02/03)、A1b/A2 重跑(11-10)、E2c ladder 优化(11-11)全部是 11 月产物,恰是论文管理层主张的主要证据;数据声明却规定这些轨迹不公开。审稿人无法独立复核 A0h vs PD 的 7–1 discordance、A0 35 个 miss 的归因(5 truncation / 30 judge)或 A3 的 11 个零字节用例;42 文档工业语料同样不公开("not deposited publicly")。要么在投稿前存放去标识化轨迹(作者自己的注释也承认此事待决),要么把所有基于 11 月轨迹的结论标注为"仅聚合统计可核"。

### SHOULD-FIX(质量改进项)

5. **【统计报告 | moderate】从非显著检验写出 "matches or exceeds" 的等同式结论。**
   锚点(n8a, E2c):"A0h versus PD differs on eight questions (seven A0h-only, one PD-only; exact McNemar $p=0.0703$), a consistent direction that does not reach the 0.05 threshold on this sample."
   同段随后写 "Tiered navigation plus the chunk union therefore matches or exceeds abandoning navigation"。不显著只能支持"未检测到差异",不能支持"matches or exceeds";等效主张需要等效边际与功效分析(均未提供,n=72、8 个 discordant 的功效极低)。建议改为"数值上更高但不显著"并给出最小可检差异。

6. **【统计报告 | moderate】同一 72 题上十余个配对 McNemar 检验无多重比较控制。**
   锚点(n8a, E2c):"All rates are gold-string containment over the 72 questions, with Wilson 95\% intervals and exact paired McNemar tests against the tiered baseline A0"
   E2c 对 6 个臂各做一次对 A0 的配对检验,再加 A0h vs PD、E2b 的两个配对检验、E5 两网格间的多个 McNemar;全文未出现任何校正声明,threats 亦未讨论。p=6.1e-5 对任意校正稳健,但 PD p=0.0039、A0f p=0.0078、A2 p=0.0227 这类边缘显著支撑着"A0f repairs eight, A0h fifteen"的递进叙述,应声明未校正并做 Holm 敏感性说明。

7. **【混杂 | moderate】E2c 效率主张只计搜索调用次数,不计判官 token/字节预算。**
   锚点(n8a, E2c):"matches or exceeds abandoning navigation while issuing roughly a tenth of the search calls"
   A0h 给判官喂入全窗口加 chunk-window 并集,每题判官输入很可能接近或超过 PD;containment 指标本身偏向送入更多原文的臂(read-all 机械上限 72/72 即为证)。路由审计报告了字节与秒数,E2c 却只报告对自己有利的调用数维度,无 token、字节或 wall-clock。效率口径不完整构成维度选择性偏置。

8. **【混杂 | moderate】同一输入下 LLM 评分摆动 0→5、3→0,该测量噪声量级未推广到 threats。**
   锚点(n8c, E8):"downstream LLM grades varied in both directions (QK01 $0\to5$ and QK03 $3\to0$ under the same twelve-document, 4{,}000-character pack; sign test $p=1.0$, $n=10$)"
   候选集与证据包完全固定时评分在量表两端翻转,说明答案级 LLM 评分的运行间噪声可达满量程;该量级超过 E8 的全部组间效应,而 threats 只写 "each arm was run once",未把噪声量级推广为对一切依赖 LLM 评分与 E5b answer gate 的单次比较的测量误差警告。

9. **【可复现性 | moderate】答案网格的任务契约、harness prompt 与模型标识不可复现。**
   锚点(n8a, Controls):"recorded in the run timeline as claude-opus-4-8[1m] with seed~0 and harness prompt v4-neutral"
   "one task contract" 的 prompt 文本、"v4-neutral" 的内容与版本均未给出;"claude-opus-4-8[1m]" 是内部运行标签而非可引用模型版本(无快照日期);对托管模型声明 seed 0 不能保证可复现。E8 已证明结论对 prompt/评分敏感,缺失 prompt 文本使答案层实验严格不可复现。

10. **【基线公平性 | moderate】被评估的 hybrid wrapper 已退役,在售混合通道从未做工具层检索基准。**
    锚点(n8b, E4):"The evaluated hybrid wrapper is no longer registered in the current tool layer, whose hybrid lane is the composed chat configuration of Section~\ref{sec:twostage}, so the negative ordering result below is bounded to that retired wrapper."
    限定是诚实的,但后果是:系统当前的 hybrid lane 只在 10 题答案网格中出现过,从未在 E4 语料上有检索质量测量;表 tab:retrieval 的 "HMRS-Hybrid" 行描述作者自己已移除的组件。应在表内显著标注 retired,并给出现行 composed lane 的等价测量或不可测的原因。

11. **【方法学 | moderate】E5b 设计汇总表与正文不一致(3 臂×6 题 vs 3 题×3 臂),"file-tree arm" 结论错行,S1/S2/S3 与 (A)/(B)/(C) 未对应。**
    锚点(n8a, tab:retrieval-design):"Three arms $\times$ six questions, public API & Cost, latency, refusal behaviour & Platform arm slower and dearer than the file-tree arm"
    正文定义 E5b 为 "Three questions (an English methodology question, a Chinese clinical question and an out-of-corpus probe) crossed three deployment arms",六问题属于 honesty battery,"file-tree arm" 是 E5 的对照;成本报告改用 "(A), (B), (C)"("Mean cost was \$0.182 (A), \$0.300 (B) and \$0.219 (C)")而映射未给出。设计汇总表是读者的实验地图,此处失真必须修正。

12. **【方法学 | moderate】21 篇不可检索论文失败归因缺失,采集失败诊断停留在语料级。**
    锚点(n8a, E1):"neither attempts against failed papers nor per-paper parse status is recorded, so the 21 cannot be attributed to parsing alone"
    一个以"可审计状态"为卖点的系统,其采集层自身只有聚合计数(91 in state file / 79 retrievable / 12+9=21),失败模式仅两句轶事("formula-dense scans and one tool-layer crash")。该自反性缺口应在 threats 中显式承认。

13. **【方法学 | moderate】threats 与实验实际缺口的四处错配。**
    锚点(n8b, E3):"One scenario and thirteen candidates cannot support an effectiveness claim; scheduled distillation, review and approval at scale, application feedback and credibility decay went unexercised."
    threats 总体罕见详尽,但遗漏:(a) 多重比较(见第 6 条);(b) E8 评分噪声量级(第 8 条);(c) "现行 composed lane 未被基准化"的外推边界(第 10 条);(d) 经验子系统(E3)批准路径从未行使、证据近零的状态完全未进 threats。

14. **【统计报告 | moderate】单次运行的非确定 agent 泳道配 Wilson 比例区间,低估总不确定性。**
    锚点(n8a, Controls):"The tool-layer retrieval lanes, grading rule, audits, duplicate adjudication and cross-lingual ingestion pipeline are deterministic; agent lanes and text-derived results are not."
    Wilson 区间只把"题目"当随机源;对承认非确定的 agent 泳道,运行间方差成分完全未估计,而 E8 的 0→5 摆动证明其不可忽略。至少应声明区间条件于单次运行,或补小规模重复运行给出方差下界。

15. **【混杂 | moderate】A1b/A2 于 11-10 更换协议后与 11-02/03 的 A0/A0f/A0h/PD/A3 同图比较。**
    锚点(n8a, E2b):"The flat and no-gate arms (A1b, A2) were re-run on 2026-11-10 as scoped per-library directed searches merged by score, replacing an earlier unscoped protocol"
    重跑已披露,但跨日期、跨协议的同图可比性风险未讨论——尤其论文在其他处强调 snapshot 差异不可合并("a different snapshot, and the two grids are not pooled")。应说明两日期间语料/索引快照是否逐位一致。

16. **【基线公平性 | minor】延迟列混合进程内基线与工具层通道。**
    锚点(n8b, E4):"neither is the platform's keyword tool, so the millisecond latencies are in-process measurements rather than a server round trip."
    正文已区分,但表格同一列并排 0.9 ms 与 542 ms,未按 substrate 加注;建议表内分组或加脚注。

17. **【混杂 | minor】测量前修复的两处故障恰属于 E2 所测失效类别。**
    锚点(n8a, Controls):"Before measurement we repaired two corpus-integrity faults through the platform's own operations: one document missing from its vector collection was re-indexed, and one library whose collection had been lost was rebuilt, the same failure class that Section~\ref{sec:e2} measures."
    E2 的一致性结果因此条件于"无未修复自然失效"的状态;自然失效率从未报告,修复与被测同源(均经平台自身操作)。

18. **【方法学 | minor】nDCG@5 已计算但不报告,构成轻度选择性报告。**
    锚点(n8a, Metric families):"nDCG@5~\cite{jarvelin-cumulated-gain-2002} was computed only inside one exploratory arm we do not report."
    一句关于该臂结果方向或弃用原因的说明即可消除疑问。

19. **【方法学 | minor】"carry repeats" 与 "one final observation per arm" 表述冲突。**
    锚点(n8a, Controls):"the 27-cell stability suite (Section~\ref{sec:e7}) and the eighteen-arm honesty battery (Section~\ref{sec:sysarms}) carry repeats"
    threats 写 "The refusal battery has one final observation per arm after two MCP-mount interruptions were rerun"。两处对同一实验重复结构的口径应统一:哪些臂有真重复观测、哪些只是失败重跑。

20. **【方法学 | minor】E7 缓存修复只重测部分读路径,完整 sweep 未声明重跑。**
    锚点(n8c, E7):"A later cache repair lowered the 30-client read-ladder \emph{p50} from 1577 to 65.8\,ms and repeated-query \emph{p50} from 3743 to 2.1\,ms; distinct queries remained near 4--5 requests per second under a process-wide lock."
    41% 超时来自修复前完整 sweep;修复后只引用两个选定指标,未说明超时率是否复测。同一小节内前后两个系统状态的测量协议不同,应声明。

### SRQR Checklist Deltas(以系统论文的对应物映射)

- **Sampling rationale(抽样理由):** 四个语料均为便利样本(自有演示实例、自投 arXiv、Wikipedia、自建十域),无独立抽样框;问题为开发者编写而非日志抽样:"The sixteen industrial questions were authored, not sampled from logs"。抽样理由部分给出(压力测试、近重复密度),但"为何这 100 篇 arXiv、为何这十个域"无可复核的选择规则。
- **Data collection details(采集细节):** 路由审计与 ladder 有日期(2–3 Nov、11 Nov 2026),答案网格有 run ID;运行环境为单工作站("Tests ran on one local workstation");但模型快照版本、harness prompt 文本、任务契约缺失(见 MUST-FIX 相关条),时长与资源(除 E7 外)未系统报告。
- **Coding process(编码/评分过程):** 确定性评分类似"编码本"且定义精确(⌈3n/5⌉、别名感知、marker 模式);但 LLM 评分与"fabrication checks were manual"无第二评分者、无一致性度量,E8 的 0→5 摆动说明该"编码"信道方差未控制。
- **Saturation(饱和/功效):** 定量研究无饱和概念,对应物是功效分析——全文无任何先验功效或样本量论证;E2c 事后承认 "the sample is too small to claim a significant advantage",E8 仅 8 个 gold-matchable 问题,均属事后知晓欠功效。
- **Triangulation(三角验证):** 三源一致性(disk/tree/metadata)是设计上的三角验证,但只在 33/322 样本上执行;两网格、多泳道、多语料的"never merged"纪律是另一种三角验证纪律,执行良好。
- **Reflexivity(反身性):** 开发者编写问题、开发者运行系统、开发者人工复核 fabrication("Questions and gold annotations were developer-authored"),论文承认了这一点,但没有任何独立性机制(外部标注者、预注册假设、盲评);Q16 文件名泄漏的敏感性检查是全文唯一的"对抗自身设计"的检查,方向正确但覆盖单一。

---

*审查人:Committee Reviewer 2(Methodology)。所有锚点引文已对照 tex 源文件逐字核对;数值未重新验证,以冻结工件为准。*
