# 测评计划（TEST-PLAN）— rag-knowledge 三模块基准

> 本套件自包含：测试文档资料（`data/`）+ 脚本（`scripts/`）+ 本计划。
> 任何人（或任何 Agent）按下面步骤执行，即可从零复现全部 benchmark 数值。
> 设计目标：**快**（全程约 30-40 分钟，其中约 25 分钟为自动化运行）、**完整**（覆盖
> 文档解析入库 / 基于内容检索 / 经验总结三大功能）、**可复现**（确定性管线双轮逐位一致）。

## 0. 前置条件（一次性，约 5 分钟）

```bash
# 仓库根目录
cd <repo-root>
# 后端 :8771 与前端 :6790 已启动（可用 ragctl start / start.bat）
curl -s http://localhost:8771/health          # 期望 {"status":"healthy"}
# 鉴权 token 在 .env 的 MCP_AUTH_TOKEN；环境变量可省略（脚本自动读取）
# 依赖：Python 3.11+（标准库）、uv（拉起 kb-mcp）、omp（仅模块 C 的冥想与评价 Agent）
# matplotlib（仅 data/make_pdf.py 生成 PDF 需要；仓库 data/ 内已附带生成好的 PDF）
```

环境变量（脚本也可自动从 .env 读取）：

```bash
export RAG_BENCH_TOKEN=$(grep MCP_AUTH_TOKEN .env | cut -d= -f2)
export RAG_BENCH_URL=http://localhost:8771
export RAG_BENCH_WEB_URL=http://localhost:6790
```

## 1. Step 0 · 清空知识库（约 2 分钟）

```bash
python scripts/00_reset_env.py
```

删除系统中**全部**知识库（级联清理向量与图谱数据），输出剩余 KB 数量应为 0。
这是复现的起点：保证从同一空白状态开始。

## 2. Step 1 · 模块 A：文档解析与入库（约 6 分钟）

```bash
python data/make_pdf.py                # 生成演示 PDF（已附带，可跳过）
python scripts/01_ingestion.py 1       # 第一轮
python scripts/01_ingestion.py 2       # 第二轮（复现校验）
```

做了什么：创建 KB-Demo-EN/ZH/JA 三个库 → 15 篇 md（en 5 / zh 4 / ja 4，外加
wind-energy.md 供检索）走生产入库 API → 1 个 PDF 经 **MCP parse_doc（MinerU 真解析）**
转 markdown 后回写 KB → force 重索引。
产出：`results/module_a_ingestion_r{1,2}.json`（解析成功率 / 入库成功率 / 指定库归属
正确率 / 存储完整率 / 自检索 Hit@1，内嵌环境指纹）。
**预期**：所有指标 ≥ 0.95；双轮数值逐位一致。

## 3. Step 2 · 模块 B：基于内容的检索 vs 向量 baseline（约 10 分钟）

```bash
python scripts/02_retrieval.py 1
python scripts/02_retrieval.py 2       # 复现校验
```

做了什么：19 个查询（en 8 / zh 5 / ja 4 / 跨库 3，含金标页与答案，见
`data/queries.jsonl`），全部经 **kb-mcp MCP stdio 真链路**（与 Agent 同款工具层）：

- **内容检索**（QDCVR 规程确定性展开）：`kb_list` → `kb_search_two_stage`
  （两阶段召回，全局+balance）→ Step2.5 硬阈值 0.35+去重 → `kb_doc_read`×3
  **内容验证**并按验证得分重排（content-overrides-vector）
- **向量 baseline**：`kb_search_vector` top-10（Chroma + BAAI/bge-m3）

指标：**命中率 Hit@1/3/5**（金标进 top-k）· **召回率 Recall@3/5**（金标覆盖率）·
**准确率 Precision@5**（top-5 相关占比）· MRR · 逐级命中分布（stage1/2/3）· 时延。
产出：`results/module_b_retrieval_r{1,2}.json`。
**预期**：内容检索整体 Hit@3 / Recall@5 / MRR 高于向量 baseline；双轮逐位一致
（延迟除外）。首轮运行会触发 BM25 全量重建（脚本内置预热等待，属正常现象）。

## 4. Step 3 · 模块 C：冥想经验自动总结（约 15 分钟）

```bash
python scripts/03_experience.py 1
python scripts/03_experience.py 2
```

做了什么：对 KB-Demo-EN / KB-Demo-ZH 触发真实冥想（`POST /meditation/run`，
harness=omp Agent 从库内文档综合信号并撰写经验）→ 读取经验区 → **创建子 Agent**
（omp 一次性运行）按 0-10 rubric 逐条评价：有据性 4 分（内容是否源自库内事实、
无幻觉）+ 结构 3 分 + 可复用性 3 分。
产出：`results/module_c_experience_r{1,2}.json`（运行成功率 / 经验产出 /
子 Agent 评分均值 / 有据比例；评价原文存 `results/judge-*.txt` 可审计）。
**预期**：两库均有经验产出；子 Agent 评分均值 ≥ 6/10；有据比例 ≥ 0.5。

## 5. 标准语料赛道 · XQuAD（可选，约 8 分钟）

在自建赛道之外，从**标准跨语言问答基准 XQuAD**（google-deepmind/xquad，CC BY-SA）
确定性抽取 en/zh 各 8 篇文章 + 32 个标准问题，走完全相同的流程：

```bash
python scripts/10_standard_fetch.py          # 下载 XQuAD 子集(冻结, 可跳过)
python scripts/10_standard_ingest.py 1       # 入库 KB-Std-EN/ZH + force 重索引
python scripts/02_retrieval.py 1 data/standard/queries-std.jsonl   # 检索对比
python scripts/03_experience.py 1 KB-Std-EN  # 冥想(单库)
```

产出：`results/module_a_std_r1.json`、`module_b_retrieval_std_r1.json`、
`module_c_experience_std_r1.json`；报告含「标准语料赛道」专属图表。

## 6. Step 4 · 生成报告

```bash
python scripts/04_report.py
# → results/benchmark-report.html（Chart.js 单文件，双击即看）
```

报告含：模块 A/B/C 各自得分图、**内容检索 vs 向量 baseline 对比图**、逐级命中率图、
时延对比（两阶段=工程加速项）、标准语料赛道图、每张图下方的解释文字（可直接改写进论文 experiments）。

## 7. 复现容忍度与判读

| 通道 | 容忍度 |
|---|---|
| 模块 A 全部、模块 B 检索指标 | **逐位一致**（延迟字段除外）——无随机数、语料与参数冻结 |
| 模块 C 冥想（LLM 生成） | 同一模型版本下经验**条目数与主题一致**；子 Agent 评分 ±1.5 |
| 判读 | 报告徽章 r1==r2 为 PASS 即复现成立 |

## 8. 语料与版本指纹

- 16 篇文档均为本套件自撰（`data/`），事实数字可核对；不依赖外部数据集版本。
- 查询集 `data/queries.jsonl` 冻结（qid、金标页、答案）。
- 每个结果 JSON 内嵌 `env`：嵌入模型（BAAI/bge-m3）、向量库（ChromaDB）、
  关键词索引（jieba BM25）、检索参数（vector k=10；stage1=40/stage2=10；阈值 0.35）。
- 系统版本：仓库分支 feat/soul-persona-system；kb-mcp 通过 `uv run` 按仓库锁定环境启动。
