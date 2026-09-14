# 全流程复现验证报告（第二轮 · 完整清库重跑）

> 执行日期：2026-09-14 · 归档基线：`results/archive-20260914-113032/`
> 方法：清空全部知识库 → 重启后端（清内存索引）→ 按 TEST-PLAN + EXPERIMENT-DESIGN
> 全量重跑（所有 4 个语料重新入库，KB 标识符全新）→ 逐项对比。
> 对比工具：`scripts/98_compare_archive.py`（指标层严格比对；计时/时间戳/指纹字段忽略）

## 1. 结论

**确定性家族（论文全部主表、消融、多域基准、路由 oracle、分层分析）在指标层
逐位一致（IDENTICAL，零差异）**；LLM 生成/评审通道（冥想、经验kit、judge）
呈现论文已作为 finding 报告的运行间方差。

| 结果家族 | 类别 | 判定 |
|---|---|---|
| `module_a_ingestion_r{1,2}` · `module_a_std2_r{1,2}` · `module_a_std_r1` | 确定性 | **IDENTICAL** |
| `module_b_std2_r{1,2}`（SciFact 主表） | 确定性 | **IDENTICAL** |
| `module_b_retrieval_r{1,2}`（in-house 主表） | 确定性 | **IDENTICAL**（仅 `search_s`/`verify_s` 计时不同） |
| `ablation_scifact_{1,2}`（组件消融） | 确定性 | **IDENTICAL** |
| `hotpot_main_{1,2}`（多域公开基准） | 确定性 | **IDENTICAL** |
| `routing_oracle_1`（路由 oracle） | 确定性 | **IDENTICAL** |
| `stratified_adjudication`（重叠分层） | 确定性 | **IDENTICAL** |
| `module_c_experience_r{1,2}`（冥想） | LLM | 方差（归档 0 条 → 本轮 3 条，judge 5.0/5.67） |
| `experience_suite_{1,2}`（3 轮重置研究） | LLM | 方差（9 轮中 3 轮产出，judge 7–9） |
| `judge_agreement_1`（双 judge 信度） | LLM | 方差（κ 0.40 → 0.33；同为“中等一致”） |
| `e4_baselines_fixed`（经验基线） | LLM | 方差（ours 四次运行均居首：6.00/5.50/5.25/5.25） |

## 2. 关键复现证据

- 全部四个语料（demo 三库 16 文档 / SciFact 148 / SQuAD 8 / HotpotQA 9 库 454）
  在**全新 KB 标识符**下重建后，检索指标（Hit@k / Recall@k / nDCG@10 / P@5 / MRR /
  answer@k）与归档完全一致——说明此前的跨会话 tie-break 差异并非稳定现象。
- QDCVR 链路证据同样复现：demo `chars_read=3938.8`、`verify_pass_rate=0.5167`、
  `rerank_changed_rate=0.2`；SciFact `chars_read=4265.6`、`verify_pass=3.0`。
- 新增复现产物：`results/repro_compare_full.json`（逐字段差异清单）、
  `results/repro-full.log`（全流程日志）、`run-*/system_scale.json`、
  `run-*/e2e_surface.json`（26/26）。

## 3. LLM 通道方差的处置（已写入论文）

冥想/评审为 LLM 通道，运行间不同是**已报告现象**而非缺陷：论文 §7 报告了
9 轮状态重置研究（3 轮产出，judge 7–9）、双 judge 信度（κ 0.33–0.40、|Δ| 1.13–1.33）
与四次独立基线运行（排序恒为 ours 居首）。论文不引用单次有利运行。

## 4. 本轮发现并修复的论文-系统不一致（详见提交信息）

1. **语料口径**（严重）：in-house 原写 “13 KBs / 154 docs / 13,709 chunks / 八大学科”，
   实测基准跑在 3 个 demo 库 16 文档上 → 已按实测改写（Setup / Stage 2 / 摘要 / C1 / Table 5 caption）。
2. **引擎数**：15 → **14**（注册表与代码；API 列 15 含 heuristic 回退，已注明）。
3. **Table 1 硬编码字面量**：13/154/13,709/179/2,502/114 原为手写且自称“来自部署” →
   改为 `82_system_scale.py` 实测（94 工具 / 14 KB-skills / 14 引擎 / 113 端点 / 124 路由）。
4. **e2e 声明无生产者**：73/73 引用不存在的文件 → 新增 `80_e2e_surface.py`
   （HTTP 外部驱动，8 组，**26/26 通过**，JSON+指纹产物）。
5. **Table 5 漏报日语组** → 增补（0.750 vs dense 1.000）。
6. **TEST-PLAN 查询数** 19 → 20。

## 5. 复现命令

```bash
cp -r benchmark-suite/results benchmark-suite/results/archive-$(date +%Y%m%d-%H%M%S)
python benchmark-suite/scripts/00_reset_env.py
node command/ragctl.js restart backend
bash benchmark-suite/scripts/99_repro_pipeline.sh          # 全流程（约 5.5 小时）
python benchmark-suite/scripts/98_compare_archive.py \
       benchmark-suite/results/archive-<ts> benchmark-suite/results
```
