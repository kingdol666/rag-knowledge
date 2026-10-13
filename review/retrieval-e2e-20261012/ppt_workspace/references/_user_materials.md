# 用户材料 — 检索端到端三通道 Benchmark 实测（2026-10-12）

来源：本项目真实运行的 benchmark 实验，全部证据已落盘。**所有数字均来自实测工件，禁止编造或外推。**

## 1. 实验设计

- 统一问题集（3 题）：
  - cm1 = InstructDS query-based 对话摘要数据合成（金标 arXiv:2310.10981，库=计算机与人工智能，131 文档）
  - cm2 = EHR 中风预测 ML 风险因素（金标 arXiv:1904.11280，库=生命科学与医学，53 文档）
  - cm3 = Herbert-Moulton collider benchmark（**域外题**，全库无此内容，应如实拒答）
- 三通道：
  - 通道1 = harness 对外 API 流式 SSE 时间线（`POST /api/claude/chat`，engine=claude，kbEnhanced=true），9 跑，逐工具耗时
  - 通道2 = `exp.py --chatmodes` 非流式系统臂（run `chatmodes-20261012T061102Z-5f9faac`），9 跑，机器门禁
  - 通道3 = `exp.py --retmodes` 纯检索矩阵（run `run-20261012T062847Z-5f9faac`，无 LLM 回答），3 模式 + 3 baseline
- 三模式（外部调用方视角，服务端执行流）：
  - A = 钉库向量快车道（kbIds=[目标库]）
  - B = 全库逐级检索/图书管理员 spine（kbIds=[]）
  - C = 混合检索（钉库 + 宽网+判卷+逐级兜底指令后缀）

## 2. 三模式真实检索流程（SSE 逐工具还原）

- A: 并行 kb_search_two_stage + kb_search_vector（0.8–1.0s，含跨语言查询改写）→ 并行 kb_laya_judge + kb_doc_read（各约 9–10s）→ 作答
- B: kb_list（20 库）→ kb_get_documents 描述层扫描（0.6–1.5s）→ kb_laya_judge 判卷 → 作答；cm1 上兜底 kb_search_vector 挂起 300s（MCP 超时）
- C: 同 A 宽网 → kb_laya_judge → kb_doc_read；证据不足补 kb_list 逐级核查（cm3 拒答前 36 段判卷）

## 3. 通道1 结果（流式, 修正门禁口径=拒答优先）

| 模式 | 题 | 预期 | 端到端s | 工具链 | 检索工具净耗时s | 门 |
|---|---|---|---|---|---|---|
| A | cm1 | found | 55.7 | two_stage→vector→vector→judge | 17.9 | ✅ |
| A | cm2 | found | 48.8 | two_stage→vector→judge→doc_read | 21.2 | ✅ |
| A | cm3 | refusal | 36.4 | kb_list→two_stage→vector | 3.6 | ✅ |
| B | cm1 | found | 353.5 | kb_list→get_documents×3→**vector(挂300s)**→judge | 319.5 | ❌假拒答 |
| B | cm2 | found | 43.2 | kb_list→get_documents×3→judge | 13.2 | ✅ |
| B | cm3 | refusal | 29.9 | kb_list→get_documents×2 | 2.0 | ✅ |
| C | cm1 | found | 43.1 | two_stage→vector→judge→doc_read | 11.7 | ✅ |
| C | cm2 | found | 45.6 | two_stage→vector→judge→doc_read | 19.8 | ✅ |
| C | cm3 | refusal | 65.0 | two_stage→vector→judge→kb_list | 21.8 | ✅ |

- 通道1 门禁 8/9（唯一 FAIL = B×cm1 假拒答）；均值 A=47.0 / B=142.2 / C=51.2s

## 4. 通道2 结果（非流式机器门禁）

| 模式 | cm1 | cm2 | cm3 | 模式均值 | 成本均值/题 |
|---|---|---|---|---|---|
| A | 53.0s✅ | 65.3s✅ | 25.7s✅(拒答) | 48.0s | $0.182 |
| B | 41.4s❌假拒答 | 91.9s✅ | 66.0s✅(拒答) | 66.4s | $0.300 |
| C | 58.3s✅ | 100.0s✅ | 48.3s✅(拒答) | 68.9s | $0.219 |

- 通道2 门禁 8/9；turns 均值 A=5.3 / B=8.3 / C=7.0

## 5. 通道3 纯检索（无 LLM）+ baseline 同题对照

| 方法 | q1(=cm1) 耗时 | q2(=cm2) 耗时 | 金标 | 保底docs | 性质 |
|---|---|---|---|---|---|
| mode_A | 25.0s | 22.7s | ✅✅ | 18/18 | 活库+Laya判卷 |
| mode_B | 25.0s | 10.2s | ✅✅ | 23/11 | 脚本化图书管理员 |
| mode_C | 37.3s | 33.7s | ✅✅ | 12/12 | A∥B 并行合并 |
| bm25 | ≈0 | ≈0 | ✅✅ rank-1 | 10/10 | 本地静态100篇 |
| vector | 0.1s | 0.1s | ✅✅ rank-1 (0.756/0.842) | 1/3 | 平台向量chunk级 |
| rrf | ≈0 | ≈0 | ✅✅ rank-1 | 10/10 | bm25+vector融合 |

- 通道3 金标 12/12（含修掉空库问题后的 baseline）
- **历史对照（2026-09-26 基线）**：B 342/234s → 25.0/10.2s（13~23×）；C 1152/1818s → 37.3/33.7s（31~54×）

## 6. 关键发现（真实产出）

1. **模式 B × cm1 系统性假拒答（三连：假拒答353.5s / 假拒答41.4s / 挂起600s）**。根因：131 文档书架 `kb_get_documents` catalog = **65.5KB** 一次性灌入上下文，LLM 注意力扫漏金标（描述明写 InstructDS）；对照 B×cm2 成功 = 53 文档≈25KB。**脚本化图书管理员同题 25.0s/10.2s 双金标** → 描述层扫描需机械化辅助。
2. vector baseline 默认库 Corpus-Chunks800 为空（reset 后 0 命中）→ `RAG_BENCH_VECTOR_KB=""` 跨库口径修复 → 12/12。
3. 判卷门问题回显假阳性已修（拒答优先 + 结论窗口前 500 字），本报告全部门禁按修正口径重算。

## 7. 内容质量抽证（回答可验证细节）

- A×cm2 答出 “29,072 条 EHR 记录、高血压/心脏病/年龄/BMI/吸烟、特征弱相关不应降维”
- C×cm1 逐字引用论文 §3.2 "three-step approach…summary-anchored query generation, query filtering and query-based summary generation"，含 Flan-T5-XL
- B×cm2 Laya 判卷 8/8 段存活最高分 0.94；答出 “PCA 年龄+婚姻状态贡献最大、MLP 75.02%”
- 三模式对 cm3 全部如实拒答（A 36.4s / B 29.9s / C 65.0s）

## 8. 证据文件（可核查）

- 报告：`review/retrieval-e2e-20261012/REPORT.md` + `REPORT.html`（visual-judge pass）
- 逐臂：`review/retrieval-e2e-20261012/c1_*.json`（SSE timeline+tool spans）+ `extra_B-cm1_confirm3.json`
- exp runs：`benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/`、`run-20261012T062847Z-5f9faac/`
