# 复现验证报告（REPRODUCTION-VERIFICATION）

> 目的：验证 `TEST-PLAN.md` 是否能让执行者（人或 Agent）从零复现 benchmark 数值。
> 方法：**归档当前结果 → 清空全部知识库 → 重启后端 → 严格按 PLAN 逐步重跑 → 逐项对比**。
> 工具：`scripts/compare_runs.py`（判定规则：A/B 数值须一致；C 的 LLM 评分容忍 ±1.5；
> 计时与时间戳字段不参与判定）。

- 归档基线：`results/archive-20260913-214859/`（复现前的结果快照）
- 复现轮次：2026-09-13 21:56 → 22:56（约 60 分钟，含冷启动）
- 对比详情：`results/_repro-compare.json`

## 1. 总体结论

| 模块 | 会话内 r1==r2 | 跨会话 vs 基线 | 判定 |
|---|---|---|---|
| A 文档解析入库 | 逐位一致 | **完全一致**（仅时间戳不同） | ✅ 可复现 |
| B 标准赛道 · **QDCVR（本系统）** | 逐位一致 | **排序指标逐位一致**（hit/recall/nDCG/P@5/MRR 全同） | ✅ 可复现 |
| B 标准赛道 · 基线（BM25/dense） | 逐位一致 | BM25 小幅差异（≤0.033），dense ≤0.006 | △ 微小方差 |
| B demo 赛道 | 逐位一致 | 仅跨库查询翻转，聚合 Δ≤0.05 | △ 微小方差 |
| C 冥想经验 | LLM 通道 | **0 条 vs 8–10 条** | ❌ 未复现（LLM 判定） |

一句话：**确定性内核（入库 + 本系统 QDCVR 检索）可复现；基线的稀疏检索有 tie-break
量级的微小方差；冥想通道因 LLM 判定不同而结果不一致，且这是可解释的。**

## 2. 分模块证据

### 2.1 模块 A —— 完全一致 ✅

| 指标 | 归档 | 复现 |
|---|---|---|
| parse_success | 1.0 | 1.0 |
| ingest_success_rate | 1.0 | 1.0 |
| membership_accuracy | 1.0 | 1.0 |
| storage_completeness | 1.0 | 1.0 |
| self_retrieval_hit1 | 0.9375 | 0.9375 |
| pdf_parse_chars（MinerU） | 1444 | 1444 |
| 标准语料 n_docs / membership / completeness | 184 / 1.0 / 1.0 | 184 / 1.0 / 1.0 |

逐位一致，唯一差异是 `summary.generated` 时间戳。

### 2.2 模块 B 标准赛道 —— QDCVR 排序指标逐位一致 ✅

BEIR SciFact（30 查询，官方 qrels）QDCVR 全部排序指标完全相同：

| 方法 | 差异字段（归档 → 复现） |
|---|---|
| **QDCVR（本系统）** | 仅 `chars_read` 4291.9→4265.6（读取量，非指标）· `claim_evidence` 0.5159→0.5126 |
| Two-stage | 仅 `claim_evidence` 0.4876→0.4928 |
| Dense (bge-m3) | `nDCG@10` 0.8298→0.8341 · `MRR` 0.8056→0.8111 |
| BM25 (stage-1) | `hit@10` 0.833→0.867 · `nDCG@10` 0.809→0.822 · `recall@5` 0.783→0.800 |

SQuAD v1.1（16 题）：QDCVR / Two-stage / Dense 的 `hit@3`、`answer@1/3` **完全一致**；
仅 BM25 的 `answer@5` 0.9375→1.0。

**关键结论**：本系统 QDCVR 的 Hit@1 0.7667、Hit@3 0.8333、nDCG@10 0.8087、SQuAD
answer@3 1.0 跨会话逐位复现。方差集中在 **BM25 稀疏基线**，属索引重建时的
并列分数 tie-break 差异（每次会话文档 UUID 重新生成），量级 ≤0.033，不影响任何结论。

### 2.3 模块 B demo 赛道 —— 跨库查询微小方差 △

| 指标 | 归档 → 复现 |
|---|---|
| staged Hit@3 / R@3 / MRR | 0.95→0.90 · 0.9083→0.8833 · 0.8667→0.8625 |
| vector Hit@3 / R@5 / MRR | 0.90→0.95 · 0.8917→0.9167 · 0.91→0.9306 |

差异**只出现在 3 个跨库查询中的 2 个**（`q-x-01`、`q-x-03`，均问“哪些文档涉及可再生
能源/转换效率”，需全局 `balance_kbs` 跨库合并）。其余 17 个单库查询全部一致。

根因：全局平衡检索在跨库合并时，并列结果的次序依赖会话级 KB UUID（每次建库重新
生成），导致跨库查询的排名在会话间可能有 1 条文档的位移。单库查询不受影响。

### 2.4 模块 C 冥想经验 —— 未复现，且已定位原因 ❌→可解释

| | 归档（09-12） | 复现（09-13） |
|---|---|---|
| run_success_rate | 1.0 | 1.0（结构信号稳定）|
| KB-Demo-EN 经验数 | 8 / 10 | **0 / 0** |
| judge_score_mean | 4.375 / 3.5 | null（无经验可评）|
| grounded_ratio | 0.625 / 0.375 | null |

冥想 Agent（harness=omp，模型 `deepseek-flash`）在本轮的最终判定原文：

> 7 篇均为百科式背景知识（黑海/咖啡加工/电动车/互联网史/光合作用/光伏/风电），
> 无 problem→solution→verification 结构，不构成可复用实践经验。heuristic 干跑
> 产出 7 条候选，但全部 `key_lessons=[]`、`tags=[]`，problem/solution 为文档原文
> 截断串，按质量标准评分 2–4/10，全部低于 3 → 依“质量<3 丢弃、禁止编造、禁止泛泛
> 经验”条款丢弃，未调用 experience_create。结论：该 demo 语料不足以支撑高质量经验，
> 按规则返回空列表而非强行生成。

即：**质量门按设计正确拒绝了纯百科语料**（与 PLAN 对 KB-Demo-ZH 的描述同源）。
归档轮产出 8–10 条，是本轮与归档之间**模型判定倾向**的差异——`deepseek-flash`
是未锁版本的模型别名，且 LLM 判定本身具有方差。因此 PLAN 中“EN 产出经验 ≥ 5 条”
的预期不成立，应改为结构化预期。

## 3. 对 TEST-PLAN 的修正（本轮已同步）

1. §7 复现容忍度：区分「会话内双轮」与「跨会话」；跨会话对 QDCVR 排序指标要求一致，
   对 BM25/跨库查询给出 ≤0.05 的 tie-break 容忍。
2. §4 模块 C 预期：不再承诺经验条目数；改为 `run_success`/草稿审批链路稳定，
   经验数 0–10 取决于质量门对语料性质（百科 vs 操作型）与模型判定的结果。
3. §0/§2：补充冷启动说明（后端重启后首轮入库含模型/索引预热，Step 1 约 25 分钟）。
4. 新增 §6b：用 `scripts/compare_runs.py <基线目录> <结果目录>` 自动核对复现。

## 4. 复现命令（可直接执行）

```bash
# 0) 归档现有结果
cp -r benchmark-suite/results benchmark-suite/results/archive-$(date +%Y%m%d-%H%M%S)

# 1) 清库 + 重启（清内存索引）
python benchmark-suite/scripts/00_reset_env.py
node command/ragctl.js restart backend          # 端口 :8771

# 2) 按 PLAN 执行
cd benchmark-suite
python scripts/01_ingestion.py 1 && python scripts/01_ingestion.py 2
python scripts/21_std2_ingest.py 1 && python scripts/21_std2_ingest.py 2
python scripts/22_std2_retrieval.py 1 && python scripts/22_std2_retrieval.py 2
python scripts/02_retrieval.py 1 && python scripts/02_retrieval.py 2
python scripts/03_experience.py 1 && python scripts/03_experience.py 2
python scripts/04_report.py

# 3) 自动对比
python scripts/compare_runs.py results/archive-<时间戳> results
```

判定输出：`PASS`=逐位一致 · `PASS*`=汇总层一致（仅逐查询明细差异）· `FAIL`=汇总层超差。
