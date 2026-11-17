# 实验结果总索引（MASTER INDEX，2026-11-12 清理后）

> 本文档是**全部实验结果的唯一入口索引**：每一族实验的权威数字、可引用产物路径、
> 归档位置。按"唯一可引用证据"原则维护——凡与本表冲突的旧数字一律以表内路径为准。

---

## 1. 逐级检索机制实验（论文主证据链）

**位置**：`review/experiment-redesign-20261101/`
**权威结果**：`RESULTS.md`（唯一可引用汇总）· **可引用 bench**：`artifacts/final_bench/`
**复现指导**：`EXPERIMENT-PIPELINE.md`（自足）

### 1.1 终版主表（2026-11-11 内容层优化轮晋升，gold n=72/臂）

| 臂 | 金标命中 | 说明 |
|---|---:|---|
| **A0h 逐级+chunk窗口并集（推荐主臂）** | **72.2%** (52/72) | vs A0 p=6.1e-05*；309KB/题（1/80 通读）；tool 13.8s |
| PD 精确逐文档 | 63.9% (46/72) | 无导航对照，p=.0039* |
| A0f 修窗逐级 | 62.5% (45/72) | 全窗判卷，p=.0078* |
| A0 基线逐级 | 51.4% (37/72) | 历史基线；路由 72/72 |
| A1b 十库向量并集 | 54.2% (39/72) | p=.69 与 A0 无显著差 |
| A2 无证据门 | 34.7% (25/72) | **p=.0227* 显著劣**（证据门价值被隔离） |
| A3 无描述层 | 45.8% (33/72) | 路由 37/72；**端到端数值跨 run 敏感，只引定性** |
| A1 通读上界 | 100% | 24.3MB/题、879 卷 |
| floor | BM25 60% / dense 47.5% / RRF 65% | dense/RRF=平台组成指纹（见 §1.3），跨环境只比 BM25 |

关键机制结论：①描述层路由 72/72（A0）vs 51-68% 散布（A3）；②证据门显著隔离（A2 劣化）；
③A0h 剩余 20 缺口=深部判卷未命中（题点词型金标 Laya<0.5，已知限制）。

### 1.2 R3 复现轮（2026-11-12，第三次独立复现）——**主结论可信裁定成立**

**报告**：`review/experiment-redesign-20261101/RESULTS-REPLICATION-20261112.md`
**产物**：`artifacts/replication_bench_20261112/`（checkpoint 可续跑）+ `artifacts/e2e_validation_r3/`

| 臂 | 终版→R3 | 逐题一致率 |
|---|---|---:|
| A0h / PD / A0f | 70.8% / 62.5% / 61.1% | 各 98.6%（71/72，同 qid walden 索引噪声） |
| A0 | 54.2%（+2.8pp） | 94.4%（含 2 例文学-中文重建修复效应） |
| A1b / A2 | 54.2% / 34.7%（不变） | **100% 零翻转（确定性常数，可直接引用）** |
| A3 | 34.7%（−11.1pp） | 75%——端到端跨 run 翻转（.4545 ns→.0026*），根因=路由卡库健康态；定性结论三跑全稳 |
| F-BM25 | 60.0%（不变） | 逐题零翻转 |

审计：qid 唯一 · 路由卡零泄漏 · A1b/A2/PD 候选 100% ∈ 十评测库 · **金标回贴 179/179**。
Reviewer：APPROVE（独立重算全吻合）。真实 Agent 车道（omp + ustc/deepseek-flash）：**7/7**。

### 1.3 平台状态与归因要点（防未来误读）

- **floor dense/RRF = 平台组成指纹**：kb_id="" 全局搜索候选分布随"哪些 chroma 集合存在且可读"变化
  （本轮三态 17→17→14/40）；终版"卫生 floor"实为孪生库段损坏=不可见的偶然卫生。**跨环境只比 BM25**。
- **A0 的 F-hlm-2/3 新增命中** = 文学-中文 chroma 段损坏经 s0j2 干净周期重建后的修复效应（终版该库带病运行）。
- **语料 confound**：MD语料-文学-英文 461 卷（终版 434 + 罪与罚 27，2026-11-10 入库）→
  readall 25.5MB/题（终版 24.3MB）、shelf 906（终版 879）。
- A1-readall 复现长跑：`--skip-done` 断点续跑（`run_r3_serial.sh` STEP-7），checkpoint 行数即进度，
  补齐后重跑 `s6c2_merge_r3.py` → `s6_stats.py` → `s6d_compare_runs.py` 即得全量。

### 1.4 真实 Agent 采样对照

| 车道 | 题集 | 结果 | 产物 |
|---|---|---|---|
| claude harness（终版） | AG1-AG6 | 6/6 completed、6/6 doc_path 溯源、220-350s/题 | `artifacts/e2e_validation/` |
| omp harness（R3，模型 ustc/deepseek-flash:max） | AG1-AG6 + AG7-ood | **7/7**（含诚实 NOT_FOUND） | `artifacts/e2e_validation_r3/` |

---

## 2. 平台功能验收（工程可信证据）

| 验收轮 | 结果 | 位置 |
|---|---|---|
| E2E 10 场景（20260930） | 全过（chat 5 场景含拒答 33.5s/resume/混合 + agent/chat 4 连发） | review/（归档索引见 §4） |
| 三车道 9/9 + 管理全量 + Run4/5 | 20261021-22，reviewer APPROVE 6/6 | review/prod-demo-20261021-run4/ + run5-20261022/ |
| 全链路压测 41 项 | 全过；瓶颈=meditation 冷缓存 30s + 向量吞吐 5.3RPS | review/stability（已归档 tarball） |
| 21 skill 四层实测 | 118/119/120v6/122 全绿 + 修复 7 项 | 20260927 工件 |
| 逐级检索优化轮（11-11） | A0h 72.2%（p=.0001）、漏检归因=judge-miss 30 | RESULTS.md + attribution_a0_misses.json |
| Live acceptance（11-11） | LIVE GO | memory live-acceptance-20261111 |
| **2026-11-12 下午全链演示** | 论文解析→入库→检索（omp+claude 双 harness）+ 整理功能 | `review/experiment-redesign-20261101/artifacts/demo-20261112/` |

---

## 3. 论文相关结果（CIKM/KBS）

| 结果族 | 位置 |
|---|---|
| **KBS 论文三类实验整理版（2026-11-13，仅描述消融/内容检索对比/回答质量）** | paper-kbs/PAPER-RESULTS-20261113.md |
| CIKM demo 论文三轨/五臂 380-trace 轮 | benchmark-suite/results/（runs/ + 归档 archive-superseded tarball） |
| KBS 20 页论文数据（30 单元 + 19 闸门） | benchmark-suite/results/paper_report.json + PAPER-REPORT.html（run-20261013T094350Z） |
| 人读入口（KBS） | TEST-RESULTS/README.md（含独立复算 verify.py） |
| 论文 provenance | .bench_backup_20260917/ + benchmark-web/（保留，勿删） |

## 4. 归档与清理记录

| 时间 | 动作 | 位置 |
|---|---|---|
| 2026-10-13 | 692 历史结果文件 + review 36 目录归档 | benchmark-suite/results/archive-superseded/ + review/archive-superseded/ |
| 2026-11-10 | 五臂旧 traces/viz（与新 8 臂重合）删除 | final_bench 内（零数据丢失，us2 审计件保留） |
| 2026-11-12 | R3 attempt1 路由污染轮中止隔离 | artifacts/replication_bench_20261112/attempt1_aborted_route_card_death/ |
| 2026-11-12 | repo 根垃圾/tmp/旧 console 日志归档删除 | review/archive-20261112-cleanup/（tarball×2 + MANIFEST.md） |

## 5. 数字引用红线

1. 唯一可引用 bench = `artifacts/final_bench/`；R3 数字 = `artifacts/replication_bench_20261112/`（并列证据，不替换终版）。
2. `qa_questions.json`（BQ01-10）/`qa_quick10.json`（QK）/`qa_questions_r2.json`（R2Q）是**三套不同题集**，数字不得混用。
3. floor 的 dense/RRF 列不可跨环境横比；BM25 列是平台无关锚。
4. A3 端到端数值不单独引用；A1b/A2 可当确定性常数。
5. 旧 readall 3.2MB/题、旧 A1-readall 双口径、`kb_id=""` 版 A1b/A2——均已作废，勿再引。
6. **RAG 向量对比数据禁令（2026-11-13）**：论文（正文+补充材料）不得出现与传统 RAG
   向量检索的对比结果（dense/RRF/混合车道表等，清除清单见 PAPER-RESULTS-20261113.md §4）；
   对比只允许三类——描述层消融、基于内容检索对比（PD/readall/BM25/A1b 自配置）、真实回答质量。
