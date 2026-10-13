# ref-context.md — 维度2+3：公开背景参考（**非本项目数据**）

> ⚠ **本文件全部为「背景参考」**，来源为公开网页/论文（URL+标题可核查），用于给 PPT 的汇报口径与视觉叙事提供外部锚点。
> **严禁与本项目实测数字混写**：本项目数字一律见 `ref-experiment-data.md`（均来自 `review/retrieval-e2e-20261012/` 与 `benchmark-suite/results/runs/` 落盘工件）。
> 采集日期：2026-10-12 · 检索工具：open-websearch（bing）+ 页面直取（WebFetch）

---

## 维度2：RAG / 检索评测的常见报告口径（背景锚点，3 条）

### 2.1 BEIR —— 检索有效性用统一指标横评，同时把"计算成本"当一等维度

- 来源：Mirco Nogueira 等《BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models》，arXiv:2104.08663，<https://arxiv.org/abs/2104.08663>
- 可核查要点（abstract 原文）：
  - 强调"统一、易用的评测框架"（"a common and easy framework"）跨多类 IR 任务横评模型——即**评测要用同一题集/同一框架**；
  - 明确把效率写进结论："models on average achieve the best zero-shot performances, however, **at high computational costs**"；"**dense and sparse-retrieval models are computationally more efficient**"——即**效果与成本必须并列报告**，不能只报效果。
- 对本文档的用法（仅叙事，不引用数字）：PPT「结果总览」页可在表头外强调"同题集 + 统一门禁 + 同时报告效果/耗时/成本"，与 BEIR 的口径一致。

### 2.2 RAGAS —— 质量不是一个分数，而是检索侧/生成侧多轴

- 来源：《Metrics | Ragas》（官方文档），<https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/>
- 可核查要点：RAGAS 把 RAG 评测指标分组，其中 **RAG 组**包含 Context Precision / Context Recall / Context Entities Recall / Noise Sensitivity（检索侧）与 Response Relevancy / Faithfulness（生成侧）；另有面向 Agent/工具的 Tool Call Accuracy、Agent Goal Accuracy，以及 Factual Correctness / Semantic Similarity 等语言比较类。
- 对本文档的用法：支持 PPT 把「检索层」与「回答层」分开报——本项目正是在这一点上做了分层：通道3 只测检索（无 LLM），通道1/2 才测端到端回答。

### 2.3 SQuAD 2.0 —— "拒答"本身是被计分的一等行为

- 来源：Rajpurkar, Jia, Liang《Know What You Don't Know: Unanswerable Questions for SQuAD》，arXiv:1806.03822，<https://arxiv.org/abs/1806.03822>
- 可核查要点（abstract 原文）：
  - "SQuAD 2.0 combines existing SQuAD data with **over 50,000 unanswerable questions** written adversarially by crowdworkers to look similar to answerable ones."
  - "To do well on SQuAD 2.0, systems must not only answer questions when possible, but also determine when no answer is supported by the paragraph and **abstain** from answering."
- 对本文档的用法：为 PPT 的"域外题必须如实拒答"提供外部依据——**拒答是正确行为而非失败**；并支撑本项目"拒答优先"门禁口径（found 题若构成拒答即 FAIL）的合理性。

> 补充口径提示（背景）：公开评测通常分面报告——**有效性**（如检索命中/排序指标）、**回答质量**（人工或 LLM 判分）、**成本/效率**（token/耗时/算力）、**拒答纪律**（不可答题）。四类维度不宜压缩成单一"总分"，与本项目"三通道分测"的设计取向一致。

---

## 维度3：数据型学术 deck 的视觉与叙事参考（背景锚点，2 条）

### 3.1 图表设计四原则：单一信息、支撑媒介适配、图注非可选、去装饰

- 来源：Rougier NP, Droettboom M, Bourne PE《Ten Simple Rules for Better Figures》，PLOS Computational Biology，<https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833>
- 可核查要点（原文表述）：
  - **Rule 2: Identify Your Message** —— 一张图只表达一个清晰观点；能在"第一眼传达引人注目的信息"的图更容易被注意到；
  - **Rule 3: Adapt the Figure to the Support Medium** —— 用于**口头报告**时"the message must be visually salient in order to grab attention"（信息必须在视觉上醒目），期刊图可承载更多细节；
  - **Rule 4: Captions Are Not Optional** —— 图注要"explains how to read the figure"；有想强调的点就"make sure it is visually distinct"，并在图注里再次点出；
  - **Rule 6: Use Color Effectively** —— "you can use color for this element while keeping other elements gray or black"（用颜色只高亮关键元素，其余降为灰黑）；
  - **Rule 8: Avoid "Chartjunk"** —— 去掉不服务信息的装饰元素。
- 对本文档的用法：直接指导本项目 3 页 deck——每页一个 take-away、图注写"怎么读"、颜色只给关键数字（如 353.5s / 2,460 字符 / 25.0s）、去掉装饰性渐变/阴影。

### 3.2 口头报告三原则：信息要少、记住三点、视觉是支撑

- 来源：Bourne PE《Ten Simple Rules for Making Good Oral Presentations》，PLOS Computational Biology，<https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.0030077>
- 可核查要点（原文表述）：
  - **Rule 2: Less is More** —— "A common mistake of inexperienced presenters is to try to say too much"，结果是"the main message is often lost"；
  - **Rule 4: Make the Take-Home Message Persistent** —— "if you ask a member of the audience a week later about your presentation, they should be able to remember **three points**"；"If they can remember any three points, but not the key points, then your emphasis was wrong"；
  - **Rule 8: Use Visuals Sparingly but Effectively** —— "if you have more than one visual for each minute you are talking, you have too many"；"do not overload the visual. **Make the points few and clear**"；"The visual should support what you are saying"。
- 对本文档的用法：3 页 deck 的 take-away 建议压到 3 点（如：① 三通道同题可比 ② B×cm1 是唯一缺陷且根因在描述层 ③ 脚本化图书管理员 + 判卷门修正让结论可信），每页图表只服务一页一个论点。

---

## 来源清单（可核查）

| # | 标题 | URL | 维度 |
|---|---|---|---|
| 1 | BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | https://arxiv.org/abs/2104.08663 | 维度2 |
| 2 | Metrics \| Ragas（官方文档总览） | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/ | 维度2 |
| 3 | Know What You Don't Know: Unanswerable Questions for SQuAD | https://arxiv.org/abs/1806.03822 | 维度2 |
| 4 | Ten Simple Rules for Better Figures | https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833 | 维度3 |
| 5 | Ten Simple Rules for Making Good Oral Presentations | https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.0030077 | 维度3 |

> 检索留痕：bing 检索命中 BEIR（arxiv/github）、SQuAD 2.0（arxiv）；RAGAS 官方文档与 PLOS 两篇为页面直取（WebFetch）。github.com 与部分 arxiv/abs 页面在本环境超时，已改用可达 URL 替代，未臆造内容。
