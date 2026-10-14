# TEST-RESULTS — 当前最新的一轮测试结果（唯一权威副本）

> 这一轮就是论文实验部分所依据的那一轮。除本目录指向的产物外，
> `benchmark-suite/results/` 与 `review/` 里其余历史结果已归档（见文末）。

## 1. 这一轮测的是什么

| 项 | 值 |
|---|---|
| Run ID | `run-20261013T094350Z-5f9faac` |
| 时间 | 2026-10-13 09:43 UTC（17:43 CST 起跑），约 17 分钟 |
| 代码版本 | `5f9faac`（branch `feat/soul-persona-system`），prompt `v4-neutral`，config `9fb259c0cf2b6dea` |
| 题集 | `benchmark-suite/data/papers/qa_questions.json`，BQ01–BQ10（论文专用题集） |
| 单元数 | 30（3 条检索臂 × 10 题），**0 哨兵 / 0 错误 / 0 空洞** |
| 花费 | **$17.25**（真实 API 消耗；`run_manifest.json: total_cost_usd` = 17.2454，与逐单元求和一致），平均 33.1 s/单元 |
| 执行方式 | 真实 harness：每单元一次 `POST /api/claude/chat`，返回真实 `sessionId` / `num_turns` / `total_cost_usd` |

**三条臂只差"给什么检索工具"，不差提示词、不差模型：**

| 臂 | 给的工具 | 语料 |
|---|---|---|
| A `a2` 平台 | 完整 `kb_*` 只读工具面（含 `kb_laya_judge` 判定引擎） | 活实例 21 库 / 322 文档 |
| B `b` 裸 agent | 只有 `Read` / `Grep` / `Glob` | 导出的 100 篇 markdown |
| C `c` 稠密检索 | 只给 1 个 `kb_search_vector`（top_k 10，阈值 0） | `Corpus-Chunks800` 4,528 块 |

## 2. 结果（论文里的数字就是这些）

| 指标 | A 平台 | B 裸 agent | C 稠密 |
|---|---|---|---|
| grounded（严格 arXiv-id 接地） | **10/10** | **10/10** | **10/10** |
| strict keywords（全部金标关键词，修正标注） | 9/10 | 9/10 | 9/10 |
| alias-aware keywords（声明别名） | **10/10** | **10/10** | **10/10** |
| cited（part/section/table 标记，含罗马节号） | **9/10** | 7/10 | **2/10** |
| 平均延迟 | 52.6 s | 22.2 s | 24.5 s |
| 平均成本 | $0.7110 | $0.4867 | $0.5269 |
| 平均工具调用 | 6.0 | 6.4 | 3.7 |

**怎么读这张表**：三臂接地率完全相同 → **"能不能找到对的论文"已不是区分点**；
真正的差异在 **cited 9 / 7 / 2** —— 平台给出可点验的定位（part·section·table），
稠密臂只能交出匿名 chunk。论文的贡献点因此落在 **evidence inspectability**，不是"更准"。

平台臂**既最慢也最贵**（10 题里 9 题比裸 agent 贵，配对 t = +4.84，df 9）——这是设计代价，如实写。

strict keywords 三处未满分都是**词形假阴性**（答案实质正确）：`a2/BQ06` 答的是
saturation *specific humidity* 而金标写 vapor pressure、`b/BQ09` 用缩写 MLP、`c/BQ10`
把 `immune evasion` 说成 immune exhaustion / reduced antigen presentation；
修正概念标注并声明别名后三臂均为 10/10。注意 BQ06 的**原始金标与源论文不符**
（原始标注把"降水效率"当主控因子，源论文的稳健结论是热力学项）——原始标注下
a2 strict 为 10/9/9（对错金标得分），修正后三臂 9/9/9；两套 grade 文件
（`exp_r2_grade_original_revised.json` / `exp_r2_grade_corrected.json`）都保留。

## 3. 稳定性套件（27/27）

`review/stability-multiround-20261013/results/r{1,2,3}_{attention,seismology,pickles}_{A,B,C}.json`

3 类任务（可答：注意力公式；库内不覆盖：地震波分类；库外：腌泡菜）× 3 车道 × 3 轮 = 27 单元：
**27/27 HTTP 200、27/27 行为正确、27/27 车道契约合规**；延迟 15–182 s，中位 52 s。

## 4. 怎么自己验一遍（不需要相信任何项目脚本）

```bash
python TEST-RESULTS/verify.py          # 独立复算：grounded / keyword / cited / 延迟 / 成本
```

它只用标准库，自己重新实现指标，直接读原始 `track_*.json`，对照
`paper-kbs/tex/journal_20p/n8c_eval.tex`（Table tab:e5-arms）的论文数字——
grounded 10/10/10、strict keywords 9/10×3、cited 9/7/2、chunk 5/0/7、
延迟 52.6/22.2/24.5 s、成本 $0.711/$0.487/$0.527——逐项打印"观测 vs 论文"。
cited 的标记正则与 grade JSON 里记录的定义逐字一致（含罗马数字节号 §III-C）。
**2026-10-15 实测：PASS（30 格全部重算一致 + manifest 总成本对账）。**

项目自己的对账链（更全，含语料/闸门/表1）：

```bash
cd benchmark-suite
python scripts/150_final_pipeline.py --assert-only --run results/runs/run-20261013T094350Z-5f9faac   # 18/18
python scripts/161_final_evidence.py --run results/runs/run-20261013T094350Z-5f9faac               # 19/19
```

## 5. 重跑整轮（会真实花钱）

```bash
cd benchmark-suite
python scripts/150_final_pipeline.py            # Gate0-3 → 30 单元 → 判分 → 对账（约 1-2 h / ~$17）
python scripts/160_run_paper_pipeline.py        # S1-S5：语料体检 → 三轨 → 稳定性 → 证据 → HTML
```

前置条件：web `6789`、backend `8771`、kb-mcp（stdio 或 SSE `:8000`）在线；
`Corpus-Chunks800` 必须**非空**（用 `151_smoke_probe.py` 查；空则先跑
`106_exp_corpus_r2.py --reuse-export`）。

## 6. 产物地图

| 文件 | 内容 |
|---|---|
| `raw-output.txt` | 本轮 19 闸门的完整输出（可直接贴给合作者） |
| `verify.py` | 独立复算脚本（本文档第 4 节） |
| `benchmark-suite/results/paper_report.json` | 论文级证据包（机器可读；闸门 + 逐题明细） |
| `benchmark-suite/results/PAPER-REPORT.html` | 同一份证据的网页版（可直接打开读） |
| `benchmark-suite/results/paper_numbers.json` | 论文 `\NUM*` 宏 vs 实测，18 条对账 |
| `benchmark-suite/results/exp_r2_grade.json` | 三臂判分（grounded/keyword/cited/延迟/成本） |
| `benchmark-suite/results/R2-EXP-3TRACK-REPORT.md` | 判分报告（人读版） |
| `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/` | **原始证据**：30 个 `track_*.json` + `SUMMARY.md`（逐字答案 + 工具轨迹）+ `run_manifest.json` |
| `benchmark-suite/results/archive-superseded/` | 被清理的历史结果（tar.gz + MANIFEST + DELETED 记录，可完整恢复） |
| `review/archive-superseded/` | 被清理的 36 个历史 review 目录（tar.gz + 清单） |

## 7. 已清理与保留

**保留**：上一节全部 + `review/stability-multiround-20261013/`。

**已归档（可恢复，不是销毁）**：
- `benchmark-suite/results/`：692 个文件 / 12.72 MB → `archive-superseded/superseded-20261013-batch2.tar.gz`
  （含 `today-20261013/` 的 Quick10、refusal、ladder、CRUD 证据，以及 3 个旧 run 目录）
  另有第一批：`superseded-20261013.tar.gz`（716 文件，含 6 个 `experiment_chat_2026*` 旧三轨目录）
- `review/`：36 个目录 / 1,560 文件 / 263 MB → `review/archive-superseded/review-superseded-20261013.tar.gz`

恢复方式：`tar -xzf <archive> -C <repo>`（归档内路径就是原始相对路径）。

## 8. 如实说明（别在论文里越界）

- **可复现的是"方法 + 判分 + 原始证据"**（判分是纯正则、无 LLM；30 个单元的答案与工具轨迹都在 repo 里）；
  **延迟/成本/措辞不承诺逐字复现**——它们取决于 CLI 版本、GPU 与缓存状态。
- 语料侧的 Table 1 证据（322 文档 / 5 门类 / 4,528 块 / 15 个检索回归探针）
  由 `scripts/155_paper_state_audit.py`、`scripts/158_a_retrieval_regression.py`、
  `scripts/108_pipeline_evidence.py` 对**活实例**产出，可审计但**入库流程本身不可一键重跑**（需重新入库 100 篇）。
- 三臂共用同一个模型与 harness，因此这是**受控对比**，不是"独立第三方复现"。
