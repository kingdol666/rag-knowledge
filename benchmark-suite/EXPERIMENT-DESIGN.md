# EXPERIMENT-DESIGN — 论文实验完整设计（对齐审稿要求）

> 目标读者：论文作者 + 执行实验的 Agent（Zcode）。
> 本文档把 `REVIEW-TODO.md`（14 项）与 `REVIEWER-AUDIT.md`（F1–F17）中**所有实验类要求**
> 映射为可执行、可复现的具体实验；执行入口与产出文件一一对应。
> 设计原则：**真实执行 > 引用**——每个数字都来自本仓库内可重跑的脚本，
> 结果写入带 run-id 的不可变目录，内嵌 git commit / 配置哈希 / 随机种子。

## 0. 实验总览（审稿要求 → 实验 → 脚本 → 产出）

| # | 审稿要求 | 实验 | 脚本 | 产出 |
|---|---|---|---|---|
| E1 | TODO-9/F12 消融与主表不同规模 | **同查询集消融**：在 BEIR SciFact 30 查询上重跑 8 个消融变体（阈值扫描 0.20/0.35/0.50、去硬阈值、去重排、去内容验证、验证读 k=1/5） | `scripts/30_ablation.py` | `results/run-*/ablation_*.json` |
| E2 | TODO-7/F13/F14 统计不合规 | **配对统计**：每对比 per-metric bootstrap 95% CI（B=2000，配对重采样）+ Wilcoxon 符号秩 + 配对 t；Holm–Bonferroni 多重校正；正态性 Shapiro–Wilk | `scripts/31_stats.py` | `stats_significance.json` |
| E3 | TODO-5/F17 状态不重置、单轮 | **Experience 状态重置 + ≥3 轮**：每轮前 API 清空 experience/draft 状态，3 次独立冥想运行，逐轮报告条数与评审分 | `scripts/40_experience_suite.py` | `experience_runs.json` |
| E4 | TODO-6 Experience 无基线 | **双基线对比**：(i) no-synthesis（原始文档检索）(ii) LLM 单次摘要（同文档一次性总结为 lessons），三者用**同一 judge 提示**评审 | 同上 | `experience_baselines.json` |
| E5 | TODO-4 五路融合未评测 | **五路 leave-one-out + 单路**：按后端同款融合公式在 harness 层实现（vector/keyword/scenario/tag/quality 五路可开关），经验查询集上 Recall@k/nDCG@k | `scripts/41_path_ablation.py` | `experience_paths.json` |
| E6 | TODO-3 衰减阈值未验证 | **衰减敏感性**：对经验库时间戳做 7/14/30/90 天窗口扫描，报告降级集合、降级精确率（对"从未被应用"代理金标）、显式声明观察窗口 | `scripts/42_decay_analysis.py` | `decay_sensitivity.json` |
| E7 | TODO-2 盲区规则未评测 | **盲区双向错误率**：金标跨 ≥2 库的查询（E8 提供）测欠抑制（漏声明）与金标单库查询测过抑制（误声明） | `scripts/50_blindspot.py` | `blindspot.json` |
| E8 | TODO-12/F-multidomain 全自建数据 | **多域公开基准**：HotpotQA dev-distractor 支撑文档按主题拆 8 个 KB（公开可复现的多库路由版），4 方法主表 + 跨库金标占比 | `scripts/60_hotpot_build.py` `61_hotpot_eval.py` | `hotpot_main.json` |
| E9 | TODO-13 规模过小/天花板 | **语料规模说明 + 去饱和**：SQuAD/XQuAD 明确标注 ceiling 并降级为功能验证；主实验 = SciFact(30) + HotpotQA(50) | 61 脚本内声明 | 报告文字 |
| E10 | TODO-10/F16 结果被覆盖、无 run 身份 | **不可变 run 目录 + 身份指纹**：所有新实验写 `results/run-<UTC时间戳>/`，每份结果内嵌 git commit、配置哈希、seed | `scripts/lib.py` 扩展 | 全部新结果文件 |
| E11 | TODO-8/F-baseline 超参未记录 | **部署指纹**：BGE-M3 revision、ChromaDB HNSW 参数、BM25 k1/b、jieba 版本写入结果 meta | `scripts/32_deployment_fingerprint.py` | `deployment.json` |
| E12 | TODO-1 动机案例不可复现 | **真实案例挖掘**：从冻结检索产物中选"向量 top-1 ≠ 金标且内容验证纠正"的查询，给出精确分数 | `scripts/33_mine_motivating.py` | `motivating_case.json` |
| E13 | 评审 W1/Q1 路由无测量 | **路由 oracle**：HotpotQA 九库上 always-search-all vs oracle-routing（限定金标库内检索），测路由可带来的上限增益 | `scripts/64_routing_oracle.py` | `routing_oracle.json` |
| E14 | 评审 Q2 词汇重叠边界 | **重叠分层分析**：按查询-金标文档词汇覆盖率分层（高/低），逐层比较 qdcvr vs two_stage——检验"按重叠触发裁决"能否消除负效应 | `scripts/65_stratified.py` | `stratified_adjudication.json` |
| E15 | 评审 W3 无 judge 一致性 | **双 judge 一致性**：同一材料两路独立 judge（不同 judge 实例/措辞扰动），报告逐条完全一致率、Cohen's κ、平均分差；**如实标注为 LLM–LLM 一致性，非人工 κ** | `scripts/66_judge_agreement.py` | `judge_agreement.json` |
| E4+ | 评审 W4 规模偏小 | 经验基线查询 4→8（同设计扩展），并复跑 hotpot 评测 r2 验证逐位复现 | `42_e4_fix.py` 扩展 | `e4_baselines_fixed.json` |

不在本轮范围（需人工/多会话，设计文档注明）：TODO-11（3 人 × 40–60 查询 κ 一致性）；
TODO-10 的匿名 artifacts 外链（Zenodo）；F1 赛道选择（论文编辑问题）。

## 1. 查询集与语料

| 查询集 | 规模 | 金标 | 用途 |
|---|---|---|---|
| BEIR SciFact | 30 查询 / 148 文档（1 KB） | 官方 qrels 多相关集 | E1 消融、E2 显著性（非饱和、IR 标准）|
| SQuAD v1.1 | 16 查询 / 8 文档 | 文章级 + 答案串 | 仅功能验证（ceiling 已声明，E9）|
| **HotpotQA dev-distractor 子集** | 50 查询 / ~160 支撑文档拆 8 主题 KB | 官方 2 跳支撑文档（天然跨 ≥1 KB，约 87% 跨 2 KB）| E8 主表、E7 盲区、E2 显著性 |
| **经验查询集** | 12 查询（症状式/学习式/决策式 ×4）| 指定经验条目（写入查询文件）| E5 五路消融、E4 基线 |

HotpotQA 拆库方法（写进论文 setup）：对每题官方 supporting docs（2 篇 Wikipedia 段落）
按标题关键词规则映射到 8 个主题 KB（geography / history / politics / music / film /
literature / science / sports-other），同题两篇常落入不同 KB → 金标天然跨库。
KB 分配规则确定性（无 LLM、无 RNG），manifest 记录每文档→KB 映射，可复现。

## 2. 方法（baselines 与 ours）

| 方法 | 实现 | 说明 |
|---|---|---|
| BM25 | `kb_search_two_stage` stage1 候选 | 稀疏检索（BEIR 基线同款；超参见 E11 指纹）|
| Dense | `kb_search_vector` top-10 | BAAI/bge-m3 + ChromaDB |
| Two-stage (Hybrid) | stage2 精排 + 阈值去重 | 无内容验证（消融意义上的"-ContentVerify"）|
| **QDCVR (ours)** | 两阶段 → 阈值 → kb_doc_read×3 内容验证重排 | 与 knowledgebase-search skill 同规程 |

外部锚点（引用，非本地运行）：BEIR 论文报告 SciFact BM25 nDCG@10 = 0.665、
DPR = 0.649（Thakur et al., CIKM 2021）——用于校验本地 BM25 实现的合理区间。

## 3. 统计协议（E2，对齐 TODO-7/F13/F14）

- 配对设计：同一查询集上每方法产出每查询指标 → 配对差分。
- 主指标：Recall@5、nDCG@10（连续，报 CI）；Hit@3 报 McNemar。
- **per-comparison** 95% CI：配对 bootstrap（B=2000， percentile 法），逐对比独立计算。
- 显著性：Wilcoxon 符号秩（主，n=30/50 小样本不假定正态）+ 配对 t（对照），
  报告 Shapiro–Wilk 正态性检验结果以说明选择依据。
- 多重校正：Holm–Bonferroni，跨全部对比族；同时报告校正前后 p 值。
- 多轮：确定性配置不做 5 次假重复——会话内双轮（r1/r2）逐位一致 + 跨重置轮
  （冷启动重跑）报告 tie-break 方差，明示"确定性管线，方差来源为会话级 UUID"。
  LLM 通道（E3 冥想）按 ≥3 独立轮报告均值 ± SD。

## 4. Experience 实验细节（E3/E4/E5/E6/E7）

### 4.1 查询集构造（E5/E4）
症状式查询刻意**不共享**目标经验的标题词汇、只共享 scenario/tags（论文 §5.4 的
动机案例），词汇式查询共享 solution 词汇（向量友好）。全部查询与金标写入
`data/experience_queries.jsonl`，随仓库冻结。

### 4.2 五路融合消融（E5）
后端融合（`experience_service.search_experiences_global`）：向量召回 + 关键词互补
召回（scenario/tag 折叠进全文本匹配分），质量反馈经可信度分层影响最终排序。
Harness 层按**同款公式**实现五路开关（每路=独立打分器，融合=分融合+去重+阈值），
变体：full / −vector / −keyword / −scenario / −tag / −quality / 每路单独（5 个）。
与线上 API 的 full 模式对齐校验（同查询 top-5 重合度报告），保证 harness 复现有效。

### 4.3 状态重置（E3，修 P2/F17）
每轮冥想前：`DELETE /experience/{kb}/experiences/{id}`（逐条）+ 清 drafts，
API 校验计数归零后再触发。3 轮独立运行 + 逐轮条数/评审分；若仍不稳定，
按审稿要求"报告两轮并作为发现分析"。

### 4.4 基线（E4，对齐 TODO-6）
- **no-synthesis**：对同一经验查询集，用 `kb_search_two_stage` 检索原始文档，
  取 top-3 文档原文作为"答案材料"。
- **LLM-summary**：对 KB-Demo-EN 全部 7 篇文档做一次性 LLM 摘要成"lessons"
  （单 prompt，无场景/标签/生命周期元数据），作为第二条基线材料。
- 三种材料（ours 经验 / LLM 摘要 / 原始文档）用**完全相同的 judge 提示**
  （Zcode 子 Agent，0–10 rubric：有据性 4 / 结构 3 / 可复用性 3，与模块 C 同款）
  逐查询评审，报告均值 ± SD。

### 4.5 衰减（E6，对齐 TODO-3）
以经验库 `updated_at`/`applied` 记录为数据源：窗口 7/14/30/90 天 → 每窗口
降级集合大小、其中"从未被应用"占比（代理精确率）；**显式声明**：系统上线
<30 天，无法观察完整 30 天周期，本实验为规则敏感性分析而非纵向验证。

### 4.6 盲区（E7，对齐 TODO-2）
金标跨 ≥2 KB 的 HotpotQA 查询：系统声明"limited coverage"（<2 库命中即声明）
→ 欠抑制率 = 未声明但金标确实跨库的比例；金标单库查询（SciFact 全部）→
过抑制率 = 单库有结果却被声明覆盖受限的比例。

## 5. 执行顺序（Agent 作业单）

```
0. 冒烟：每模块单独调用一次（kb_list / two_stage / vector / doc_read /
   experience CRUD / meditation / parse_doc）→ 全绿才继续
1. E11 部署指纹 → E10 身份基建（lib.py 扩展）
2. E1 消融（SciFact，8 变体 ×30 查询，双轮）→ E2 统计
3. E8 HotpotQA：下载 → 拆库 → 入库 → 4 方法评测 → E7 盲区
4. E3 Experience 重置 + 3 轮 → E4 基线 → E5 五路消融 → E6 衰减
5. E12 动机案例挖掘
6. 汇整：EXPERIMENTS.md + experiments-report.html（冻结到 run 目录）
```

## 6. 复现保证

- 每份结果 JSON 内嵌：`git_commit`、`config_hash`（backend config.yml + 检索参数）、
  `seed=0`（无 RNG；LLM 通道记录模型名与 provider）、`run_id`（UTC 时间戳）。
- 结果一律写 `results/run-<run_id>/`，不覆盖既有文件；报告引用快照文件名。
- 一键重跑：本文档 §5 顺序即命令序列；每步失败即停（`&&` 串联）。
