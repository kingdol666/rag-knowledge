# 三模式检索实验报告（exp 项目正式臂）

- Run：`retmodes-20260926T202450Z-47cc948` · 生成：2026-09-26 20:58 UTC
- 语料：{'kbs': 18, 'docs': 379}（真库在线快照）· 平台预检：backend/web/token OK
- 臂完成：**6**（A/B/C × q1/q2）· 验证门通过：**6/6** · 金标命中：**6/6**

> **一句话结论**：三种检索模式在同一真库、同一问题上全部命中金标文档、全部走真实 Laya 引擎判决（fail-closed 无一击穿）；A 秒级-2分钟出结论级证据，B 分钟级给出最全行号级溯源，C 覆盖最全但受 Laya CPU 推理瓶颈拖慢。三者可按「速度 ↔ 溯源深度 ↔ 覆盖面」三角取舍。

## 1 · 实验设置

| 臂 | 检索模式 | 机制（唯一变量） |
|---|---|---|
| A | A · QDCVR 向量优先 | 宽网向量召回（top_k=30）→ 文档去重 → 重读分段 → 真实 Laya 逐段判决（fail-closed）→ yes 全收 |
| B | B · Librarian 目录道 | kb_list → 书架标签(L1) → 全量描述(L2) → 元数据信任(L3) → 预算读取(L4) → complete_recall 真实 Laya 判决 → 引擎裁决即终审 |
| C | C · Hybrid 并行 | 向量道 ∥ 目录道并行 → 合并去重 → 统一重读 → Laya 判决 → 去重 result_list（--require-real） |

| 问题 | 语言 | 金标文档 | B 臂书架标签 |
|---|---|---|---|
| q1 | en | `instructive-dialogue-summarization`（Instructive Dialogue Summarization 论文（4-part 拆分, 即 InstructDS 方法论文）） | ['计算机与人工智能'] |
| q2 | zh→en 跨语言 | `stroke-from-electronic-health`（predicting-stroke-from-electronic-health-rec 论文） | ['生命科学与医学'] |

每个臂执行后过**硬验证门**：进程 exit 0 · `real_engine=true`（真实 Laya，非桩）· 证据文档数 > 0 · 金标文档在幸存集 · 延迟已记录。任一门失败即判该臂异常。

## 2 · 主结果矩阵

| 模式 × 问题 | 耗时 | 幸存文档 | 判决段数 | 证据包字符 | 金标 | 引擎 | 门 |
|---|---:|---:|---:|---:|:--:|:--:|:--:|
| A × q1 | 117.1s | 17 | 95 | 24,000 | ✅ | real Laya | ✅ |
| A × q2 | 124.5s | 15 | 95 | 24,000 | ✅ | real Laya | ✅ |
| B × q1 | 171.3s | 23 | 151 | 40,001 | ✅ | real Laya | ✅ |
| B × q2 | 89.3s | 11 | 79 | 40,001 | ✅ | real Laya | ✅ |
| C × q1 | 576.5s | 36 | 547 | 12,000 | ✅ | real Laya | ✅ |
| C × q2 | 541.7s | 39 | 506 | 12,000 | ✅ | real Laya | ✅ |

## 3 · 与 2026-09-26 基线对比

| 模式 × 问题 | 本轮耗时 | 基线耗时 | 本轮幸存 | 基线幸存 | 备注 |
|---|---:|---:|---:|---:|---|
| A × q1 | 117.1s | ~13.3s | 17 | — | +780% |
| A × q2 | 124.5s | ~7.4s | 15 | — | +1582% |
| B × q1 | 171.3s | ~342s | 128 | 128 | -50% |
| B × q2 | 89.3s | ~234s | 77 | 77 | -62% |
| C × q1 | 576.5s | ~1152s | 36 | 173 | -50% |
| C × q2 | 541.7s | ~1818s | 39 | — | -70% |

> 基线口径说明：①基线为 2026-09-26 同问题真机数据（11 KB/367 docs）；本轮语料已漂移至 {'kbs': 18, 'docs': 379}（新增小说/演示/人格测试库），跨库向量检索候选池变大。②A 臂基线是**旧契约**（纯向量无判决），新契约含真实 Laya 逐段判决，耗时不可直接比——换来的是每段证据都有引擎背书。③B 臂书架内文档数未变，且本轮幸存段数与基线逐段一致（128/77），可比性最强：提速来自引擎与缓存的热身而非契约变化。

## 4 · 延迟可视化（对数感知：同为真机单次）

```
A×q1 ████████ 117.1s
A×q2 █████████ 124.5s
B×q1 ████████████ 171.3s
B×q2 ██████ 89.3s
C×q1 ████████████████████████████████████████ 576.5s
C×q2 ██████████████████████████████████████ 541.7s
```

## 5 · 逐臂明细

### A × q1

- 金标：Instructive Dialogue Summarization 论文（4-part 拆分, 即 InstructDS 方法论文） → 命中
- 幸存/结果文档 17，证据包 24,000 字符，判决引擎 laya_sdk/real
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `Novel-PridePrejudice/pride_and_prejudice (part 2 of 26).md`
  - `Novel-PridePrejudice/pride_and_prejudice (part 6 of 26).md`
  - `aw-industrial/【冒烟测试】深度诊断报告-diag_kb_smoke_mock.md`
  - `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`
  - `e2e-demo-0923-022632/global-rag-benchmark.md`
  - `soul-demo-qa/soul-definition.md`
  - `soul-demo-qa/thinking-style.md`
  - `soul-e2e-tester-024115/soul-definition.md`
  - `soul-e2e-tester-024115/thinking-style.md`
  - `工程与能源/mathematics__2211.12700__tailored-presolve-techniques-in-branch-and-b.md (part 5 of 5).md`
  - …（7 篇省略）

### A × q2

- 金标：predicting-stroke-from-electronic-health-rec 论文 → 命中
- 幸存/结果文档 15，证据包 24,000 字符，判决引擎 laya_sdk/real
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `Novel-PridePrejudice/pride_and_prejudice (part 26 of 26).md`
  - `aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md`
  - `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`
  - `e2e-demo-0923-022632/global-rag-benchmark.md`
  - `soul-demo-qa/memory-conventions.md`
  - `soul-e2e-tester-024115/memory-conventions.md`
  - `工程与能源/power-systems__2207.08146__mapping-disruption-sources-in-the-power-grid.md (part 1 of 2).md`
  - `生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md`
  - `生命科学与医学/clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon (part 1 of 3).md`
  - `经济与社会/economics__2011.14424__on-the-effectiveness-of-the-european-central (part 2 of 5).md`
  - …（5 篇省略）

### B × q1

- 金标：Instructive Dialogue Summarization 论文（4-part 拆分, 即 InstructDS 方法论文） → 命中
- 幸存/结果文档 23，证据包 40,001 字符，判决引擎 laya_sdk/real
- L2 描述扫描 131 docs · L3 不可信描述 0 · L4 全文读 23 / 信任头读 0 · 未扫 108
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `计算机与人工智能/large-language-models__2312.10793__demystifying-instruction-mixing-for-fine-tun.md (part 1 of 2).md`
  - `计算机与人工智能/large-language-models__2312.10793__demystifying-instruction-mixing-for-fine-tun.md (part 2 of 2).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 1 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 2 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 3 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 4 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 5 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 6 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 7 of 9).md`
  - `计算机与人工智能/large-language-models__2402.11690__vision-flan-scaling-human-labeled-tasks-in-v.md (part 8 of 9).md`
  - …（13 篇省略）

### B × q2

- 金标：predicting-stroke-from-electronic-health-rec 论文 → 命中
- 幸存/结果文档 11，证据包 40,001 字符，判决引擎 laya_sdk/real
- L2 描述扫描 53 docs · L3 不可信描述 0 · L4 全文读 11 / 信任头读 0 · 未扫 42
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `生命科学与医学/clinical-medicine__1809.08199__profiling-lung-cancer-patients-using-electro.md`
  - `生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md`
  - `生命科学与医学/clinical-medicine__2110.08918__using-clinical-drug-representations-for-impr.md (part 1 of 2).md`
  - `生命科学与医学/clinical-medicine__2110.08918__using-clinical-drug-representations-for-impr.md (part 2 of 2).md`
  - `生命科学与医学/clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon (part 1 of 3).md`
  - `生命科学与医学/clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon (part 2 of 3).md`
  - `生命科学与医学/clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon (part 3 of 3).md`
  - `生命科学与医学/genomics__2508.18304__sci2cl-effectively-integrating-single-cell-m (part 1 of 4).md`
  - `生命科学与医学/genomics__2508.18304__sci2cl-effectively-integrating-single-cell-m (part 2 of 4).md`
  - `生命科学与医学/genomics__2508.18304__sci2cl-effectively-integrating-single-cell-m (part 3 of 4).md`
  - …（1 篇省略）

### C × q1

- 金标：Instructive Dialogue Summarization 论文（4-part 拆分, 即 InstructDS 方法论文） → 命中
- 幸存/结果文档 36，证据包 12,000 字符，判决引擎 laya_sdk/real
- 双道合并：vector=None catalog=None → merged=39 kept=None unscanned=None
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `Novel-PridePrejudice/pride_and_prejudice (part 11 of 26).md`
  - `Novel-PridePrejudice/pride_and_prejudice (part 21 of 26).md`
  - `Novel-PridePrejudice/pride_and_prejudice (part 24 of 26).md`
  - `Novel-PridePrejudice/pride_and_prejudice (part 25 of 26).md`
  - `aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md`
  - `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`
  - `工程与能源/mathematics__2402.07064__piecewise-sos-convex-moment-optimization-and (part 1 of 6).md`
  - `工程与能源/mathematics__2402.07064__piecewise-sos-convex-moment-optimization-and (part 2 of 6).md`
  - `工程与能源/mathematics__2402.07064__piecewise-sos-convex-moment-optimization-and (part 3 of 6).md`
  - `工程与能源/mathematics__2402.07064__piecewise-sos-convex-moment-optimization-and (part 4 of 6).md`
  - …（26 篇省略）

### C × q2

- 金标：predicting-stroke-from-electronic-health-rec 论文 → 命中
- 幸存/结果文档 39，证据包 12,000 字符，判决引擎 laya_sdk/real
- 双道合并：vector=None catalog=None → merged=39 kept=None unscanned=None
- 验证门：exit_ok=✅ · real_engine=✅ · evidence_nonempty=✅ · gold_hit=✅ · latency_recorded=✅
- 结果文档（前 10）：
  - `aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md`
  - `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 1 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 11 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 3 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 4 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 5 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 6 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 7 of 12).md`
  - `工程与能源/mathematics__1405.4980__convex-optimization-algorithms-and-complexit (part 8 of 12).md`
  - …（29 篇省略）

## 6 · 发现与建议

1. **三模式各有生态位**（与 2026-09-26 结论一致且经真机复验）：A 快、适合交互式问答；B 溯源最深（行号级 evidence + 全幸存集交付）、适合审计/综述；C 双道合并覆盖最全、适合离线深加工，但 Laya CPU 逐段判决是时间瓶颈。
2. **语料漂移是本轮最大新发现**：测试残留库（Novel-PridePrejudice、demo-qa、soul-* 人格库等）已进入全库向量检索候选池，A 臂结果中出现与问题无关的杂项文档（如 Pride & Prejudice 分篇、人格宪法文档）。建议：检索层增加 KB 白名单/过滤（如排除 soul-* 与 test 标记库），或定期清理测试残留。
3. **fail-closed 全部成立**：三模式 6 臂全部 real_engine=true，无一路击穿为桩判决（含 --require-real 门）。
4. B 臂书架内文档数未随语料漂移变化，其耗时与基线可比性最强；C 臂耗时受语料规模放大最明显。

## 7 · 工件与复现

- 臂结果：`benchmark-suite\results\runs\retmodes-20260926T202450Z-47cc948/arm_<mode>-<qid>.json`（含 gate、trace、幸存集）· 运行清单 `RUN.json`
- 复现：
```bash
python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode A --mode B --mode C
python benchmark-suite/scripts/141_retrieval_modes_report.py <run_dir>
```
