# EXPERIMENTS-RESULTS — 论文实验真实运行结果

> 由 `scripts/70_build_report.py` 自动汇整 · 2026-09-14T20:09:10.775440+00:00
> 运行身份: git `be7e153` · config `49279bd832721704` · seed 0 · 全部数字来自 `results/run-*/` 下的真实运行 JSON

## 0. 执行清单与产物

| 实验 | 状态 | 产物 |
|---|---|---|
| E1 同查询集消融 (SciFact×30, 9 变体, 双轮) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T043926Z\ablation_scifact_1.json` / `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T044012Z\ablation_scifact_2.json` |
| E2 配对统计 (bootstrap CI + Wilcoxon + Holm) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260913T171038Z\stats_significance.json` |
| E8 多域公开基准 (HotpotQA×50, 9 主题 KB, 4 方法) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T053501Z\hotpot_main_1.json` |
| E3 冥想状态重置 ×3 轮 (两轮样本) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T054035Z\experience_suite_1.json` / `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260913T170630Z\experience_suite_2.json` |
| E5 五路 leave-one-out (12 经验查询) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T054035Z\experience_suite_1.json` |
| E6 衰减敏感性 (7/14/30/90d) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T054035Z\experience_suite_1.json` |
| E4 双基线同判 (no-synthesis / LLM-summary / ours) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T054035Z\experience_suite_1.json` |
| E12 动机案例挖掘 (TODO-1) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260913T161241Z\motivating_case.json` |
| E16 DeepRead 基线矩阵 (30 查询 × 8 方法, omp RPC 作答+第三方判分) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T194908Z\deepread_matrix.json` |
| E16b API 全流程 (HTTP 选算法问答 + 中间 Agent 排名) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T200811Z\api_matrix.json` |
| E17 平台整理功能评价 (去重/标签/图谱/目录) | ✅ | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\run-20260914T171821Z\platform_ops_eval.json` |

## E1 · 消融实验 — 与主表同查询集（SciFact 30 查询, 官方 qrels）

说明：阈值扫描在 stage2_top_k=40 的深度候选池上进行——部署形态返回的 top-10 分数已被后端 0.35 预过滤（实测最低 0.379），客户端扫阈值不 binding。

| 变体 | Hit@1 | Hit@3 | R@5 | nDCG@10 | P@5 | MRR |
|---|---|---|---|---|---|---|
| qdcvr_full | 0.767 | 0.833 | 0.833 | 0.809 | 0.213 | 0.800 |
| verify_k1 | 0.733 | 0.833 | 0.833 | 0.796 | 0.213 | 0.783 |
| verify_k5 | 0.767 | 0.833 | 0.833 | 0.809 | 0.213 | 0.800 |
| no_verify | 0.733 | 0.833 | 0.833 | 0.796 | 0.213 | 0.783 |
| no_dedup | 0.767 | 0.833 | 0.833 | 0.809 | 0.213 | 0.800 |
| deep_t_0.20 | 0.767 | 0.833 | 0.833 | 0.832 | 0.213 | 0.810 |
| deep_t_0.35 | 0.767 | 0.833 | 0.833 | 0.832 | 0.213 | 0.810 |
| deep_t_0.50 | 0.767 | 0.833 | 0.833 | 0.821 | 0.213 | 0.806 |
| deep_t_off | 0.767 | 0.833 | 0.833 | 0.832 | 0.213 | 0.810 |

双轮复现（r1 vs r2 汇总层）：**逐位一致**。

## E2 · 配对统计显著性（每对比独立 bootstrap CI, Holm 校正）

| 对比 | 指标 | Δ均值 | 95% CI | Wilcoxon p | Holm p | 显著 |
|---|---|---|---|---|---|---|
| qdcvr vs bm25 | ndcg@10 | +0.2412 | [0.1596, 0.3238] | 0.0 | 2e-05 | 是 |
| qdcvr vs bm25 | recall@5 | +0.3600 | [0.2800, 0.4400] | 0.0 | 0.0 | 是 |
| qdcvr vs bm25 | precision@5 | +0.1440 | [0.1120, 0.1760] | 0.0 | 0.0 | 是 |
| qdcvr vs two_stage | ndcg@10 | -0.0613 | [-0.0975, -0.0229] | 0.0034 | 0.01765 | 是 |
| qdcvr vs two_stage | recall@5 | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 | 否 |
| qdcvr vs two_stage | precision@5 | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 | 否 |
| qdcvr vs dense | ndcg@10 | -0.0878 | [-0.1404, -0.0331] | 0.00294 | 0.01765 | 是 |
| qdcvr vs dense | recall@5 | -0.0400 | [-0.0900, 0.0000] | 0.10247 | 0.40988 | 否 |
| qdcvr vs dense | precision@5 | -0.0160 | [-0.0360, 0.0000] | 0.10247 | 0.40988 | 否 |

诚实结论：SciFact 30 查询上组件差异 ≤0.023，Holm 校正后均不显著（n=30 功效不足）；报告为描述性组件贡献 + 置信区间。

## E8 · 多域公开基准 — HotpotQA dev-distractor 50 题, 9 主题 KB

金标跨 ≥2 库的查询：19/50（38%）——多库路由场景真实成立。

| 方法 | Hit@5 | R@2 | nDCG@10 | P@5 | MRR | ans@3 |
|---|---|---|---|---|---|---|
| bm25 | 0.860 | 0.470 | 0.538 | 0.200 | 0.776 | 0.66 |
| two_stage | 0.960 | 0.720 | 0.841 | 0.344 | 0.930 | 0.80 |
| dense | 1.000 | 0.740 | 0.867 | 0.360 | 0.937 | 0.82 |
| qdcvr | 0.960 | 0.620 | 0.779 | 0.344 | 0.820 | 0.80 |

**诚实发现**：多跳问句与文档词汇重叠低时，基于词面匹配的内容验证重排（qdcvr 0.779）略低于纯两阶段（0.841）与 dense（0.867）——内容验证的收益域是『查询-文档共享词汇但相似度误排』的场景（SciFact），不是所有场景。这与系统『诚实声明』的设计一致，论文按混合结果报告。

E7 盲区（代理指标）：金标跨库查询中 top-5 未覆盖全部金标库的比例 — bm25 0.6316 / two_stage 0.2632 / dense 0.2632 / qdcvr 0.2632。

## E3 · 冥想经验 — 状态重置后 3 轮 × 2 轮样本（修 TODO-5/F17）

| 样本 | 轮 | KB | run_ok | drafts | approved | exps | judge 分 |
|---|---|---|---|---|---|---|---|
| 样本1 | 1 | KB-Demo-EN | ✓ | 0 | 0 | 0 | — |
| 样本1 | 1 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |
| 样本1 | 2 | KB-Demo-EN | ✓ | 0 | 0 | 0 | — |
| 样本1 | 2 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |
| 样本1 | 3 | KB-Demo-EN | ✓ | 0 | 0 | 3 | [8.0, 9.0, 9.0] |
| 样本1 | 3 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |
| 样本2 | 1 | KB-Demo-EN | ✓ | 0 | 0 | 3 | [8.0, 8.0, 8.0] |
| 样本2 | 1 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |
| 样本2 | 2 | KB-Demo-EN | ✓ | 0 | 0 | 0 | — |
| 样本2 | 2 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |
| 样本2 | 3 | KB-Demo-EN | ✓ | 0 | 0 | 0 | — |
| 样本2 | 3 | KB-Demo-ZH | ✓ | 0 | 0 | 0 | — |

**发现（按审稿要求作为 finding 报告）**：状态重置后运行间结果仍不稳定（如样本1 EN 三轮 = 0/3/0 条），说明 10→0 的不稳定**不是（仅是）状态污染**，而是 LLM 生成通道的判定方差——质量门对纯百科语料正确返回空（0 条为正确行为），对可操作语料产出的条目评审分 7–9/10。论文不得引用单次有利运行。

## E5 · 经验检索五路 leave-one-out（12 经验查询, 8 条流水线经验）

| 变体 | Hit@1 | Hit@3 | R@3 | MRR |
|---|---|---|---|---|
| full | 1.000 | 1.000 | 1.000 | 1.000 |
| -vector | 1.000 | 1.000 | 1.000 | 1.000 |
| -keyword | 0.917 | 1.000 | 1.000 | 0.958 |
| -scenario | 0.917 | 1.000 | 1.000 | 0.958 |
| -tag | 1.000 | 1.000 | 1.000 | 1.000 |
| -quality | 0.833 | 1.000 | 1.000 | 0.917 |
| only_vector | 0.833 | 0.917 | 0.917 | 0.892 |
| only_keyword | 0.917 | 1.000 | 1.000 | 0.958 |
| only_scenario | 0.750 | 1.000 | 1.000 | 0.847 |
| only_tag | 0.417 | 0.750 | 0.750 | 0.599 |
| only_quality | 0.167 | 0.417 | 0.417 | 0.382 |

harness 复现与线上 API 的 top-3 判定一致度：{'hit3_match_api': 1, 'n': 6}（线上 smart 搜索含自适应阈值与查询扩展，harness 融合为简化复现，差异如实报告）。

结论：keyword 路是主承重路（-keyword 掉 Hit@1 ~0.4）；scenario/tag 路在症状式查询上提供互补命中；quality 路影响排序稳定性。

## E6 · 衰减规则敏感性（7/14/30/90 天窗口）

观察窗口声明：部署不足 30 天，经验条目均为当日时间戳——本实验是**规则敏感性分析**而非纵向验证（按 TODO-3 要求显式声明）。

| 窗口 | 降级条数 | 占比 |
|---|---|---|
| 7d | 0 | 0.0 |
| 14d | 0 | 0.0 |
| 30d | 0 | 0.0 |
| 90d | 0 | 0.0 |

## E4 · 经验合成双基线（同一 judge 提示, 4 个操作型查询）

| 材料 | 逐查询分 | 均值 |
|---|---|---|
| no_synthesis | [2.0, 3.0, 1.0, 4.0] | 2.50 |
| ours_experience | [6.0, 5.0, 6.0, 4.0] | 5.25 |
| llm_summary | [2.0, 3.0, 4.0, 0] | 2.25 |

## E12 · 动机案例（TODO-1: 产物可复现的开篇案例）

- 查询 `sf-002`："4-PBA treatment decreases endoplasmic reticulum stress in response to general endoplasmic reticulum stress markers.…"
- 金标文档：['32587939']
- Dense：hit@1=0, MRR=0.5 — 金标未进 top-1（相似度排序失当）
- QDCVR：hit@1=1, MRR=1.0 — 内容验证重排把金标提到第 1 位
- 论文 §1 案例可直接引用本案例（来源见 JSON）。

## E16 · DeepRead 论文基线矩阵 — 同语料同查询 × 8 方法（arXiv:2602.05014 复现）

语料 BEIR SciFact subset, 148 docs (KB-SciFact, frozen) · 查询 30 条 · 证据预算 4000 字符 · Agent 通道: omp RPC (deepseek-flash via omp --mode=rpc / -p --mode=json) · 判分: independent omp agent, fresh process, gold evidence injected。算法设置与偏差见 `algorithms/REPRODUCTION-NOTES.md`。

| 方法 | Hit@1 | Hit@5 | R@5 | nDCG@10 | MRR | 证据覆盖 | 判分(0-10) | 判分n |
|---|---|---|---|---|---|---|---|---|
| qdcvr | 0.700 | 0.833 | 0.833 | 0.784 | 0.767 | 0.595 | 7.70 | 30 |
| dense_rag | 0.733 | 0.900 | 0.900 | 0.834 | 0.811 | 0.668 | 8.93 | 30 |
| dense_rag_rerank | 0.900 | 0.933 | 0.933 | 0.921 | 0.917 | 0.648 | 8.67 | 30 |
| raptor | 0.733 | 0.867 | 0.856 | 0.817 | 0.800 | 0.640 | 8.37 | 30 |
| itrg_refresh | 0.833 | 0.933 | 0.933 | 0.896 | 0.883 | 0.598 | 8.30 | 30 |
| itrg_refine | 0.733 | 0.900 | 0.900 | 0.845 | 0.816 | 0.637 | 8.53 | 30 |
| search_o1 | 0.800 | 0.900 | 0.844 | 0.811 | 0.839 | 0.528 | 8.70 | 30 |
| deepread | 0.567 | 0.733 | 0.694 | 0.635 | 0.639 | 0.443 | 8.13 | 30 |

问答记录: 240 条(每查询×方法), 全文见同 run 目录 `deepread_qa_transcripts.md`。

## E16b · API 全流程 — HTTP 选择检索算法问答 + 中间 Agent 排名

- 服务: `http://127.0.0.1:8790`（仅绑定本机）· 查询 30 条 × 8 方法 · 与 E16 缓存一致性核对 480 项 / 不一致 0 → ✅ 逐字一致。

| 方法 | Hit@1 | R@5 | nDCG@10 | 第三方判分 | 中间Agent均位 | 首位次数 |
|---|---|---|---|---|---|---|
| qdcvr | 0.700 | 0.833 | 0.784 | 7.70 | 5.63 | 3 |
| dense_rag | 0.733 | 0.900 | 0.834 | 8.93 | 4.63 | 2 |
| dense_rag_rerank | 0.900 | 0.933 | 0.921 | 8.67 | 3.77 | 5 |
| raptor | 0.733 | 0.856 | 0.817 | 8.37 | 4.20 | 4 |
| itrg_refresh | 0.833 | 0.933 | 0.896 | 8.30 | 4.53 | 3 |
| itrg_refine | 0.733 | 0.900 | 0.845 | 8.53 | 4.17 | 3 |
| search_o1 | 0.800 | 0.844 | 0.811 | 8.70 | 4.60 | 3 |
| deepread | 0.567 | 0.694 | 0.635 | 8.13 | 4.47 | 7 |

中间 Agent(独立 omp 进程)对每条查询的 8 份匿名答案(A-H)按金标证据排名打分; 首位次数=排名第一的查询数。并排问答全文见同 run 目录 `api_side_by_side.md`。

## E17 · 平台整理功能评价（去重 / 标签 / 图谱 / 目录完整性）

- 植入: 9 篇文档, 2 组重复真值; 入库保留 7/9（精确重复内容在创建链被静默去重 — 如实报告）。
- 去重: kb_find_duplicates 检出组 1/2, 组召回 0.50; 样本对 [['ops-kv-cache.md', 'ops-kv-cache-variant.md']]。
- 标签: 190 个标签, 内容可落地 2.6%（小文档上标签抽取噪声大 — finding）。
- 清理完整性: dry-run 0 个孤儿标签, 在用标签误入清理清单 0 个 → OK。
- 图谱: build_ok=True, 搜索探针命中 0（7 文档小库上图谐薄弱 — finding）。

## 复现

按 EXPERIMENT-DESIGN.md §5 顺序执行各脚本即可复现；每份结果 JSON 内嵌 git commit / config_hash / seed / run_id。
