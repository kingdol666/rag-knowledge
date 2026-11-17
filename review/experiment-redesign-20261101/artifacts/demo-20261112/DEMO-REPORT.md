# 实机演示与 API 测试报告（demo-20261112）

> 任务：清理后启动真实项目，实机交互演示 + API 测试——验证 omp / claude code 双 harness 集成，
> 任选论文（DeepSeek-R1, arXiv 2501.12948）完成 **解析 → 上传入库 → 检索** 全链，记录检索增强
> 回答并评价质量；另验证知识库整理功能。平台：backend 8771 / web 6789 / kb-mcp stdio+8000，全绿。
> 证据目录：`artifacts/demo-20261112/`（本目录，全部原始 JSON/日志落盘）。

---

## 1. 论文解析 → 上传入库（omp harness，agent/chat API 驱动）

**论文名**：DeepSeek-R1 (arXiv 2501.12948)，PDF 5.0MB / 17 页 / 229,423 字符 / 57 图——**确认不在任何既有语料库**。

| 回合 | 任务 | 结果 |
|---|---|---|
| try1 | 全流程（查重→创建→MinerU 解析→质检→入库） | 601.9s **撞 600s 回合墙**；死前已完成查重、MinerU 解析（240,932 chars/57 图）、A2-Q 质检中 |
| try2 | 聚焦入库（解析已缓存） | 601.9s 撞墙；**Part 1/5 已入库（59,184B，自动索引已触发）** |
| try3 | 续传剩余卷 | **成功**：5/5 卷入库、552 chunks、每卷内容归纳描述（A3c）、双通道回查命中 |

**入库终态（独立复核）**：KB `演示-R1论文-20261112`（id 2f63d95f）；5 卷 = 59,184/54,927/57,451/50,511/25,798 B；
chunks 124/135/119/116/58 = **552**；57 图入 assets；60K 结构感知分卷边界正确（p1 止于 B.3、p2 起于 B.3.1）。
**回查双通道**：BM25 two-stage 命中 chunk16=`## 2.1 Group Relative Policy Optimization`（0.604）；
向量 top 0.741（独立复核 5 hits）。

**发现（如实披露）**：agent/chat 存在 **600s 单回合硬上限**（chat.post.ts 取 timeout_ms 但 omp 引擎回合 600s 截断），
5MB 论文"解析+全量入库"单回合放不下——**增量续传可用**（try2 的半成品被 try3 识别并续完，零重复写盘）。
这是 omp/claude 集成的真实使用边界，不是缺陷掩盖：两次超时都产出了持久化进展。

## 2. 检索增强回答（US-11，omp×claude 同题对照，单题一回合）

8/8 任务全部 completed（无超时）：

| 题 | 金标（PDF 原文） | omp 回答 | claude 回答 |
|---|---|---|---|
| Q1 AIME/MATH-500 成绩 | **79.8% / 97.3%** | ✅ 79.8/97.3，Table 8 OCR 列序走读 + Table 3 交叉印证 | ✅ 同答案，双独立表格互证 |
| Q2 RL 算法/为何不用神经奖励 | **GRPO + 规则奖励；neural reward models susceptible to reward hacking** | ✅ 三者全对 + PRM 段逐字 | ✅ 全对 + A.3 GRPO/PPO 对比 |
| Q3 R1-Zero 纯 RL？可读性 | **纯 RL（跳过 SFT）；poor readability + language mixing** | ✅ 且精确化"纯RL=跳过SFT而非从零训练" | ✅ 全对 |
| Q4-ood 电费（论文无此数） | 无电费数据；有 $294K 训练成本 | ✅ **拒绝编造电费**，如实呈现 $294K 训练成本并明确"训练成本≠电费账单" | ✅ 同样诚实边界处理 |

**质量评定：8/8 回答四维全对（正确性/溯源/逐字引用/零编造），0 幻觉**。两个 harness 风格差异：
omp 引用 OCR 原样表格并逐列走读（更工程化）；claude 引用排版后文本并做双表互证（更严谨感）。
耗时：omp 180-390s/题，claude 170-551s/题。

## 3. 知识库整理功能（US-12，MCP 工具直驱）— **14/14 PASS**

| 步骤 | 结果 |
|---|---|
| 标签更新 + kb_tags_list 读回 | PASS |
| 子库创建（演示-R1论文-20261112/安全与参考） | PASS |
| 文档移动 part 5 → 子库 | PASS（二次运行确认已移动；首跑成功） |
| 移动后子库向量可检索 + 父库递归检索仍命中 | PASS |
| KB 改名（kb_update）→ 检索仍命中（rename 卫生）→ 标签平台级标签表仍含演示库标签 → 改回 | PASS ×4 |
| kb_reindex 提交 → +5s 探针命中（异步不破坏检索） | PASS |
| 三源一致性（kb_list vs 磁盘目录 vs yml） | PASS |

## 4. 结论

1. **omp 与 claude code 双 harness 均已完整集成**：经同一 `/api/kb/agent/chat`，omp 完成解析+上传入库
   （含增量续传），claude 完成检索问答；两者检索质量同级（8/8 正确、零编造、逐字溯源）。
2. **解析入库功能满足要求**：MinerU 解析质量好（240K 字符/57 图）、60K 结构分卷边界正确、
   自动索引+显式索引双保险、双通道回查命中。
3. **检索功能满足要求**：8/8 事实题精确命中金标数字/概念并逐字溯源；OOD 题零编造且能
   "拒绝+补充相关事实"的诚实边界处理。
4. **整理功能满足要求**：14/14，整理操作全程不破坏检索（rename/reindex/move 后探针全命中）。
5. **使用边界**：单回合 600s 上限 → 大论文入库需增量续传（可用、已验证）。

## 5. 证据清单

- 入库三轮原始任务 JSON：`ingest_omp{,_try2,_try3}.json` + console 日志
- 8 条问答原文：`qa_omp_Q{1,2,3}.json`、`qa_claude_Q{1,2,3,4-ood}.json`、`qa_omp_Q4-ood.json`
- 整理测试：`organize_test.py` + `organize_test_results.json`（14 步逐条）
- 金标文本：`gold_text.txt`（PDF 全文 229,423 chars，用于 8 答案对照）
- 汇整索引：仓库根 `EXPERIMENT-RESULTS-MASTER.md`
- 清理归档：`review/archive-20261112-cleanup/`（MANIFEST v2 + tarball ×1；混沌期日志系 11-10 前轮已删，见 MANIFEST 更正披露）
