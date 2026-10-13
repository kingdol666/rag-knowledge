# 搜索需求摘要（_brief.md）

## PPT 主题
「检索端到端三通道 Benchmark 实测」——RAG Knowledge 平台 2026-10-12 最新实验结果的汇报演示

## 目标受众与场景
论文评审 / 技术评审 / 项目组内部；学术+工程混合受众；用于展示实验严谨性与结论可信度

## 页数
3 页（结果总览 → 数据对比 → 发现与定论）

## 语言
中文为主，保留关键英文术语（InstructDS / EHR / gold / baseline）

## 搜索维度（3-8 个）

### 维度 1：本地实验工件精读（最高优先，全部真实数据源）
从以下文件提取**图表可用的结构化数据**（表格/序列），写入 `ref-experiment-data.md`：
- `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\ppt_workspace\references\_user_materials.md`（已整理的主摘要）
- `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\REPORT.md`（完整报告）
- `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\run-20261012T062847Z-5f9faac\RETRIEVAL-COMPARE.md`
- `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\chatmodes-20261012T061102Z-5f9faac\CHAT-MODES-COMPARE.md`
要求：每个数据点附带来源文件路径；数字与文件逐字一致（可用 python 读 JSON 抽查 2-3 个关键数字核对）。

### 维度 2：RAG 系统评测的常见报告口径（背景锚点）
检索 1-3 条公开信息：RAG 评测（如 HotpotQA / BEIR / RAGAS）通常如何报告 latency / quality / cost / abstention（拒答）维度。写入 `ref-context.md`。要求：只写可验证来源（URL+标题），标注"背景参考"，**不得与本项目数字混写**。

### 维度 3：视觉与叙事参考（可选，轻量）
数据型学术 deck 的信息图叙事参考（如 Nature/Science 信息图的"图注+关键数字放大"惯例），1-2 条。写入 `ref-context.md` 同文件。
