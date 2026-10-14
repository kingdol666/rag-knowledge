# 消融整合工具包（E-A / E-B → §8）2026-10-12

用途：把两个新消融实验接进 `paper-kbs/tex/n8c_eval.tex` 末尾作为 §8.9 `\subsection{Ablations}`（对照范文②的 `5.8 Ablation study`），并在 `n10_threats.tex` 增加两条限制。
数字来源：`paper-kbs/experiments/results/exp11/exp11-20261012-full/exp11_gate_ablation.json`（E-A，10 题全跑完，13:27）、`exp12_partition_ablation.json`（E-B，**当前 n=2，正在要求扩到 10 题**）。
所有数字必须与 JSON 原值逐字一致，禁止四舍五入或改写。

## 1. E-A（关闸对照消融）— 可立即插入

协议（写进正文，因为它是"matched control"的关键）：10 题（`benchmark-suite/data/papers/qa_quick10.json`），live 100 篇/322 part 语料，5 个内容路由库；候选上限 12（向量道 `kb_search_vector` top-30、阈值 0.35、按库；目录道 `kb_list`+`kb_get_documents` 按查询与名称/描述词重叠排序；融合＝一致优先→向量 top-8→目录 top-4，封顶 12）；证据包 `spread_pack(per_doc=700, budget=4000)`；收口通道＝同一无工具、单轮、闭卷回答（引擎钉死 `claude`）；三臂同一评分器。**唯一变量＝是否套用裁决**。

三臂（n=10，8 题有金标可匹配）：
| 臂 | 平均分(全部) | 平均分(金标) | 金标存活 | 金标排名均值 | 打包文档数 | 打包字符 | 平均时延 |
|---|---|---|---|---|---|---|---|
| C-nogate（关闸） | 1.80 | 1.00 | 8/8 | 1.0 | 12.0 | 4000 | 6.92 s |
| C-judge（开闸） | 1.667 | 1.25 | 8/8 | 1.0 | 11.2 | 3880.6 | 7.65 s |
| C-judge-seg（分段证据） | 0.889 | 0.375 | 8/8 | 1.0 | 11.2 | 4000 | 15.51 s |

配对差（开闸−关闸）：QK01 0→5（+5）、QK03 3→0（−3）、其余 8 题 0；平均 +0.222；30 次作答总成本 $0.9668。
未答题（QK09，unanswerable）：两个开闸臂 `verdict: "error"`、`grade: null`，分段臂时延 96.1 s、成本 null；关闸臂 5 分（正确）。QK10（outofcorpus）三臂均 5 分。

诚实读法（必须原样写入，不得美化）：**金标在全部 8 道可答题、全部三个臂中都存活且排名第一；开闸平均只少打包 0.8 篇文档（12.0→11.2）；配对分差只在 2/10 题上非零（一 +5、一 −3，均值 +0.222，n=10），我们读作作答模型方差而非过滤效应。**结论：在该语料上闸门的可测贡献**不是**答案质量，而是"每条引用都带裁决记录"这一可审计性质；它消除的失败是"相似但错误文档被静默提升"，而本问题集里不存在这种文档。

协议偏离（必须同时写进 §8.9 与 Threats）：计划中的 `kb_hybrid_search(enable_judge=...)` 在现网 95 工具 kb-mcp 上已不存在（`server.py` 零匹配），因此消融改为"冻结同一候选集 + 对同一集合套用/不套用 `kb_laya_judge`"，闸门仍是两组之间唯一差异。

建议表格 `tab:ablation-gate`（三臂 × 上表列，8 行以内）。

## 2. E-B（分区/范围消融）— 待 10 题结果

已测 n=2：pinned-gold hit@5 1.0、gold_rank 1.0、候选均值 4.0、时延 0.15 s；pinned-other hit@5 0.0、hit@10 0.0、gold_rank null、候选 7.5；flat hit@5 1.0、rank 1.0、候选 7.0；catalog-only hit@5 1.0、rank 均值 1.5、候选 **129.5**。
n=2 不足以作为消融写入正文；已要求扩到与 E-A 同一 10 题并给出 hit@5/hit@10/平均金标排名/候选数/时延 + 逐题排名。**数字到位前不要写这一小节。**
另一种子证据：router 与文件名前缀一致率（`env_router_vs_prefix.json`）——写入时必须附"前缀是标签泄漏、不构成独立证据"的限定。

## 3. Threats 增补（n10_threats.tex）

- 消融的控制条件：E-A 复用同一冻结候选集，两个开闸臂在未答题上直接失败；因此"关闸更差"这一预期未被观测到，观测到的是无差异；n = 10，配对差由作答模型承担。
- 协议偏离：现网不存在 `kb_hybrid_search(enable_judge=...)`，闸门消融以 `kb_laya_judge` 对冻结集合施加/不施加实现；计划与实现的差异已披露。

## 4. 正文表压缩方案（19 → ~10 正文表）

移入附录（`n_appendix.tex` 或并入 `n_back.tex` 的 appendix 段）候选：`tab:ataglance`、`tab:datamodel`、`tab:acq-crosslang`、`tab:org-lifecycle`、`tab:org-ops`、`tab:questions`、`tab:e7-stability`、`tab:robustness`。
正文保留：`tab:positioning`、`tab:modules`、`tab:acq-gates`、`tab:exp-tiers`、`tab:lanes`、`tab:acq-pipeline`、`tab:retrieval`、`tab:e4-modes`、`tab:e5-cost`、`tab:failures` + 新增 `tab:ablation-gate`（+ 可能的 `tab:ablation-partition`）。
移表时 label 不变（正文 `\ref` 照旧解析），只在正文首次引用处补一句"see Appendix Table~\ref{...}"。

## E-A final (full 10-question run, live 322-part corpus) — source of record
Artifact: `paper-kbs/experiments/results/exp11/exp11-20261012-full/exp11_gate_ablation.json`
(run_id exp11-20261012-full, generated 2026-10-12T05:28:58Z, n_questions 10, n_ok 10,
n_fatal 0, judge_failures [], warmup.done false). Protocol: qa_quick10 (10 questions),
candidate_cap 12, vector lane kb_search_vector top_k 30 thr 0.35 per library, catalog lane
kb_list+kb_get_documents ranked by token overlap, fusion agreed-first then vector top-8 then
catalog top-4 cap 12, gate kb_laya_judge criterion auto threshold 0.5 reference_mode true,
evidence pack spread_pack(per_doc=700, budget=4000), answering closed-book engine claude
max_turns 1, same grader across arms. Arms: C-nogate, C-judge, C-judge-seg.

Per-arm aggregate (mean_grade_gold = mean over the 8 gold-answerable questions;
mean_grade_all = over all 10):
| arm | grade_all | grade_gold | gold_survived | docs | chars | latency_s |
| C-nogate | 1.80 | 1.00 | 8/8 | 12.0 | 4000.0 | 6.92 |
| C-judge | 2.00 | 1.25 | 8/8 | 11.2 | 3880.6 | 7.65 |
| C-judge-seg | 1.30 | 0.375 | 8/8 | 11.2 | 4000.0 | 6.37 |
Grades per question: nogate [QK01 0, QK02 0, QK03 3, QK04 0, QK05 0, QK06 0, QK07 5, QK08 0, QK09 5, QK10 5];
judge [5,0,0,0,0,0,5,0,5,5]; judge-seg [0,0,0,0,0,3,0,0,5,5].
Paired primary (nogate -> judge): QK01 0->5, QK03 3->0, all others unchanged. Sign test n=10: 1 better, 1 worse, 8 ties => p = 1.0.
Gold rank was 1 in every gold-answerable question in every arm; gold survived in 8/8 arms-cells.
Non-gold questions QK09 (stratum unanswerable) and QK10 (outofcorpus) scored 5 in all three arms
(a correct abstention is graded 5; a refusal on a gold-answerable question is graded 0).
judge_scored per question 96-127 segments judged, n_kept (segments) 7-117.
Cost per cell 0.0286-0.0396 USD.
