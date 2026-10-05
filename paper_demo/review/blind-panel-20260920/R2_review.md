# 审稿意见 R2（CIKM 2026 Demo）

审稿人视角：工业界工程师，长期构建并现场运行系统 Demo。本评审以**社区有用性（Usefulness）与演示质量/可复现性（Demo Quality / Reproducibility）**为主要透镜，仅依据稿件正文与三幅图独立作出判断。

## 论文摘要（审稿人复述，4-6 句）

论文提出 QDCVR（Query-Driven Content-Verified Retrieval），一个由 agent 操作的知识组织与可检验检索平台，面向需要整理论文集合并追溯答案证据的研究管理员。系统由 Web 控制台、FastAPI 后端、ragctl CLI 与 MCP server 组成，打包的 agent skill 调用 41 个 `kb_*` 工具完成文档解析（MinerU）、按内容在既有分类库（base）间路由、打标、检索与按偏移读段。检索协议为：向量召回 → 提示式"内容门"自评（0–8 分：主题 0–3、场景 0–3、证据 0–2）→ 低于 6 分触发 librarian 回退（继续检索/重读）→ 显式 not-found 报告；门分被明确定位为 agent 判断而非正确性保证。演示含三个环节（整理文档、核对答案证据、查看 not-found 报告），基于 5 个 base、50 篇论文、165 条存储记录的留痕；十题片段级回归通过 9/10，另三个库外探针为脚本化预置判断。代码、语料抓取脚本与留痕在 GitHub 公开，演示视频链接置于摘要。

## 评分（五个维度各 1-5 + 总评 1-5 + 推荐档）

| 维度 | 分数 | 简评 |
|---|---|---|
| 1. 新颖性 Novelty | 3 | 单项技术（自评门、纠错式 RAG、agent 工具化 KB 管理）均有先例；贡献在集成方式——管理侧"放置/打标"与检索侧"搜索/读段"共享同一套文档-分部标识符，加上显式 not-found 语义。对 Demo 而言足够，但不构成研究 novelty。 |
| 2. 社区有用性 Usefulness | 3 | 对构建 agentic KB/RAG 系统的实践者有可迁移的模式（共享 part ID、门分透明化、scoped not-found）；对"研究管理员"这一目标用户的普适性偏窄，且全部证据为 50 篇论文的小语料。 |
| 3. 技术可靠性 Technical soundness | 3 | 表述异常克制、内部自洽、几乎无过度声明；扣分在于 0–8 门从未与任何外部正确性标准校验，回归判据为"top-3 命中 + 字面关键词"的片段级检查，三个库外探针为预置判断。 |
| 4. 演示质量 Demo quality | 3 | 参会者"做什么"写得具体（见 S1），有解析延迟的降级预案；但无任何端到端延迟数字（文中自认"end-to-end latency is unavailable"），第三环节完全脚本化，工件复现需要"配置好的文档服务 + agent harness/model"而稿件未说明打包方式。 |
| 5. 表达与合规 Presentation & compliance | 3 | 行文密集但诚实，图 1–3 专业且自带免责说明；作者栏为占位符却出现真实 GitHub 用户名链接（匿名性矛盾），GenAI 声明延续到第 5 页（正文限 4 页、第 5 页仅允许参考文献的口径下存疑）。 |

**总评：3 / 5。推荐档：borderline（偏接受）。** 若作者在 rebuttal 中补齐：门分/harness/模型的可复现打包（Docker、命名模型版本）、留痕中的实测每步延迟、以及至少一个真机运行的 not-found 演示，并澄清匿名与页数问题，可升至 accept。

## 优点（S1, S2, ... 每条附论文中的证据）

- **S1（演示场景设计具体、参会者动作清晰）**：第 3 节给出三个编号环节，每一步都指明参会者实际操作与观察对象——(1) 选一个 PDF 与入库位置，让 agent 解析并按内容整理，"compare the parsed text with the proposed category, inspects the parts, and checks tags and indexing status"；(2) 用 BQ02（NISQ）问题核对证据：首个命中为 NISQ 论文 part 2/3、相似度约 0.71、agent 门分 8/8 走直接回答路径，"Attendees open the source and compare it with the answer: similarity, agent judgment, and evidence are distinct"；(3) 用虚构论文探针查看 not-found 报告的 near miss 与检索范围。这是 Demo 稿里少见的、可照着执行的脚本。
- **S2（证据表述罕见地诚实、克制）**：全文反复且一致地限制声明范围——摘要即写明 "Gate scores expose the agent's judgment; they do not guarantee semantic correctness"；图 1 标注 "Compared configurations, not a claim of accuracy superiority"；第 4 节承认库外探针 "illustrate the reporting format, not measured autonomous abstention"，并披露 "C explicitly abstains in two of ten saved answers"、"mutable file-tree metadata is not an append-only per-query audit log"、A 轨固定改写"include expected-answer terms, precluding a fair retrieval comparison"。对演示类论文而言，这种自我设界能有效防止观众误读，值得肯定。
- **S3（工件与实现面具体、可定位）**：Artifacts 段给出代码、语料抓取脚本与留痕的公开仓库；正文给出足够细的实现坐标：FastAPI + ragctl + MCP server、"41 kb_* knowledge-management tools within a 94-tool inventory"、MinerU 解析、30,000 字符分部上限、行偏移续读、ChromaDB/BGE-M3 向量库、答案记录字段（"search paths, answer, sources, confidence, and blind spots"）。这些数字与命名让审稿人相信系统真实存在且可被找到。
- **S4（问题定义切中真实痛点）**：第 1 节的集成命题准确——"carry a document from administrative placement into evidence an agent can locate and a user can inspect"，并以"QDCVR connects move-/tagging tools to the same document-part identifiers used by search and reading"落到机制；"Attendees can therefore inspect a routing decision and then follow the placed document into an answer or a scoped failure report" 把组织与检索闭环成一条可检验链路。scoped not-found（scope + near miss + reason）是一个可直接复用的交互模式。
- **S5（对现场风险有部分预案）**：第 3 节为解析延迟准备了降级路径——"A prepared example, explicitly identified as such, is available if live parsing would delay the session"，且明确区分真机操作与预置样例（"explicitly identified as such"），说明作者有展台意识（但答案路径的延迟预案缺失，见 W1）。

## 缺点（W1, W2, ... 每条具体、可操作，注明严重度 P0 致命 / P1 重要 / P2 次要）

- **W1（P1）现场演示的关键可行性数据缺失：端到端延迟为零披露。** 第 4 节自认 "A records retrieval and read times but not answer-authoring time, so its end-to-end latency is unavailable"，而全文未给出任何一个实测延迟数字。QDCVR 的完整循环是 query 改写 → 向量召回 → 读候选 → 0–8 门评 → （<6 时）librarian 二次检索/重读 → 再评 → 生成答案，多步 LLM 循环在展台可能以分钟计。稿件只对**解析**环节准备了降级样例，对**问答**环节没有任何"若真机循环卡顿/超时怎么办"的预案。可操作建议：从已有留痕中报告每步实测时延与预期真机墙钟时间；在演示脚本中写明超时切换到留痕回放的触发条件。
- **W2（P1）可复现性包装不足：核心配置未命名、未归档、未见打包方案。** 结论段写 "Reproduction requires configured document services and an agent harness/model"，但全文**未命名**产生留痕的 LLM 与 agent harness；第 4 节自认 "Resolved LLM configurations are not archived per answer, and cache state and parametric knowledge are uncontrolled"。0–8 门分与改写行为强依赖模型与提示版本，这意味着论文里的留痕（8/8、1/8、0.71 等）在稿件描述范围内不可复现；稿件也未提及 Docker/一条命令安装/种子数据脚本等打包手段。可操作建议：命名模型与 harness 及版本、提供 docker-compose + 语料种子脚本、按答案归档解析后的 LLM 配置。
- **W3（P1）第三演示环节完全脚本化，not-found 能力未被真机展示。** 第 4 节明确三个库外探针 "combine script-collected retrieval and catalog evidence with predefined agent-authored judgments and templated not-found reports"，即参会者在环节 3 看到的是"预置的 agent 判断 + 模板化报告"，而非系统真实决策。论文对此很诚实（"illustrate the reporting format, not measured autonomous abstention"），但对 Demo 评审而言，最有卖点的行为（显式 not-found 而非张冠李戴，如 BERT near miss 得 1/8 后仍不冒名作答）恰恰只有录播没有实况。可操作建议：展台增加至少一次真机库外探针；或视频中收录一段真机运行的 not-found。
- **W4（P1）匿名性自相矛盾（若本轨双盲则升级为合规违规）。** 作者栏为占位符（"Author Name / Affiliation / City, Country / author@example.com"，ACM 引用格式同样写 "Author Name. 2026."），但摘要的视频链接与结论的工件链接均指向 `https://github.com/kingdol666/...`——真实用户名直接去匿名。若本轨为双盲评审，这是 P1 合规问题（需换匿名仓库或匿名化镜像）；若非双盲，作者栏占位符本身就是待修项。请作者明示本轨匿名政策并统一处理。
- **W5（P2）评审性证据整体偏薄，且仅剩片段级口径。** 留痕规模为 10 题 + 3 探针、50 篇论文；回归判据为"指定论文进 top-3 且合并片段含至少一个字面金标关键词"，文中自认 "This checks snippet coverage, not final-answer correctness"；唯一失败案例 BQ06 也没有错误分析（缺的是哪个关键词、为何缺失）。作为运营性 spot check 可以接受，但离"能让 attendee 判断系统好不好用"还有距离。可操作建议：补充 BQ06 的失败解剖与 1–2 个门的错分案例（高分错配/低分漏配）。
- **W6（P2）关键数字口径与术语混乱。** (a) "165 stored documents and parts"（摘要、第 4 节）与 "catalog census covers five bases and 165 entries... 153 names retained"（第 3 节）的关系未定义——165 是文档+分部之和还是目录条目？153 丢的 12 个是什么？(b) P0/P1 在图 1 中是答案等级标签（"P0 ≥6 / P1 =5"），在第 3 节与图 3 中 "P2" 又是探针编号，同一符号两种含义且未定义；(c) 图 1 中 ≈800-token 窗口与 ≤4,000-character 证据窗并存（2×800 token ≈ 6,400 字符已超 4,000），token/char 两套预算如何叠加需说明（图 3 的 "2 chunks · 2,854 characters" 暗示实际片段远小于窗口上限，但应写明）。可操作建议：给出清单口径定义、改名探针编号、统一或对照标注两套预算单位。
- **W7（P2）Neo4j 的存在价值未在演示中体现。** 第 2 节写 "Graph navigation is optional, not the evaluated retrieval route"，图 2 也只把它列在存储层；那么它对参会者可见什么？若环节 1–3 都不触及图能力，它在演示环境里只增加部署与讲解负担。可操作建议：要么给 30 秒的图导航展示点（如文档关系在 not-found near-miss 中的作用），要么从演示装机中移除并在正文说明。

## 向作者的问题（Q1, Q2, ...）

- **Q1**：留痕 A 中记录的 retrieval/read 实测时间是多少？完整 agent 循环（含 librarian 回退）在真机上预期墙钟时间是多少？若展台上循环卡死或超过几分钟，演示脚本如何降级？
- **Q2**：产生留痕的 LLM 与 agent harness 具体是什么（名称/版本/提示版本）？既然"Resolved LLM configurations are not archived per answer"，审稿人或复现者在相机就绪前能否拿到逐答案配置？
- **Q3**：三个库外探针为何不设计为展台真机运行？如果理由是延迟或脆弱性，是否意味着 not-found 行为尚未稳定到可以现场展示？视频中是否有任何一段真机 not-found？
- **Q4**：请精确定义 "165 stored documents and parts" 与 "165 catalog entries / 153 names retained" 的清点口径，并解释 165→153 的差异。
- **Q5**：本轨评审是否双盲？若是，如何处理摘要与结论中 `kingdol666` 用户名的去匿名问题；若否，作者栏为何保留占位符？
- **Q6**：GenAI 使用声明延续到第 5 页——按"正文 4 页 + 参考文献另计"的口径，该部分是否计入正文？作者能否压缩回第 4 页？
- **Q7**：图 1 中 ≈800-token 窗口、2 个摘录与 ≤4,000 字符预算如何同时成立？BQ01 案例的 "2 chunks · 2,854 characters" 是否代表典型取值？
- **Q8**：图 1/图 2 中的 P0/P1 标签与第 3 节的 "P2 example" 是否同一体系？请在正文给出定义或改用不同记号。

## 合规检查（页数、GenAI 声明、占位符、视频/工件链接）

- **页数**：PDF 共 5 页。正文（摘要至第 5 节 + Artifacts 段）与 GenAI 声明的大部分在第 1–4 页；**GenAI 声明余下约三分之一栏延续至第 5 页顶部**，其后为参考文献。若规则为"正文 4 页、第 5 页仅参考文献"，声明溢出构成边缘违规（取决于声明是否计入正文，见 Q6）——按 P2 记录，建议压缩。
- **GenAI 声明**：存在且质量高——点名工具（OpenAI Codex）、列明用途（文字润色、稿件组织、实现与实验工件检查、矢量图实现）、声明"本次修订未运行新的答案生成实验"、给出人类作者责任条款。**符合要求**，可作为同类稿件范例。
- **占位符**：作者名/单位/邮箱/ACM 引用格式均为占位符（"Author Name"、"author@example.com"）。若为双盲投稿可接受；但与 W4 的真实 GitHub 用户名构成矛盾，须统一。
- **视频/工件链接**：视频为 GitHub blob 直链（`.../blob/master/paper_demo/video/qdcvr-demo.mp4`），置于摘要且第 5 节再次指认——链接**存在且一致**，但未给出时长、未提供第二托管（如 YouTube/会议服务器），blob 直链对大 mp4 不稳健；工件为同一仓库（代码 + 语料抓取脚本 + 留痕），无 DOI/存档（如 Zenodo）。建议提供时长与冗余链接、为相机就绪版做存档 DOI。审稿人未验证链接内容可访问（盲评以稿件文本为准）。

## 详细意见（按章节）

**摘要**：信息密度高、声明克制（门分非正确性保证的限定前置），视频链接入摘要是明确但少见的做法（可接受）。"165 stored documents and parts" 未定义即出现（W6a）。摘要声称留痕覆盖"50 papers in five bases and 165 stored documents and parts"与第 4 节一致，但与 P2 例的"census"口径需统一。

**第 1 节 Introduction**：定位清晰，把 QDCVR 与 Self-RAG/Corrective RAG（自适应处理）、DeepRead（结构坐标）、CyberBOT（本体接地）区分开，落点在"放置→可定位→可检验"的集成问题——这是全文最强的一段论证。文献覆盖面足够用于 Demo 稿。

**第 2 节 System and Agent Workflow**：实现面具体（41/94 工具、30,000 字符上限、行偏移续读、五 base 为演示配置而非平台限制），且有两处难得的诚实：成功上传不等于完成打标索引（"successful upload alone does not establish complete tagging and indexing"）、文件树元数据不是 append-only 审计日志。0–8 评分细则（主题 0–3 + 场景 0–3 + 证据 0–2）首次完整给出，但"score 5 作为回退"与"score ≥6 直接回答"的边界完全依赖提示遵从（"These instructions rely on agent compliance"），论文承认却未给出任何遵从率或错分观察（关联 W5）。图 2 清晰，脚注"Skills execute gate / retry / classification; web or HTTP search does not automatically enforce this policy"是重要的防误读设计；Neo4j 角色含糊（W7）。

**第 3 节 Interactive Demonstration**：本稿最佳章节。三个环节均有"参会者做什么 + 看什么 + 得出什么"的完整闭环，BQ02 的 0.71/8/8 与 P2 的 1/8 是具体可核对的展示点；"ordinary web search is not presented as an equivalent execution of the skill" 避免了常见的演示误导。不足：环节 3 为脚本化（W3）；对问答环节无延迟预案（W1）；"165 entries / 153 names" 口径混乱（W6a）。

**第 4 节 Demonstration Evidence and Limitations**：限制清单的完整程度超出多数 Demo 稿（脚本化改写含期望词、B 的文件来源为自报、C 的日志适配器丢元数据且明确归因于"this reproduction rather than dense retrieval"、LLM 配置未归档、缓存与参数知识未控、端到端延迟不可得）。问题在于把限制叠加之后，稿件剩余可主张的结论几乎为零——这作为诚实的代价可以理解，但也暴露出证据层的单薄：9/10 只是片段级、无错误分析（W5）。图 3 的三卡对比（part/section 标签 vs 自报文件名 vs 弃权）信息量大，"1706.03762" 的自报来源是很好的具象化。

**第 5 节 Conclusion 与 Artifacts**：结论克制（"saved cases illustrate operation rather than establish general effectiveness; compliance with the workflow and complete run provenance remain important validation requirements"），与正文一致。Artifacts 段链接齐备但复现门槛未包装（W2）。

**图件总体评价**：三图风格统一、可读性好、图注自带免责声明（图 1 "not a claim of accuracy superiority"、图 3 "not independent accuracy measurements"），这是同类稿件中少见的规范。扣分点：图 1 token/字符两套预算并存的混淆（W6c）、P0/P1 记号未定义（W6b）。

**给 PC 的综合意见**：这是一份"设计合格、包装未完成"的演示投稿。现场脚本与诚实边界是真实的强项；决定其成败的是展台上能否稳定走完一次真机循环（延迟未知）与工件能否被第三方低成本复现（目前稿件层面不能）。在 borderline 档，若 rebuttal 能回应 W1–W3 中的任意两项并澄清 W4/W6，我愿意上调至 accept。
