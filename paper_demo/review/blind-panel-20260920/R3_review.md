# 审稿意见 R3（CIKM 2026 Demo）

审稿人：R3（关注点：声明—证据一致性、数字与图文互证、合规与图表呈现）。本评审仅基于稿件 PDF（5 页）与三张投稿图（fig1-concept / fig2-architecture / fig3-evidence）独立作出，未参考任何外部材料。

## 论文摘要（审稿人复述，4-6 句）

论文演示 QDCVR（Query-Driven Content-Verified Retrieval），一个由 agent 操作的知识组织与可检视检索平台：打包的 agent skills 通过工具 API（41 个 kb_* 工具 / 94 工具清单）完成 PDF 解析（MinerU）、按内容在既有五个分类库间路由、标签维护与分段寻址阅读；后端为 ChromaDB（BGE-M3 向量）+ Neo4j + 文件树/YAML 元数据。检索协议是"向量召回 → 提示式内容门控自评（0–8 分：≥6 直接引用作答，=5 作为兜底可给出带归因的限定性回答，≤4 丢弃）→ 需要时 librarian 追加检索与阅读 → 显式 not-found 报告"。交互演示设计为三个环节：整理一篇文档、检视一个答案的证据链（BQ02/NISQ，首中 part 2/3、相似度 ≈0.71、gate 8/8）、检视 not-found 报告（虚构论文 P2，BERT 近似命中但记录 1/8，最终 NOT_FOUND）。作者以 50 篇论文、5 个库、165 条 stored documents and parts 的保存轨迹，以及一个 10 题片段回归（通过 9 题，唯一失败为 BQ06）作为操作性证据，并用三个脚本化语料外探针展示失败报告格式。全文反复强调：gate 分数是 agent 的提示式判断而非正确性保证，一切对照均为配置对照，不构成效果、速度或正确性声明。

## 评分（五个维度各 1-5 + 总评 + 推荐档）

| 维度 | 分数 | 简评 |
|---|---|---|
| 1. Novelty | 3 | 相对 Self-RAG / CRAG / DeepRead / CyberBOT，新意在"内容引导的库间路由 + 分段寻址证据 + 门控/兜底/not-found 一体化的 MCP skill 封装 + 可检视轨迹"，属于整合型创新，单点技术新意有限。 |
| 2. Usefulness | 3 | 目标用户（研究数据管理员）与场景真实，工件（代码/轨迹/视频）齐全；但无用户评估，实际收益仅以"可检视性"论证。 |
| 3. Technical soundness | 4 | 就其自我设定的范围（操作演示而非效果评测）而言，声明与证据高度对齐，未发现正文与图之间的数值矛盾；扣分在于核心门控机制的可靠性零测量，以及 50/165/153 三个清点数字的关系无法从文本推出。 |
| 4. Demo quality | 4 | 三环节演示脚本具体、有准备示例兜底 live 解析延迟、视频与保存轨迹齐备；但演示数值案例集中在我称为"精选个案"（8/8 与 1/8），缺分布。 |
| 5. Presentation & compliance | 3 | 英文流畅、图为整洁矢量图；但正文（GenAI 声明段）溢出到第 5 页、作者区与 running header 为字面占位符、P0/P1/P2 记号未定义且重载、Qdcvr/QDCVR 大小写混用。 |
| **总评** | **3.5**（如需整数取 3） | 内容达到 Demo Track 水准且异常克制诚实，但存在必须修复的合规与一致性缺陷。 |
| **推荐档** | **borderline（条件性偏 accept）** | 若确认"4 页正文 + 仅参考文献附加页"规则且 GenAI 声明不计豁免，则当前版本因页数违规应拒后修改；若作者将正文收回 4 页内并修复 W2/W3，可升为 accept。 |

## 优点（附论文中的证据）

- **S1（声明—证据校准堪称典范）**。全文系统性地把"agent 判断"与"正确性"解耦：摘要"Gate scores expose the agent's judgment; they do not guarantee semantic correctness"；图 1 脚注"Scores are agent judgments"；图 3 页脚"Scores are recorded agent judgments, not independent accuracy measurements"；§4 明言三个脚本化案例"illustrate the reporting format, not measured autonomous abstention"、轨迹"support an operational demonstration, not claims of answer accuracy, speed advantage, or general efficacy"。审稿人逐条核对后未发现任何越界声明——这在 Demo 投稿中少见。
- **S2（可核对数字在图文间一致）**。我逐一互证：50 papers / 5 bases / 165 entries（摘要 = §3 = §4 = 图 3"5 bases · 165 entries"）；153 names retained（§4 = 图 3）；回归 9/10（摘要"passes nine cases" = §4"passes 9/10"，失败例具体到 BQ06 及其失败原因"lacks the required keyword"）；BQ02 的 gate 8/8（§3）、BQ01 的"Gate: 8/8 · fast exit"（图 3A）、P2 的"Recorded: 1/8"（图 3）；Track C"4,000-character context budget"（§4）与图 1"pack 2 excerpts ≤4,000-character evidence window"及图 3C"2 chunks · 2,854 characters"（2,854 ≤ 4,000，2 chunks = 2 excerpts）自洽；rubric 公式 s = s_topic + s_scenario + s_evidence，范围 0–3/0–3/0–2（§2.3，满分 8）与各图 0–8、≥6、=5、≤4 完全吻合。
- **S3（可检视性作为一等设计目标）**。§3 环节 2 让观众并排对照"similarity, agent judgment, and evidence are distinct"三重信息；环节 3 的 BERT 近似命中案例具体展示了系统拒绝用相邻文献替代（"the saved report states not-found rather than substituting BERT's recipe"），比常见的只演示成功路径更有说服力。
- **S4（局限章节覆盖面广且具体）**。§4 覆盖：跨 Track 证据窗口/配置不可比、A 的"scripted, fixed rewrites include expected-answer terms, precluding a fair retrieval comparison"（主动承认自评污染）、B 自报告无读事件、C 元数据在 logging adapter 丢失、"Resolved LLM configurations are not archived per answer, and cache state and parametric knowledge are uncontrolled"、端到端延迟不可得。§2.3 还诚实说明"mutable file-tree metadata is not an append-only per-query audit log"。
- **S5（GenAI 披露相对完整）**。专节说明工具（OpenAI Codex）、四类用途（prose 修订、稿件组织、实现与实验工件检查、矢量图实现）、"No new answer-generation experiments were run for this revision"，并区分系统内 LLM 用途（路由/评分/起草）与确定性盘点，最后落到人类作者责任。
- **S6（图面工程质量高）**。三张图均为统一风格的矢量渲染，字号在整页宽度下可读；图 3 用三栏并置呈现三种证据形态差异（保存的读取轨迹 vs 自报告文件名 vs 弃答），信息密度高而不乱。

## 缺点（具体、可操作；P0 致命 / P1 重要 / P2 次要）

- **W1（P1，页数合规）正文溢出第 5 页**。GenAI Usage Disclosure 段落跨页：第 4 页末行止于"...and"，第 5 页以"vector-figure implementation. No new answer-generation experiments..."开篇并延续 8 行，之后才是 References。若 CIKM Demo 规则为"4 页正文 + 仅参考文献的附加页"，则第 5 页含正文内容即违规（ACM Reference Format 块自报"5 pages"与实际一致，但页数合规不因此豁免）。修复：压缩 §4/披露段，或将披露段并入第 4 页；并向 chair 确认声明性内容是否计页。
- **W2（P1，记号未定义且重载）P0/P1/P2 在正文中从未定义，且一词两义**。图 1/图 2 中 P0/P1 是候选证据等级（"P0 ≥6 → Cited answer"、"P1 =5 → Qualified answer"、"No usable P0/P1 → Not found"），而图 3 标题与 §3 中"P2"是脚本化探针编号（"The scripted P2 example"）。正文 §2.3 只定义了分数语义（≥6 / =5 / ≤4），从未出现"P0/P1"字样；三个语料外探针也只描述了 P2，P0/P1 作为探针是否存在、结果如何均未交代。读者无法不猜。修复：给证据等级改名（如 direct / backstop class），探针统一编号 Probe #1–#3，并在 §2.3 与 §4 首次出现处定义。
- **W3（P1，双盲风险）工件与视频链接指向可识别的 GitHub 账号**。摘要视频链接与 §5 Artifacts 均指向 `github.com/kingdol666/rag-knowledge`，账号名"kingdol666"可能直接暴露作者身份；Demo Track 若为双盲，这构成去匿名化通道。修复：改用匿名化镜像（如 anonymous.4open.science）或 Org 级中立账号，camera-ready 再还原。
- **W4（P1，清点数字语义断裂）50 / 165 / 153 三个数字的关系无法从文本推出**。§3 称"A prepared instance contains 50 papers in five bases"，§4/摘要称 165 条"stored documents and parts"，§4 与图 3 又称普查"counts 165 catalog entries but retains 153 document names"。若 165 条均由 50 篇论文派生（文档+分片），去重后的文档名不应达到 153；若 153 是库内全部文档名（即库内不止 50 篇论文），则 §3 的"contains 50 papers"表述失准。论文对三者的口径关系零解释，属声明—证据链上的真实断裂。修复：一句话说明 165 = 文档数 + 分片数、153 是什么口径（唯一文档名？含非论文文档？跨库重名如何去重？）。
- **W5（P2，图文信息不对等）**。(a) 图 2"Cited answer — 5 sections"中的"5 sections"全文无解释（推测对应 §2.3"Answers contain search paths, answer, sources, confidence, and blind spots"五字段，但读者无法知道）；(b) 图 1"≈800-token windows"是基线分块参数，正文只字未提，且与正文字符口径（4,000-character budget、30,000-character ceiling）单位混杂，token 与 character 并置易被误读为同一量纲；(c) 图 3C"C reports: parsing + Table 4 results"的"Table 4"指涉不明（应为语料论文的表 4），caption 虽声明 paraphrased，仍宜注明"Table 4 of the source paper"。
- **W6（P2，摘要口径略夸）**。摘要"three scripted out-of-corpus examples illustrate agent-authored not-found reports"与 §4"predefined agent-authored judgments and **templated** not-found reports"存在agent 自主性口径差：正文明确这是脚本采集证据 + 预定义判断 + 模板化报告。建议摘要改为"scripted, template-based not-found reports"，消除略读歧义。
- **W7（P2，术语/排版一致性）**。(a) "Qdcvr"（摘要、§2.1、§4 Track A、§5）与"QDCVR"（标题、图、其余正文）大小写混用；(b) "librarian"（§2.3 与两图）作为组件首次出现未定义（是子 agent、skill 阶段还是函数？）；(c) 作者区与 running header 为字面占位符"Author Name / Affiliation / City, Country / author@example.com"，ACM 引用块同为"Author Name. 2026."——盲审版可接受，但建议改用 acmart 的 anonymous 模式（"Anonymous Author(s)"），避免 camera-ready 遗漏。
- **W8（P2，证据为精选个案、缺分布）**。全文只给出两个门控分数（8/8 与 1/8）与一个相似度（≈0.71），未报告 10 条 trace 的分数分布、相似度分布、兜底（=5）触发次数、librarian 回退次数；"two of ten saved answers"弃答也仅在 §4 一笔带过。回归判据本身较弱（top-3 + 字面关键词，正文已自认"This checks snippet coverage, not final-answer correctness"），在无分布的情况下难以评估工作流的真实行为面。建议在 §4 补一张小表：10 题各自的 gate 分数、路径（direct/fallback/not-found）、相似度。
- **W9（P2，图 3A 的溯源瑕疵已声明但仍显突兀）**。"A's part/section labels are reconstructed from its evidence trace"（caption）意味着展示的 §3.2.3/§7 并非原始记录字段；既然论文以"inspectability"为核心卖点，重建标签与原始 trace 字段的差异宜在正文（而非仅 caption）说明。

## 向作者的问题

- **Q1** 图 2"Cited answer — 5 sections"的"5 sections"具体何指？是否即答案记录的五个字段（search paths / answer / sources / confidence / blind spots）？如是，请在图注中说明。
- **Q2** P0/P1（图 1、2 的证据等级）的精确定义是什么？与图 3/§3 的探针编号"P2"是否同一命名体系？三个语料外探针的 P0、P1 内容与结果为何未报告？
- **Q3** 50 篇论文、165 条 entries、153 个 document names 三者的确切关系是什么？153 是"唯一文档名"还是"含非论文文档"？跨库重复如何处理？（见 W4）
- **Q4** GenAI 声明段是否计页？若不计，请提供 chair/CFP 条款；若计，请给出收回 4 页的删减方案。
- **Q5** `github.com/kingdol666` 账号与作者的关系？双盲评审期间能否提供匿名镜像？
- **Q6** 10 条保存 trace 的 gate 分数分布如何？8/8 出现的频率是多少？0.71 在相似度分布中处于什么位置？是否存在 gate 打满导致"分数无分辨力"的迹象？
- **Q7** BQ06 的"required keyword"清单何时固化？是否先于回归运行确定，以排除事后挑选？
- **Q8** 图 3C 的"2 chunks · 2,854 characters"是单条 trace；其余 9 条 Track C 回答的 chunk 数与字符数是多少？基线"≈800-token windows"用什么 tokenizer 计数，与 4,000-character 预算如何对齐比较？
- **Q9** Track A 的"A records retrieval and read times but not answer-authoring time, so its end-to-end latency is unavailable"——演示现场是否提供延迟量级，让组织者评估现场可行性？

## 合规检查（页数、GenAI 声明、占位符、视频/工件链接）

- **页数**：共 5 页（letter, acmart sigconf 双栏）。正文（至 §5 Conclusion 与 GenAI 声明）结束于第 5 页上部，References 占第 4 页右栏下部至第 5 页；第 5 页含约 8 行正文（GenAI 声明后半段）→ 疑似违反"4 页正文 + 仅参考文献附加页"，**P1**（W1）。
- **GenAI 声明**：有专节，要素较全（工具、用途清单、"无新实验"、系统内 LLM 用途与确定性检查的区分、人类责任归属），满足 CIKM 政策的实质要求；位置在正文内，页位问题见 W1。可再补一句：GenAI 协助"inspection of implementation and experiment artifacts"是否影响过任何被报告的观察值。
- **占位符**：作者区"Author Name / Affiliation / City, Country / author@example.com"；偶数页 running header 右侧"Author Name"（第 2、4 页）；ACM Reference Format 块"Author Name. 2026."。盲审版勉强可接受，但规范做法是 acmart `anonymous` 选项；终稿必须全部替换（W7c）。
- **视频/工件链接**：摘要内嵌视频链接（GitHub blob 页的 mp4，建议改 raw 直链便于播放）；§5 Artifacts 给出代码/取语料脚本/保存轨迹链接。两者同指向非匿名账号 `kingdol666` → 双盲下去匿名化风险，**P1**（W3）。审稿人未（也不应）点开验证内容，仅审查其存在性与形式。
- **图/文一致性**：所有可核对数值一致（S2）；未定义/重载记号 P0/P1/P2（W2，P1）与"5 sections / Table 4 / ≈800-token"未解释项（W5，P2）为呈现层缺陷。
- **格式**：CCS 概念与关键词齐备；三图均为跨栏浮动、有编号与说明性 caption；参考文献 8 条、格式规范（[4] DeepRead arXiv:2602.05014、[8] CyberBOT CIKM'25 与 2026 年投稿时间线自洽）；未发现明显参考文献错引。

## 详细意见（按章节）

- **标题/摘要**：标题"Agent-Operated Platform"与内容相符。摘要单段信息密度高，数字（50/5/165、9/10、三探针）与正文一致；两处口径问题：`Qdcvr` 大小写（W7a）与"agent-authored not-found reports"（W6）。视频 URL 直接嵌在摘要段内且换行断字（"rag-\nknowledge"），可读性尚可但建议移到脚注或 Artifacts 节。
- **§1 Introduction**：相关工作定位（RAG / Self-RAG / CRAG / DeepRead / CyberBOT）准确、差异化表述清晰（"content-guided collection management and a reusable evidence workflow built on tool APIs"）；三条贡献 bullet 明确。"The inspected implementation exposes 41 kb_* tools within a 94-tool inventory"给出具体规模，但无图示或截图佐证，观众无法在演示中一览 41 个工具——建议图 2 或视频给出工具清单画面。
- **§2 System and Agent Workflow**：§2.1 服务拓扑（console / FastAPI / ragctl / MCP）清楚，且诚实指出"ordinary search endpoints return candidates without requiring a content-gate judgment"（策略仅存在于 skill 层，图 2 底注亦重申）。§2.2 的 30,000 字符切分上限、"successful upload alone does not establish complete tagging and indexing"的检查语义、五库仅为演示配置等表述严谨。§2.3 的 rubric 公式与阈值链（≥6/=5/≤4 → direct/attributed/not-found）是全文技术核心，图文完全一致；"librarian"未定义（W7b）、"These instructions rely on agent compliance"是恰当的免责。
- **§3 Interactive Demonstration**：三环节脚本可操作、观众参与点明确；"A prepared example, explicitly identified as such, is available if live parsing would delay the session"体现演示工程成熟度。BQ02 数值案例（part 2/3、≈0.71、8/8）仅存在于文字——图 1 只以 BQ02 为标题做机制示意，图 3 展示的是 BQ01；建议在图 1 中以小标签标注该 trace 的实际数值，使文字声明可视化。环节 3 对 P2 的描述与图 3 下带一致（1/8、BERT near miss、165/153、NOT_FOUND）。
- **§4 Demonstration Evidence and Limitations**：全文最强的一节。三条 Track 的不可比性、脚本改写含答案词、元数据丢失、配置未归档等自我暴露充分；BQ06 失败归因具体。欠缺：分数/相似度分布（W8）、50/165/153 口径（W4）、以及 153 与"not exhaustive content inspection"之间的量化余量（12 条差额意味着什么）。
- **§5 Conclusion 与 Artifacts**：结论克制（"illustrate operation rather than establish general effectiveness"）；Artifacts 段完整，唯链接匿名性（W3）与"stored answers are not independent ground-truth judgments"的复述恰当。
- **GenAI Usage Disclosure**：内容合格（S5），页位合规问题（W1）。
- **三张图（作为渲染图单独评审）**：fig1 概念对照图清晰，机制阈值标注完整，底注免责到位；fig2 双面板架构/流程图信息密度高，(a)(b) 分区明确，虚线"Indexed evidence → recall"的存取关系可辨，但"5 sections"、"P0/P1"、"librarian shelf scan"均未在正文定义；fig3 三栏对照 + P2 带状区的叙事设计出色，"Declared unread: positional formula, training details, benchmark scores"这类负空间披露尤其好。三图均无位图噪点、无截断、无字体混杂问题；主要缺陷集中在符号学与正文联动（W2/W5），而非制图质量。

---

*评审完成于盲审条件下；所有证据均引自稿件文本与三张投稿图的可见内容。*
