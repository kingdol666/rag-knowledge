# 引用一致性审计报告 —— HMRS / Knowledge-Based Systems 正本

- **审计对象**：`paper-kbs/tex/journal_20p/main_20p.tex`（20 页投稿正本）及 `n*.tex`
- **审计日期**：2026-11-14（第二轮，用户要求"检查引用的时机和位置是否与文献内容一致"）
- **范围**：本轮引入的 **32 个引用键**（27 条新增 KBS 文献 + 5 条补引用的孤儿键），并对既有引用做抽样检查
- **结论**：**发现 1 处成组的位置错配（P0）与 5 处描述不符（P1），已全部修正**，见第 5 节

---

## 1. 方法与证据（不凭印象）

| 证据 | 来源 | 说明 |
|:--|:--|:--|
| 文献实际内容 | `kbs_abstract_evidence.json` | `audit_citation_evidence.py` 用 pypdf 抽取 29 篇 PDF 前两页与 `Abstract` 窗口，逐篇人工比对 |
| 条目题名 | `bib_titles.json` | 97 条定义条目的 title / DOI / year |
| 引用上下文 | `citation_contexts.json` | 87 个 `\cite` 位置各自所在 section 与前 420 / 后 220 字符 |

判定标准：①**内容一致**——紧邻句子的断言必须能被该文献题名/摘要直接支持，不得过度诠释；②**位置一致**——引用必须落在论证该主题的小节与句子里，不能为凑数塞进相邻但不同主题的小节；③**时机一致**——引用句不能打断原有叙述流，且并列引用不能把不同主题的文献绑到同一个限定语下。

---

## 2. 问题汇总（P0–P2）

| 级别 | 数量 | 问题 | 涉及键 |
|:--|:--|:--|:--|
| **P0** | 1 组（5 键） | §2.3「Verification, correction and abstention」新增段落把 5 篇**与验证/可信性/弃答无关**的系统工程与持续学习文献，整体归入 "on the trustworthiness side"。位置与论证主题错配，会误导读者把这些文献读成验证/弃答相关工作 | `mohamed2026orchestra`, `liu2026automatin`, `chen2026enhancing`, `sorokin2023sigopt`, `wu2025informati` |
| **P1** | 5 | 正文断言与文献实际内容不符或缺乏证据 | `dai2025large`, `sorokin2023sigopt`, `gallofr2021jkpdesign`, `feng-abstain`/`yin-knowwhat`（并列限定语）, `hou2025msdiagnos` |
| **P2** | 3 | 引用时机/措辞可改进 | `wu2025informati`（应归 memory 段）, `n8a_eval.tex` 插入点打断运行设置叙述, `siddharth2024retrieval` 描述可更精确 |

---

## 3. 逐条判定（32 条）

> 判定列：`OK` = 内容与位置均一致；`P0/P1/P2` = 见第 2 节。

### 3.1 §2.1 Knowledge management and document acquisition（10 条）

| 键 | 正文断言（缩写） | 文献实际内容（摘要证据） | 判定 | 处理 |
|:--|:--|:--|:--|:--|
| `ocaa2023software` | 软件参考架构，文献+原型推导，模块职责与架构原则 | KBS 276 (2023) 110750：提出 JKP 软件参考架构，design grounded on literature + prototype experience，含架构原则与 PoC | OK | 保留 |
| `gallofr2021jkpdesign` | "its **design-science derivation** is documented separately" | CEUR-WS Vol-2978 摘要只说 "outlines a software reference architecture ... along with a proof-of-concept"；**无 design-science 方法学表述** | **P1** | 改为 "an earlier workshop version outlines the architecture and a proof-of-concept" |
| `yang2024building` | 图语义模型的知识接地对话系统 | 题名即 "Building knowledge-grounded dialogue systems with graph-based semantic modelling" | OK | 保留 |
| `budur2024building` | 低资源语言 OpenQA 系统 | 题名一致；摘要为 OpenQA 从非结构化知识源检索段落作答 | OK | 保留 |
| `vito2025heliot` | LLM 临床决策支持系统 | HELIOT: LLM-Based CDSS for adverse drug reaction management | OK | 保留 |
| `aarab2024system` | 银行监管者 IR 系统 | 摘要 "we introduce a novel IR System tailored to assist supervisors" | OK | 保留 |
| `liao2026practical` | 隐私保护服务框架 | 题名 "A practical and privacy-preserving framework for real-world LLM services" | OK | 保留 |
| `garridomer2026gofai` | LLM 辅助构建专家系统 | 题名 "Development of expert systems by means of large language models" | OK | 保留 |
| `hou2025method` | operator–function 描述构建领域知识库 | Geo-FuB：为地理空间代码生成构建 Operator-Function KB | OK | 保留 |
| `ciatto2025large` | LLM 生成领域知识以实例化本体 | 题名 "LLMs as oracles for instantiating ontologies with domain-specific knowledge" | OK | 保留 |

### 3.2 §2.2 Retrieval, organisation and agentic search（9 条）

| 键 | 正文断言（缩写） | 文献实际内容 | 判定 | 处理 |
|:--|:--|:--|:--|:--|
| `siddharth2024retrieval` | 工程设计知识上的 RAG | 题名一致；摘要更精确为"从专利描述抽取工程设计事实三元组以支撑 RAG" | **P2** | 题名直接支持现写法，保留（不做超出摘要的细述） |
| `peng2024soft` | 软提示调优稠密检索 | 题名一致 | OK | 保留 |
| `massai2023evaluatio` | 语义关系查询扩展的检索系统评测 | 题名 "Evaluation of semantic relations impact in query expansion-based retrieval systems" | OK | 保留 |
| `zan2025private` | 私有库检索支撑代码生成 | 摘要证实 APIFinder 用**向量检索**从 API 文档取 API、APICoder 再生成代码 | OK | 保留 |
| `dai2025large` | "knowledge graphs serve as a **reasoning substrate**" | 摘要实为研究 **LLM 如何理解不同 prompt 格式/组织的 KG 信息**（linearized triples → fluent text），并非把 KG 当推理基底 | **P1** | 改为 "studying how LLMs comprehend knowledge-graph facts supplied in different prompt formats" |
| `huang2025prompting` | 长尾事实问答的 KG 提示 | 题名一致 | OK | 保留（与上一键合并为并列句） |
| `tao2025fine` | 细粒度状态化知识探索经 LLM 导航图 | 题名 "Fine-grained Stateful Knowledge Exploration: graph retrieval with LLMs" | OK | 保留 |
| `sinha2026finbloom` | 实时金融数据知识接地 | 摘要 "real-time information ... finance ... recent news or price movements" | OK | 保留 |
| `saadaoui2025coordinat` | 协同多智能体答案生成 | 题名 "Coordinated LLM multi-agent systems for collaborative question-answer generation" | OK | 保留 |

### 3.3 §2.3 Verification, correction and abstention（8 条 + 孤儿键 2 条）

| 键 | 正文断言（缩写） | 文献实际内容 | 判定 | 处理 |
|:--|:--|:--|:--|:--|
| `saeed2023explainab` | XAI 系统元综述 | 摘要 "presents a systematic meta-survey for challenges..." | OK | 保留 |
| `zhou2026lgmt` | 逻辑接地的推理可靠性变形测试 | 题名/摘要一致（LGMT, logically equivalent transformations） | OK | 保留 |
| `hou2025msdiagnos` | "multi-step clinical **reasoning**" | 题名为 "multi-step clinical **diagnosis**"；摘要讲 primary/differential/final diagnosis | **P1** | 改为 "multi-step clinical diagnosis" |
| `wu2025informati` | 与 XAI/可靠性测试并列，归 "trustworthiness side" | 实为**持续学习的信息论双记忆系统**（continual learning, 抗遗忘），与可信性无关 | **P0 + P2** | 移出该段，改放到本节开头的 agent memory 段，并改为准确描述 |
| `mohamed2026orchestra` | 同上，归 "trustworthiness side" | 开源多 Agent 框架 + 生物医学 KG 证据富集 | **P0** | 移至 §2.1 系统工程列举 |
| `liu2026automatin` | 同上 | 工程数据驱动建模的 LLM Agent 系统 | **P0** | 移至 §2.1 |
| `chen2026enhancing` | 同上 | 端到端电路分析 LLM 系统 | **P0** | 移至 §2.1 |
| `sorokin2023sigopt` | 同上；且称 "automated **model evaluation**" | SigOpt Mulch 实为 GBT **超参黑箱优化 / AutoML**（model-aware tuning），不是模型评估 | **P0 + P1** | 移至 §2.1，并改为 "automated hyperparameter tuning for gradient-boosted trees" |
| `feng-abstain`, `yin-knowwhat` | 与 `kamath` 并列于 "Selective prediction **under domain shift**" | 两篇分别是 "Don't Hallucinate, Abstain"、"Do LLMs Know What They Don't Know?"，**不研究 domain shift** | **P1** | 拆成独立并列项，去掉共同限定语 |

### 3.4 `n8a_eval.tex` Measures and controls（3 条孤儿键）

| 键 | 正文断言 | 文献实际内容 | 判定 | 处理 |
|:--|:--|:--|:--|:--|
| `es-ragas-2024`, `saad-falcon-ares-2024` | "Automated RAG evaluation frameworks ... target semantic answer quality and graded relevance" | RAGAs / ARES 确为 RAG 自动评测框架（答案质量、忠实度等） | **P2** | 与 cumulated-gain 分开陈述，避免两类指标共用一个宾语 |
| `jarvelin-cumulated-gain-2002` | 同上，"graded relevance" | "Cumulated gain-based evaluation of IR techniques"，确为排序的 graded relevance | **P2** | 同上；并把引用句移到指标定义句之后（现插入点落在 "Agent arms use one model..." 与 "answer-layer campaigns..." 之间，打断运行设置叙述） |

### 3.5 既有引用抽样（6 条，未改动）

| 键 | 位置 | 判定 |
|:--|:--|:--|
| `yang-kbs-llm-2025` | §2.1 "Studies of LLM integration with knowledge-based methods..." | OK，题名即本刊综述 |
| `ghali-kbs-retrieval-2025` | §2.2 "combine semantic retrieval, vector storage and language models" | OK，摘要证实 "combines generative capabilities of LLMs with ... vector databases" |
| `li-kbs-rmrsst-2026` / `shen-kbs-teierag-2026` / `kinalioglu-kbs-eprag-2026` | §2.2 / §2.3 | 按 bib 题名与紧邻断言一致；这三篇**未在本次文献包中下载全文**，故只按题名/元数据核验，不做内容级断言 |
| `hmrs-demo` | 未引用 | 正确：本项目前置 demo 论文，双盲评审下不引用 |

---

## 4. 关键结论

1. **"引用是否出现"与"引用是否正确"是两件事。** 上一轮保证了 27 条键全部 `\cite` 且全部进入 `.bbl`，但为了把它们塞进三个小节，把 5 篇系统/持续学习文献放进了「验证与弃答」小节——这是本轮查出的最主要缺陷，属于**位置错配**，不是格式错误，编译与引文检查脚本都发现不了。
2. **两处描述属于凭题名臆断**：`dai2025large`（"reasoning substrate"）、`sorokin2023sigopt`（"automated model evaluation"）。摘要证据直接否定这两种说法。
3. **一个无证据的方法学标签**：CEUR 前驱论文被写成 "design-science derivation"，其摘要并无该方法学表述。
4. **并列引用会传递错误限定**：把两篇讲"模型知其所不知"的文献并列在 "under domain shift" 下，等价于声称它们研究域偏移。

---

## 5. 修正方案（已实施）

| # | 文件 | 修正 |
|:--|:--|:--|
| 1 | `n2_related.tex` §2.1 | CEUR 描述改为 "earlier workshop version outlines the architecture and a proof-of-concept"；新增一句以准确描述纳入 4 篇系统工程文献（KG-Orchestra / 工程建模 Agent / 电路分析 / GBT 超参 AutoML），落在"本刊完整系统类贡献"论证处 |
| 2 | `n2_related.tex` §2.2 | KG 句改写为「从 LLM 如何理解不同 prompt 格式的 KG 事实，到用 KG 提示回答长尾事实」，分别对应 `dai2025large` 与 `huang2025prompting` |
| 3 | `n2_related.tex` §2.3 memory 段 | 追加一句准确描述 `wu2025informati` 为持续学习的双记忆系统 |
| 4 | `n2_related.tex` §2.3 selective prediction 句 | 拆分为独立并列项，去掉共同限定语 "under domain shift" |
| 5 | `n2_related.tex` §2.3 新增段 | 重写为纯可信性/评测三篇（XAI 元综述 / LGMT / MSDiagnosis），差异句保留；`hou2025msdiagnos` 改为 "clinical diagnosis" |
| 6 | `n8a_eval.tex` | 评测框架句移到指标定义之后，并把 RAGAs/ARES（生成答案语义质量）与 cumulated gain（排序 graded relevance）分开陈述 |

**约束保持**：27 条新增键 + 5 条孤儿键仍全部被引用；`hmrs-demo` 仍不引用；零未定义引用。

---

## 6. 复核结果（修正后实测）

**约束复核**：`paper-kbs/notes/verify_citation_fix.py` **15/15 PASS**，逐项为

```
[PASS] all 27 integrated keys still cited
[PASS] all 5 orphan keys still cited
[PASS] no undefined citations
[PASS] only hmrs-demo left uncited
[PASS] 4 system-engineering keys moved to sec 2.1
[PASS] those 4 keys absent from sec 2.3
[PASS] wu2025informati in memory paragraph
[PASS] no 'trustworthiness side' framing left
[PASS] disproved phrase removed: design-science derivation
[PASS] disproved phrase removed: reasoning substrate
[PASS] disproved phrase removed: automated model evaluation
[PASS] disproved phrase removed: clinical reasoning
[PASS] domain-shift key group split
[PASS] evaluation sentence moved next to metric definition
[PASS] RAGAs/ARES separated from cumulated gain
[summary] 15/15 checks passed | cited=96 defined=97
```

**重新编译**（`pdflatex → bibtex → pdflatex ×2`，TeX Live 2025）：

| 项 | 结果 |
|:--|:--|
| `main_20p.pdf` | **20 页 / 4,004,525 B**（与修正前同为 20 页） |
| `main_20p.bbl` | **96 条 `\bibitem`**，27 条新增仍逐条在列 |
| LaTeX 错误 / 未定义引用 / >15pt overfull | **0 / 0 / 0** |
| `main_20p.log` 内 `undefined` / `! ` 匹配 | **无** |
| BibTeX 告警 | 仍为 5 条 `empty pages`（4 条原有 + CEUR companion），未新增 |

**重新生成的证据**：`audit_citation_evidence.py` 重跑后引用点由 87 → **88**
（因 `kamath` 与 `feng-abstain,yin-knowwhat` 拆成两个独立引用点），
`citation_contexts.json` 已更新为修正后版本，可据此复核每个键的新位置。

**仍存在的边界（如实说明）**：`li-kbs-rmrsst-2026`、`shen-kbs-teierag-2026`、
`kinalioglu-kbs-eprag-2026` 三篇既有 KBS 引用未在本次文献包中下载全文，
只按 bib 题名/元数据核验，未做摘要级内容断言；若投稿前需要 100% 覆盖，
应补下这三篇 OA 全文再核一遍。
