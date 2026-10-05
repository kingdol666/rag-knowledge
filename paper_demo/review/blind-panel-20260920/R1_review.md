# 审稿意见 R1（CIKM 2026 Demo）

审稿人视角说明：本评审仅依据投稿 PDF（5 页）与三张图（Fig 1 概念图、Fig 2 架构/工作流图、Fig 3 证据案例图）独立作出。评审重点维度：新颖性与技术稳健性。

## 论文摘要（审稿人复述，4-6 句）

论文演示 QDCVR（Query-Driven Content-Verified Retrieval），一个由 LLM 代理操作的知识组织与"可检视检索"平台。摄取侧：MinerU 将 PDF 解析为结构化 Markdown，代理读取解析内容并在既有分类库（category bases）之间做内容引导路由、维护标签、分片索引（ChromaDB/BGE-M3 向量、Neo4j 关系、Markdown+YAML 元数据），并显式核验标签与索引状态。检索侧：以"打包代理技能"形式实现协议——查询改写、跨库向量召回、0–8 分（主题 0–3 + 场景 0–3 + 证据 0–2）的提示式"内容门"自评，初始 <6 分触发 librarian 兜底（查库摘要、定向再检索、再读再评），兜底后可用 P1=5 证据支持带归因的降级回答，无可用证据则输出带范围（scope）、近似未中（near miss）与原因的 not-found 报告。演示含三个观众环节：组织一篇文档、检视一条答案的证据、检视 not-found 报告；支撑证据为 50 篇论文 / 5 库 / 165 条目上的 10 条保存轨迹（Track A/B/C 三种配置）、10 题片段回归（9/10 通过，判据为指定论文进前三且片段含至少一个字面金关键词）与 3 个脚本化语料外探针。论文反复声明：门分是代理判断而非正确性保证、轨迹是挑选与部分脚本化的记录、不主张准确率/速度/一般有效性优势；代码、轨迹与视频在 GitHub 公开。

## 评分（五个维度各 1-5 + 总评 1-5 + 推荐档）

| 维度 | 分数 | 简评 |
|---|---|---|
| 1. 新颖性 Novelty | **2 / 5** | 检索协议与 CRAG/Self-RAG 的"评估—纠正/弃答"结构同构，属提示式再实现；最有新意的"管理侧组织 + 共享编址 + 可检视记录"是整合性贡献而非技术贡献，且路由侧无任何测量。 |
| 2. 有用性 Usefulness | **3 / 5** | 对构建代理 RAG 系统的与会者有实际参考价值（溯源分级、索引核验、not-found 规范）；但演示语料仅 50 篇，可迁移经验有限。 |
| 3. 技术稳健性 Technical soundness | **3 / 5** | 声明边界异常诚实、几乎没有过度声称（这是加分项）；但门控参数无校准、招牌行为无观测轨迹支撑、回归判据弱且自认不测答案正确性。 |
| 4. 演示质量 Demo quality | **3 / 5** | 三步演示场景具体、有防超时的备用示例、视频+代码+轨迹齐全；但兜底成功路径没有任何真实记录，not-found 为预定义脚本，演示的"自适应"部分实为回放。 |
| 5. 表达与合规 Presentation & compliance | **3 / 5** | 页数合规、GenAI 披露完整；但匿名化与具名 GitHub 链接冲突、免责文字五处重复挤占篇幅、P0/P1 记号未在正文定义、图 1 存在 token/字符预算算术张力。 |
| **总评 Overall** | **3 / 5** | 真实、可复现、诚实的系统演示；但研究增量薄，演示最有卖点的两段行为（兜底、弃答）未被观测证据支撑。 |
| **推荐档** | **borderline** | 若 rebuttal 能补充至少一条非脚本化的 librarian 兜底成功轨迹 + 门控依从率统计 + 匿名化工件镜像，可升为 accept。 |

## 优点（S1, S2, ...）

**S1（声明边界异常克制，罕见且值得肯定）**。论文几乎在每个声称处同步给出反声称：摘要即写明 "Gate scores expose the agent's judgment; they do not guarantee semantic correctness"；Fig 1 标注 "Compared configurations, not a claim of accuracy superiority"；Fig 3 标注 "Gate scores are agent-authored rubric judgments, not independent correctness ratings"；Sec 4 明确 "These selected traces support an operational demonstration, not claims of answer accuracy, speed advantage, or general efficacy"。Sec 5 结论也只主张 "illustrate operation rather than establish general effectiveness"。这种自我设界在 demo 投稿中少见，大幅降低了误导读者的风险。

**S2（端到端整合 + 共享编址是论文最实的贡献点）**。Sec 1 提出 "The integration problem is to carry a document from administrative placement into evidence an agent can locate and a user can inspect"，并声称 "connects movement/tagging tools to the same document-part identifiers used by search and reading"。base/document/part/section 四级编址确实贯穿全文：Sec 2.2 的摄取核验、Sec 2.3 的证据编址、Sec 3 步骤 1 的观众操作使用同一坐标。答案结构包含 "search paths, answer, sources, confidence, and blind spots"（Sec 2.3），Sec 3 步骤 2 进一步演示 "similarity, agent judgment, and evidence are distinct" 三者分离——这一可检视性设计（尤其 blind spots 与 near-miss 字段）是 Self-RAG/CRAG/DeepRead 的原始论文中没有作为系统界面呈现的内容。

**S3（演示设计具体、可复现、有容错预案）**。Sec 3 的三个观众环节均落到具体操作与具体问题（BQ02 的 NISQ 问题、Spectral Tuning 虚构论文问题）；步骤 1 预备了 "A prepared example, explicitly identified as such, is available if live parsing would delay the session"，这是现场演示的良好工程实践。Artifacts 段给出代码、语料抓取脚本与保存轨迹的仓库链接，摘要给出视频链接，Sec 3 还明确 "ordinary web search is not presented as an equivalent execution of the skill"，防止观众误解 HTTP 检索即技能执行。

**S4（跨轨迹的溯源审计细致，对社区有方法论价值）**。Sec 4 对三条 track 的证据等级做了逐条降级说明：A 的 "scripted, fixed rewrites include expected-answer terms, precluding a fair retrieval comparison"；B 的 "file references are self-reported without retained read events"；C 的 "loses document metadata at the logging adapter, a limitation of this reproduction rather than dense retrieval"。还披露 "Resolved LLM configurations are not archived per answer, and cache state and parametric knowledge are uncontrolled" 以及 A 无端到端时延。对代理轨迹做这种分级标注，是本论文对"如何报告 agent 实验"这一社区痛点最有教育意义的部分。

**S5（GenAI 披露完整且区分系统内 LLM 用途）**。GenAI Usage Disclosure 段不仅说明写作工具（OpenAI Codex 协助文字修订、组织、工件检查、矢量图实现），还声明 "No new answer-generation experiments were run for this revision"，并区分系统内 LLM 输出（路由、评分、草拟）与确定性盘点检查，且将最终责任归于人类作者。披露的颗粒度超过多数投稿。

## 缺点（W1, W2, ...；P0 致命 / P1 重要 / P2 次要）

**W1（P1）核心检索协议新颖性有限，"content-gate + librarian fallback" 基本是 CRAG/Self-RAG 的提示式再实现。** 查询改写→召回→对候选做提示式相关性自评→低分触发追加检索与再读→无证据则弃答，与 CRAG（检索评估器 + correct/incorrect/ambiguous 三分支 + 纠正性追加检索）和 Self-RAG（ISREL/ISSUP/ISUSE 自反思令牌控制检索与生成）在控制流上同构；librarian 兜底对应 CRAG 的 corrective retrieval，not-found 对应两者的弃答路径。论文的实现是提示词技能而非学习组件，且未给出与这两类方法在任何决策点上的机制差异对照或行为差异实验。组织侧"内容引导路由到既有库"（Sec 2.2）是本可差异化的部分，但全文没有报告任何路由准确率、错误路由案例或与朴素基线（如按标题/关键词匹配既有库）的比较——"content-guided" 目前只是一个未测量的声明。Sec 1 自我定位为 "complements these approaches"，但对 complement 的论证停留在"集成问题"叙述，缺一张机制对照或一个能区分 QDCVR 与"裸 CRAG 提示"的行为实例。

**W2（P1）演示的招牌自适应行为没有以观测轨迹呈现：兜底与弃答均为脚本/预定义产物。** Sec 4 承认三个语料外例子 "combine script-collected retrieval and catalog evidence with predefined agent-authored judgments and templated not-found reports" 且 "They illustrate the reporting format, not measured autonomous abstention"；Sec 3 对 P2 的描述同样是 "a predefined, agent-authored judgment"。这意味着三段式协议（门控直答 / 兜底降级 / not-found）中，只有第一段（BQ02 的 8/8 直答）有真实观测记录；最有演示价值的第二、三段在论文证据里是回放而非行为。Sec 2.3 承认 "These instructions rely on agent compliance"，但全文没有依从率、失败模式或换用执行模型后的稳定性数据。对一篇以"可检视的代理判断"为卖点的 demo 而言，这是证据链上最大的空洞：观众在演示现场看到的自主行为是否可复现，论文无法回答。

**W3（P1）评估证据薄且判据弱，且 admittedly-incomparable 的对比占据了两张主图的版面。** 10 题回归的语料仅 50 篇、题目与"金关键词"出自作者之手（文中未说明拟定程序），通过判据是"指定论文进前三 + 合并片段含至少一个字面金词"，作者自己承认 "This checks snippet coverage, not final-answer correctness"（Sec 4），BQ06 检索命中但缺关键词即构成唯一失败。这一回归即便全过，也只说明语料内检索自查通过。与此同时，Fig 1 整幅与 Fig 3 上半幅都用于 A/B/C 三配置对照展示，而 Sec 4 已逐一声明三者不可公平比较（A 改写含答案词、B 自报读取、C 日志缺失）。视觉对称的对比版式与文字上的不可比声明相互矛盾，即便有免责脚注，仍构成对读者的优越性暗示；在 4 页正文里用约两幅主图的代价展示一个自认无效的对比，版面决策值得商榷。

**W4（P2）门控参数与记号缺乏定义与验证。** 0–8 = s_topic(0–3)+s_scenario(0–3)+s_evidence(0–2) 是全文最核心的"方法"，但三个分项的评分锚点（什么情况给 3、什么情况给 0）、阈值 6/5/4 的来源、"保留 5 条候选、丢弃 ≤4" 的依据，均无任何敏感性分析或与人工相关性判断的一致性检验；Sec 2.3 仅以 "Content-verified denotes a prompted relevance assessment, not guaranteed correctness" 带过。此外 P0/P1 记号只在图中出现（Fig 1 "P0 ≥6 / P1 =5"、Fig 2/3 "No usable P0/P1"），正文从未定义，读者需自行反推 P0=强证据、P1=5 分后备。

**W5（P2）数字与表述小疵。** (a) Fig 1 左栏 "≈800-token windows" 与同栏 "pack 2 excerpts ≤4,000-character evidence window" 算术不自洽：2×800 token 约 6,400 字符，超出 4,000 字符预算，若存在截断应说明截断点。(b) 摘要 "Saved operational traces cover 50 papers in five bases and 165 stored documents and parts" 易误读为轨迹覆盖 50 篇论文（实为 10+3 条轨迹作用于 50 篇语料）。(c) 同一组免责声明在摘要、Fig 1 注、Sec 2.3、Sec 3、Fig 3 注、Sec 4 至少五处重复，在 4 页限制下挤占了本可用于给出一条兜底成功案例的空间。(d) 系统名大小写不统一：标题用 QDCVR，摘要与结论用 "Qdcvr"。(e) "8/8" 的分式写法容易被读作 8 题对 8 题，建议写 "8（满分 8）"。

**W6（P2）匿名化与工件链接存在张力。** 作者栏为 "Author Name / Affiliation / City, Country / author@example.com"，表明投稿按匿名处理；但摘要与 Artifacts 段的链接均指向具名账号仓库（github.com/kingdol666/...）。若本 track 实行双盲评审，具名账号直接去匿名化；视频采用仓库内 blob 深链也缺乏稳定性保障。建议改用匿名镜像（如 anonymous.4open.science）并在 camera-ready 时恢复具名链接。

## 向作者的问题（Q1, Q2, ...）

**Q1（对应 W2，关键）** 在 10 条 BQ 轨迹之外，是否存在任何**非脚本化**的 librarian 兜底成功记录（初始 <6 → 再检索/再读 → P1=5 → 降级回答）？10 题中初始门分 <6 触发兜底的频次分布如何？若完全没有，能否在演示前补采若干条并提交？

**Q2（对应 W2）** "These instructions rely on agent compliance"——在不同执行模型/采样温度下，代理完整执行"先读后评→阈值分流→兜底→弃答"指令的依从率是多少？是否观察到跳过读取直接打分、或已弃答仍给答案的失败模式？

**Q3（对应 W1）** 内容引导路由：50 篇的放置有多少经过人工核对？错误路由率是多少？与"按标题/关键词匹配到既有库"的朴素基线相比，读全文内容的路由带来了多少可测量的收益？

**Q4（对应 W3）** 9/10 回归评测的是哪条 track 的检索？BQ 题目与"金关键词"由谁、在什么阶段、依据什么语料拟定？指定论文是先有题目还是先有论文？如何排除"以语料成题"的循环性？

**Q5（对应 W5a）** Fig 1 中 "≈800-token windows" 与 "2 excerpts ≤4,000 characters" 如何同时成立？两个片段合计的 token 预算到底是多少？800 token 指单元还是总量？

**Q6** 分片上限 30,000 字符远大于常见的 ~1k token 块：门控评分时代理实际读入候选文本的多少？是否存在读入截断导致评分偏低的已知案例？一次 BQ02 式查询的 token 成本/时延量级是多少？

**Q7** 41 个 kb_* 工具嵌在 94 工具总清单中：代理如何发现并选中正确工具？是否发生过工具混淆（如调用普通 HTTP 搜索代替技能）导致的失败？这是否正是 Fig 2 脚注 "web or HTTP search does not automatically enforce this policy" 想要防范的情形？

**Q8（对应 W6）** 评审期是否提供匿名化工件镜像？视频是否有独立于 GitHub 的稳定托管（以保证链接不因仓库变动失效）？

## 合规检查（页数、GenAI 声明、占位符、视频/工件链接）

| 检查项 | 结论 |
|---|---|
| 页数 | **合规**。正文（含摘要、系统、演示、证据与局限、结论、Artifacts、GenAI 披露）止于第 4 页；第 5 页仅含 8 条参考文献，符合"4 页正文 + ≤2 页仅参考文献"限制。ACM Reference Format 块标注 5 页，一致。 |
| GenAI 声明 | **有且完整**。位于第 4 页，说明工具（OpenAI Codex）、用途（文字修订、组织、工件检查、矢量图实现）、边界（未为新修订运行新的答案生成实验）、系统内 LLM 用途的区分（路由/评分/草拟 vs 确定性盘点）及人类作者责任。满足并超出披露预期。 |
| 占位符 | **基本无**。正文无 TODO/FIXME/未填数字。作者栏 "Author Name / author@example.com" 为匿名化样式（合规），但与具名 GitHub 账号链接冲突（见 W6，条件性 P1：若本 track 双盲则升级）。 |
| 视频/工件链接 | **存在**。视频：摘要中的 GitHub blob 深链 mp4；代码+语料脚本+保存轨迹：Artifacts 段仓库链接。链接具体可用，但均为具名仓库且视频为深链，建议匿名镜像 + 稳定落地页（见 Q8）。 |
| 图表合规 | 三图均为矢量渲染、信息密度高、可读；但免责脚注字号偏小，Fig 1/2/3 累计免责文字约占图面一成，进一步压缩有效信息（见 W5c）。 |

## 详细意见（按章节）

**标题与摘要。** 标题 "Agent-Operated Platform for Knowledge Organization and Inspectable Retrieval" 与内容相符，"Inspectable" 一词由答案结构与轨迹记录支撑，不算过度声称。摘要把核心免责（门分非正确性保证）写入第二句，克制但牺牲了信息密度；"165 stored documents and parts" 与 "traces cover 50 papers" 的搭配需要读者自行重组成"轨迹作用于语料"的正确理解（W5b）。

**Sec 1 引言。** 动机（管理员需组织文档并解释证据）具体、非空泛。相关工作段覆盖 Self-RAG/CRAG/DeepRead/CyBERBOT，定位语 "QDCVR complements these approaches with content-guided collection management and a reusable evidence workflow built on tool APIs" 是全文新颖性声明的准确形式——问题在于该差异仅以一句话陈述，未展开为机制对照：哪些决策点 QDCVR 有而上述工作没有？按我的阅读，答案只有"摄取/组织侧工具 + 共享编址 + 逐查询记录"，这一点完全可以（也应该）用一张小表或一个反例场景论证（W1）。三点贡献中第二条 "Reusable agent skills that coordinate tool calls" 作为研究贡献偏弱，实为工程打包方式。

**Sec 2 系统与代理工作流。** 交代坦诚：41 个 kb_* 工具嵌于 94 工具清单；"These interfaces share data and operations, not necessarily a reasoning policy: ordinary search endpoints return candidates without requiring a content-gate judgment" 明确了内容门只存在于技能层提示中——这对可复现性是必要的诚实，但也等于承认"协议"本质是一份提示词规范，任何代理框架都可直接复制，进一步压缩了系统层面的新颖性（W1）。Sec 2.2 的摄取核验（"successful upload alone does not establish complete tagging and indexing"）和"五库为演示配置而非平台限制"的说明是好细节。Sec 2.3 给出评分公式与阈值分流，是全文方法核心，但缺锚点定义与验证（W4）；"mutable file-tree metadata is not an append-only per-query audit log" 是又一处重要诚实声明——它实际上限定了"可检视"的强度：记录可查，但不是防篡改审计日志。

**Sec 3 交互演示。** 三步设计（组织文档 / 检视证据 / 检视 not-found）覆盖了写—读—败三个面，是本论文最强的部分。BQ02 案例给出了可核查的具体数字（part 2/3、相似度约 0.71、门分 8/8），并强调相似度、代理判断、证据三者可分离——这正是"可检视"的落地。步骤 3 的虚构论文探针设计得当，且明确了报告边界（"The report concerns evidence in this collection, not the existence of an answer elsewhere"）；但 P2 的判定与报告是预定义脚本这一事实虽被披露，仍使该环节的教育价值打折（W2）。步骤 2 引用 Fig 3 的 Transformer 三方对照是全文信息量最高的段落：A 的 part/section 标签系由轨迹重建、B 系自报文件名、C 弃答——把三种证据等级并排放置的做法值得推广。

**Sec 4 演示证据与局限。** 这一节是双刃剑：作为局限声明，它几乎穷尽了 agent 实验的所有已知混淆（改写含答案词、自报读取、日志适配器丢元数据、LLM 配置未逐答归档、缓存与参数知识未控、无端到端时延），我赞赏其彻底性；但它的净效果是系统性地取消了本文全部正面证据的证明力——剩下的只是"系统能运行、记录可查看"。对 demo track，"能运行 + 可检视"本可及格，但叠加 W2（兜底与弃答无观测记录）后，演示中被代理"自主"执行的部分只剩 8/8 直答一条快路径，这在证据结构上头重脚轻（W2、W3）。

**Sec 5 结论、Artifacts 与 GenAI 披露。** 结论措辞与证据等级一致（"illustrate operation rather than establish general effectiveness"），无越界。Artifacts 明示复现前提（需配置文档服务与代理模型）并声明 "stored answers are not independent ground-truth judgments"，延续了全文的克制。GenAI 披露见 S5。

**图 1（概念对比）。** 布局清晰、流程完整，右侧门控分支（≥6 直答 / 初始 <6 兜底 / P0≥6、P1=5、无可用三分出口）与正文一致；主要问题是左栏 token/字符预算不自洽（Q5）与左右对称排版暗示可比性（W3）。

**图 2（架构与工作流）。** (a) 摄取链路（PDF→MinerU→Section Markdown→代理路由/标签→切分索引→ChromaDB·Neo4j·文件树）与 (b) 在线检索链路齐全，双入口（Web HTTP/CLI 与 Agents→MCP adapter）交代清楚；脚注明确了策略仅由技能执行。问题：脚注与免责文字字号过小；正文未定义的 P0/P1 记号出现在图中（W4）。

**图 3（证据案例）。** 上半（BQ01 三方对照）信息密度高、证据分级标注到位；下半（P2 脚本探针）四步链条（BERT 近未中→记录 1/8→目录普查 165/153→NOT_FOUND）清楚，且注明 "not an autonomous benchmark"。此图是"可检视性"主张的最好视觉证据；遗憾在于其对照价值被 Sec 4 的不可比声明抵消（W3），且 P2 的预定义性质使下半图实为格式展示（W2）。

**总体判断。** 这是一篇诚实到近乎自我消解的 demo 投稿：系统真实、整合完整、记录规范、披露充分，作为工程演示有价值；但其研究增量（门控+兜底）是 CRAG/Self-RAG 控制流的提示式复刻，组织侧差异点未经测量，而演示最想展示的两类自主行为恰恰没有观测证据。给定我的评审重点（新颖性、技术稳健性），当前状态为 **borderline**：若作者能补充一条真实兜底成功轨迹、门控依从率数据、路由准确率（哪怕是 50 篇上的人工核对表），并将工件匿名化，我将愿意提升评分。
