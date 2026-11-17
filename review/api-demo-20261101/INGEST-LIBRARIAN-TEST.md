# 入库 + 逐级检索 Subagent 实测报告（2026-11-02）

> 测试目标：用 ingest skill 全流程入库一篇新论文 → 派 subagent 以 librarian 逐级检索提问 → 评估回答质量。
> 论文：《Lost in the Middle: How Language Models Use Long Contexts》（Liu et al., arXiv 2307.03172，747KB PDF）
> 目标库：`计算机与人工智能`（b1199132-e4d4-4305-8c2e-82dc1753b0ba，入库前 131 篇）

---

## 一、入库全流程（A0–A9）

| 阶段 | 执行 | 结果 |
|---|---|---|
| Pre-flight | `kb_project_status` | ✅ backend 8771 / web 6789 / MCP 全绿 |
| A0 去重 | `kb_search` + `kb_search_vector(0.85)` 双通道 | ✅ 无重复（通道1命中均为无关临床 LLM 论文） |
| A1 勘查 | `kb_list` 34 库 | ✅ 归入 `计算机与人工智能`（描述含 NLP/LLM，A3d ②匹配） |
| A2 解析 | `parse_doc` + 轮询 | ✅ 63,091 字符 / 24 图 / 2 次轮询即完成 |
| **A2-Q 质检门** | 头 1500 字符检查 | ✅ 真实标题、无乱码（0 replacement char）、无二进制残留、无空行爆炸 |
| **A2.5 分卷门** | `split_large_doc.py`（max_chars=30000） | ⚠️ 见下述缺陷①：脚本 `--agent-plan` 未实现 → 走 deterministic 结构兜底，产出 3 卷（28.2K/28.5K/7.1K，边界均在章节接缝） |
| A3 内容分析 | 读三卷正文 | ✅ 提取 title/domain/methods/scenario/key_findings |
| A5 入库 | `kb_doc_create` ×3 + 图片上传 | ✅ 3 卷落库，描述由我按各部分真实正文撰写（ICD 格式 + 【Part i/N · 范围】标签） |
| A3b 标签 | `kb_doc_update_tags` | ✅ 5 个内容锚定标签：long-context / language-model-evaluation / multi-document-qa / key-value-retrieval / serial-position-effect |
| A6 索引+图谱 | `kb_index_document` ×3 + `kb_graph_build(force)` + 轮询 | ✅ 69/72/18 chunks，collection=`kb_b1199132-…`（UUID 一致），graph 三卷均有节点 |
| **A3c-R 自检** | `kb_search`（描述问题维度措辞）+ `kb_search_vector`（改写问句），各 top_k=5 | ✅ 首轮关键词通道未召回（描述缺英文锚词）→ 按契约并入 `long context`/`middle`/`instruction fine-tuning` 等词后重测：**关键词通道 rank1-3、向量通道 rank2**，两通道命中 |
| A7 C1–C9 | 逐项核验 | ✅ C1 正文完整 / C2 五要素描述 / C3 5 标签 / C4 域一致 / C5 UUID+chunks / C6 图 24/24 / C7 三卷图谱 / C8 三层元数据（doc_count 131→134）/ C9 双通道自检 |
| A9 报告 | 本文件 | ✅ |

### 入库环节发现的 3 个真实问题（如实记录）

1. **`split_large_doc.py` 的 `--agent-plan` 未实现**：脚本把 plan 读入 `cfg["agent_plan"]` 后，`plan_split()` 从未消费它——Agent 规划的分卷边界被静默忽略，始终输出 deterministic 结构兜底。我提交的 3 卷 Agent 规划（题头-§2.3 / §3-附录E / 参考文献-附录G）与其实际产物（题头-§4.2 / §4.3-附录E / 附录F-G）不一致。**按 skill 纪律未冒充 Agent 分卷**，如实标注 planner=deterministic。
2. **`fs_upload_file` 污染文档目录**：skill 要求"分卷前先把解析图片上传到库"，但该工具把 24 张 hash 名 `.jpg` 直接存到 KB 根目录 → `doc_count` 131→158、出现在 `(flat)` 分组、可被 `kb_search` 检索命中（实测 jpg 文件名可被搜出）。**这会让图书管理员的书架多出 24 条垃圾条目**。我清理了 24 条（原图保留在 parse 输出目录），库恢复 134 篇。建议 skill 明确"图片应进 `images/` 子目录且不计入文档目录"。
3. **判卷 refs 的 Windows 路径转义陷阱**：subagent 用反斜杠路径构造 JSON → 4 次 `Invalid \escape` 失败。我复测确认引擎健康（`real_engine=True`、survivors 命中、pack 28.9KB），**失败纯属 Agent 侧转义**。建议：统一正斜杠（已实测可行），或按 librarian skill 的 `@file` 传递。

## 二、Subagent 逐级检索执行

| 指标 | 实测 |
|---|---|
| 车道 | librarian（L0 目录 → L0.5 子库检查 → L1 groups 书架图 → L1b 定向翻页 → L3 判卷 → L4 读原文） |
| 定位 | (flat) 分组恰好 3 篇 = 目标三卷，一次翻页全命中 |
| MCP 调用 | 18 次（契约上限 14 → **超 4 次**：4 次判卷转义失败 + 2 次 offset 误用） |
| 判卷 | 0 次成功（全为 Agent 侧转义失败）→ 三个答案全部改用 `kb_doc_read` 直读原文取证（skill 允许的降级） |
| 读原文 | part 1 读到 §4.1 开头、part 2 读到 §5 前，part 3 未读 |

## 三、回答质量评估（对照原文逐字核验）

### 3.1 事实准确性：**14/14 全部命中，零编造**

我用脚本把 subagent 的每条引用回贴原文核验：

| 引用 | 原文位置 | 核验 |
|---|---|---|
| "performance is often highest when relevant information occurs at the beginning or end … significantly degrades … in the middle" | part 1（Abstract） | ✅ 逐字 |
| "primacy bias" / "recency bias" | part 1/2 | ✅ |
| "closed-book setting; 56.1%" | part 1 | ✅ |
| "extended-context models are not necessarily better at using their input context" | part 1 | ✅ |
| "model architecture (decoder-only vs. encoderdecoder), query-aware contextualization, and instruction fine-tuning" | part 1 | ✅ |
| "The task specification and/or instruction is commonly placed at the beginning of the input context" | part 2 | ✅ |
| "MPT-30B and MPT-30B-Instruct exhibit a U-shaped performance curve" | part 2 | ✅ |
| "instruction fine-tuning process itself is not necessarily responsible" | part 2 | ✅ |
| "biased towards recent tokens" | part 2 | ✅ |
| "prompting language models with longer input contexts is a trade-off" | part 1/2 | ✅ |
| "reader model performance saturates long before retriever performance saturates" | part 2 | ✅ |
| "Using more than 20 retrieved documents only marginally improves … ~1.5% … ~1%" | part 2 | ✅ |
| "effective reranking of retrieved documents" | part 2 | ✅ |
| 定量推断"最好/最差差距从近 10% 缩小到约 4%" | part 2："reduces the worst-case performance disparity from nearly 10% … to around 4%" | ✅ |

### 3.2 溯源性：**满分**
三题答案均带 `doc_path` + 逐字英文引文 + 中文解释；无一句脱离原文。

### 3.3 完整性：**Q1/Q3 完整，Q2 部分**
- **Q1（核心发现）**：完整——U 形曲线、primacy/recency bias、中部低于闭卷（56.1%）、长上下文模型未必更会使用上下文。
- **Q2（位置不稳健的原因）**：**不完整**——只答出"指令微调被排除 + recency bias 来自预训练"，**遗漏 §4.1 架构对比（decoder-only vs encoder-decoder）与 §4.2 query-aware contextualization 的具体结论**（它自己也如实列为盲区）。这两节恰是论文归因的核心。
- **Q3（更多上下文是否更好）**：完整——trade-off、reader 早饱和、>20 篇仅 ~1.5%/1% 边际、重排/截断建议。

### 3.4 过程合规与诚实性
- 超预算 4 次调用（自身转义+offset 误用）
- 判卷 0 次成功 → 降级直读，未假装有判卷证据
- **盲区披露质量极高**：明确列出未扫描分组、未读章节、判卷失败原因、编码问题，并声明"§4.1/§4.2 未读到，不做推断"

## 四、总结评价

| 维度 | 评级 | 说明 |
|---|---|---|
| 检索定位 | A | 逐级导航一次定位到目标 3 卷（(flat) 分组），无全库扫读 |
| 事实准确性 | **A+** | 14/14 引用逐字命中，零幻觉，含数字 |
| 溯源性 | **A+** | 每条结论可回贴原文 |
| 完整性 | B | Q2 漏掉论文最核心的两条归因（架构、query-aware contextualization） |
| 过程效率 | C+ | 判卷 4 次失败（转义）+ 2 次 offset 误用，超预算 4 次 |
| 诚实性 | A+ | 盲区披露详尽，未编造 |

**结论**：入库链路完整可用（C1–C9 全绿），**子 agent 的回答在"准确与可溯源"上达到满分级**（这是可信检索最关键的维度），但在"完整性"上受限于自身判卷转义失败导致的降级直读与阅读深度不足。**若判卷调用正常（正向斜杠路径），L3 证据门会给出幸存卷与行级定位，Q2 的缺口可自动收敛**。

## 五、可执行改进（2026-11-02 更新：①③已修复并验收，②待办）

1. **skill/工具侧**：① `split_large_doc.py` 实现或删除 `--agent-plan`（当前静默忽略，违反契约）【待办】；② `fs_upload_file` 增加图片目录语义或不计入文档目录【待办，本轮已人工清理】；③ ~~skill 明示判卷 refs 用正斜杠路径~~ **✅ 已根治（2026-11-02）：`kb_laya_judge` 的 `documents` 改为兼容 list/str 双形式 + 服务端反斜杠路径归一化 + `bad_request` 错误分类（`error_kind` 字段），验收 6/6 PASS（`scripts/s9_judge_fix_acceptance.py`：A list/B str+反斜杠/C 非法转义分类/D 正斜杠回归/E1-E2 行语义回归）**；`kb_doc_read` docstring 已补 offset=行号/limit=行数语义。
2. **Agent 执行侧**：① ~~判卷 payload 统一正斜杠~~（服务端已兼容反斜杠）；② `kb_doc_read` 的 offset 是**行号**不是字符偏移（已文档化）；③ 判卷失败后按 skill 只重试一次（不变）。
3. **流程侧**：Q2 类"多原因"问题应显式驱动二轮（读完 §4.1/§4.2），或在第一次判卷成功后按 pack 中的幸存段落继续读。

---
工件：`review/api-demo-20261101/artifacts/`（parse_lostmiddle.json / split_scan.json / split_result.json / lostmiddle_plan.json / lostmiddle_ingest.json）；原文三卷：`backend/output/40bcd8c6eba7/`。
