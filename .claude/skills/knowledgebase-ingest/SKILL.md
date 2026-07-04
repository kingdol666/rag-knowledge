---
name: knowledgebase-ingest
description: >
  Document ingestion pipeline for knowledge bases. Complete A1→A9 workflow:
  survey collection, classify each document by domain, find or create the
  correct KB, select tags from vocabulary, execute storage (parse-path or
  direct), assign tags, verify, and **auto-create sub-KBs when a parent KB
  grows too large** for effective retrieval. Invoked by Archival when
  documents need to be stored.
---

# Knowledge Ingest — Document Ingestion Pipeline

Invoked by Archival when the scenario is diagnosed as **Ingest**.
Follow these steps EXACTLY. Do not skip any step.

---

## ⚠️ Core Architecture: Hierarchical KB for Precision Retrieval

**Your knowledge base is not flat.** When a KB accumulates many documents, 
retrieval precision degrades because description scanning (Step 1-2 of Search)
must distinguish too many items. The solution is **auto-creation of sub-KBs**.

```
Before (flat KB, 12 docs, retrieval accuracy degrades):
Thermal-Power-Monitoring/
├── doc1 (coal mill prediction)
├── doc2 (fan vibration)
├── doc3 (boiler efficiency)
├── doc4 (wind turbine)
├── doc5 (coal mill 2)
├── doc6 (boiler tube leak)
├── doc7 (generator exciter)
├── doc8 (condenser cleaning)
├── doc9 (pulverizer maintenance)
├── doc10 (scrubber optimization)
├── doc11 (steam turbine)
└── doc12 (transformer oil)

After (hierarchical KBs, precise description-driven retrieval):
Thermal-Power-Monitoring/
├── (no docs at root — they're all in sub-KBs)
├── Coal-Mill-Fault-Prediction/
│   ├── doc1 (coal mill CNN-LSTM)
│   └── doc5 (coal mill MSET)
├── Boiler-Diagnostics/
│   ├── doc3 (boiler efficiency optimization)
│   └── doc6 (boiler tube leak detection)
├── Steam-Turbine-Monitoring/
│   ├── doc7 (generator exciter fault)
│   └── doc11 (steam turbine vibration)
├── Fan-And-Pump-Diagnostics/
│   └── doc2 (primary fan vibration analysis)
└── Auxiliary-Equipment/
    ├── doc8 (condenser cleaning robot)
    ├── doc9 (pulverizer maintenance)
    ├── doc10 (scrubber optimization)
    └── doc12 (transformer oil DGA)
```

**Why this matters**: When Search's Step 1 scans `kb_catalog()`, the Agent reads
*6 focused descriptions* ("Coal-Mill-Fault-Prediction: CNN-LSTM/MSET methods for
coal mill early warning → matches 'mill fault' query") instead of *1 vague
description* ("Thermal-Power-Monitoring: energy industry documents"). The sub-KB
descriptions carry **machine-level precision** that vector search alone cannot match.

This is the core of your **Judgment-First Retrieval**: the KB hierarchy is
designed so that AGENT reading descriptions can pinpoint the right sub-domain
without needing vector search at all for most queries.

---

## A0 — Duplicate Pre-Check

Before surveying, check if this document already exists:

```
kb_search(query="<filename without extension>", top_k=5)
```

### ⚠️ A0-key — 关键工具调用约定（避免 400 错误）

**`kb_doc_read` 的 doc_path 参数规则（实测确认）：**
- 当提供 `kb_id` 时，`doc_path` 必须是 **bare filename**（如 `01-paper.md`），
  **不能带路径前缀**（如 `KB-Name/01-paper.md` 会报 400 "path is required"）
- 当不提供 `kb_id` 时，用 `path` 参数传完整相对路径

```python
# ✅ 正确（kb_id + bare filename）
kb_doc_read(kb_id="uuid", doc_path="01-paper.md", max_chars=800)

# ❌ 错误（带路径前缀 + kb_id → 400）
kb_doc_read(kb_id="uuid", doc_path="KB-Name/01-paper.md")
```

**`kb_doc_update_meta` / `kb_doc_update_tags` / `kb_doc_delete` / `kb_doc_move` 同理**：
提供 `kb_id` 时，`doc_path` 用 bare filename（即 `doc.name`，不是 `doc.path`）。

**其他工具签名：**
- `parse_doc(file_path, kb_id, description="", tags=[], use_ocr=true)` — 非阻塞，返回 task_id
- `kb_doc_create(kb_id, name, content, description="")` — content 是完整 markdown 文本
- `kb_create(name, description="", parent_id="")` — parent_id 用于子KB
- `kb_update(kb_id, name?, description?)` — kb_id 接受 UUID 或 path
- `parse_task_status(task_id)` — 轮询解析状态，返回 markdown_chars/image_count

**For each result:**
- Compare name (case-insensitive) with incoming doc name
- If name matches AND file_size/lines are similar → **likely duplicate**
- If name differs but content same topic → **possible related doc to note**

**Decision:**
- Duplicate found → "This document appears to already exist in [KB-Name]. Skip or re-parse?"
- No duplicate → Proceed to A1

### A0b — Content-Hash Dedup (enhanced)

For suspicious duplicates (same size, similar topic but different name):

1. Read first 500 chars of incoming document.
2. Compare against first 500 chars of existing doc matched: `kb_doc_read(kb_id, doc_path, max_chars=500)`
3. Compute word-count + first-sentence similarity.
4. If content same → "Content matches '[existing-doc]' in [KB-Name]. Skipping."

## A1 — Survey First

```
kb_list()          → load all KBs (including hierarchy — note parent-child relationships)
kb_tags_list()     → load the vocabulary
fs_get_tree(include_files=False, max_depth=3) → understand full KB tree hierarchy
```

**You MUST understand the KB hierarchy before deciding where anything goes.**
A sub-KB exists for a reason — don't put coal mill documents in the parent
Thermal-Power-Monitoring KB when Coal-Mill-Fault-Prediction already exists as a sub-KB.

## A2 — Classify Each Document

For each item, determine its domain AND sub-domain:

| Domain Level | How to determine | Used for |
|---|---|---|
| **Parent domain** | Broad field: Energy/Power, AI/ML, Healthcare, Legal, etc. | Top-level KB selection |
| **Sub-domain** | Specific technology/equipment: coal-mill, steam-turbine, boiler, transformer-oil, CNN-LSTM, wind-turbine | Sub-KB creation or matching |
| **Task scenario** | What problem does it solve? early-warning, fault-diagnosis, efficiency-optimization, predictive-maintenance | Description's scenario field |

**Classification signals:**

| Domain | Parent signals | Sub-domain signals |
|--------|---------------|-------------------|
| **Energy/Power** | turbine, thermal, boiler, generator, 火电, 发电, power-plant | coal-mill, steam-turbine, wind-turbine, gas-turbine, boiler, condenser, transformer, fan, pump, combustion |
| **AI/ML** | deep learning, neural network, NLP, LLM, RAG | computer-vision, NLP, recommendation, reinforcement-learning, time-series-forecasting |
| **Healthcare** | clinical, diagnosis, patient, pharmaceutical, medical-imaging | radiology, cardiology, oncology, pathology, genomics |
| **Engineering** | mechanical, electrical, manufacturing, 故障诊断, Industry 4.0 | gearbox, bearing, rotating-machinery, structural, hydraulic, pneumatic |
| **CS/Software** | algorithm, code, API, architecture, .py | database, networking, security, frontend, compilers, OS |

**Rule**: If multiple sub-domains match, pick the most SPECIFIC application.

## A3 — Find or Create the Right KB (Hierarchical)

For each document's domain + sub-domain, scan `kb_list()`:

| Match level | Criteria | Action |
|---|---|---|
| **Exact sub-KB** | A sub-KB description contains the document's sub-domain | Use it |
| **Parent + sub** | Parent KB matches domain but NO sub-KB for sub-domain exists | **Create sub-KB** (`kb_create` with `parent_id=parent_kb_id`) |
| **Parent only** | Parent KB matches domain, document is the first in that sub-category | Create sub-KB under parent |
| **None** | No matching parent KB at all | Create top-level KB (no parent_id) |
| **User-specified** | User said "put it in X" | Respect, but note mismatch |

### Sub-KB Creation Decision Algorithm

```
IF kb_get_documents(parent_kb_id).count >= 8 AND documents span ≥2 distinct sub-domains:
    → Evaluate: can these docs be grouped into focused sub-KBs?
    → YES → create sub-KBs, move docs
    → NO → keep flat for now (not enough differentiation)

ELSE IF incoming document is clear sub-domain AND parent has ≤3 docs:
    → Keep in parent for now. Evaluate at next organize cycle.

ELSE IF incoming document is the FIRST in a clear sub-domain:
    → Keep in parent. Flag for re-evaluation at 8-doc threshold.
```

**Threshold**: When a KB's document count reaches **8-12** AND documents
span multiple sub-domains, auto-create sub-KBs during ingest.

## A4 — Write the Description（场景可定位，核心基石）

> **核心原则**：description 必须基于**真实读取的内容**来写，而不是文件名、来源或猜测。
> 如果不读文档内容就写 description，等于是盲写——可能把 RAG for AIGC 写成 Corrective RAG，
> 把 Generative Agents 写成 MetaGPT。**必须读内容，然后基于内容摘要生成。**
>
> Agentic优先检索的基石是：Agent **只读 description 就能判断**这篇文档/KB
> 适用于什么场景——这要求 description 必须来源于真实内容摘要。

### A4-0 — 黄金法则：先读内容，再写描述

**所有入库文档（包括 KB 级别的 description），在写入之前必须先读取真实内容：**

```
# Parse-path 文档（先解析，再读内容，再写描述）
parse_doc(...) → 等待完成 → 读取 markdown 前 3000 字符 → 生成 description

# Direct-path 文档（内容已可用）
kb_doc_read(kb_id, doc_path, max_chars=3000, offset=0) 或
head -c 3000 <file_path>
→ AI 分析内容 → 生成 description
```

**禁止的行为：**
- ❌ 不读内容，仅根据文件名写 description（文件名可能是错的！）
- ❌ 不读内容，仅根据 sourcePdf 来源写 "Parsed from XXX.pdf"
- ❌ 不读内容，直接复制论文摘要（可能和实际入库内容不对应）
- ❌ 不读内容，凭记忆或训练数据写 description（过时或不对应）

### A4-1 — 子Agent内容摘要流程 ⭐

> 当入库文档很多时，逐个读内容会严重占用主上下文。此流程通过
> **委托子Agent**完成内容提取和 description 生成，主Agent只做分发和验证。

**何时使用子Agent：**
- 单次入库 ≥ 3 篇文档
- 单篇文档 > 50KB（含解析后）
- 文档内容语言主Agent不擅长（如中文古文、德文、专业符号）

**子Agent调用方式：**

```
Agent(
  subagent_type="general-purpose",
  prompt="""读这个文档的前 2000 字符内容，然后输出结构化的内容摘要。

文档路径: {file_path} (或 markdown_path)
源文件名: {filename}

输出格式（纯 JSON，不要 markdown 代码块包裹）：
{
  "title": "文档的真实标题（从前2000字符中提取）",
  "content_preview": "前100字真实内容摘要",
  "domain": "检测到的领域",
  "methods": ["方法1", "方法2"],
  "scenario": "适用场景描述（1-2句话）",
  "key_results": "关键结论或数据（如果有）",
  "language": "中文/英文/中英",
  "suggested_tags": ["标签1", "标签2", "标签3"],
  "suggested_description": "基于内容的完整 description（A4格式）"
}"""
)
```

**对子Agent输出验证：**
- description 中是否包含具体的方法名/设备名？→ 没有则退回
- content_preview 是否与真实内容一致？→ 明显不一致则退回
- 提取的 title 是否和文件名暗示的一致？→ 不一致则标注"⚠️ 文件命名可能错误"

### A4a — 文档级别 description 模板

```
[研究对象] + [方法/技术] + [解决什么问题/适用场景] + [关键结论/数据] + [语言]
```

**要素逐项展开：**
1. **研究对象**：什么设备/系统/领域（磨煤机/蒸汽轮机/CNN-LSTM/知识图谱）
2. **方法**：用什么方法（CNN-LSTM/MSET/互信息量/贝叶斯网络）
3. **场景**：解决什么问题（堵煤预警/早期故障排查/性能衰减趋势预测）
4. **数据亮点**：关键结果（提前315分钟预警/准确率96.7%/660MW实测）
5. **语言**：中文/英文/中英

**好例子：**
- ✅ "基于CNN-LSTM的火电厂中速磨煤机堵煤故障预警方法。利用DCS历史数据训练多输入单步预测模型，通过真实残差分析实现渐变故障早期识别。660MW机组实测，提前315min预警无误报。适用于磨煤机渐变故障早期预警、偏离度阈值核定。中文。"
- ✅ "风电齿轮箱（增速箱）故障诊断实践总结。涵盖齿面点蚀/磨损、轴承内外圈/保持架/滚动体6类故障的特征频率计算与振动/油液/温度三参量交叉验证方法。适用于齿轮箱早期故障排查、状态监测系统参数标定。中文。"

**坏例子（场景模糊，不可定位）：**
- ❌ "一篇关于磨煤机的论文"（无方法、无场景、无亮点）
- ❌ "AI-based warning system"（无设备、无具体场景）  
- ❌ "test" / "文档" / "资料"（完全无信息）
- ❌ "Parsed from XXX.pdf"（无内容信息，Agent无法判断相关性）

### A4b — KB 级别 description 模板（分层）

**父级KB**（覆盖面广，让Agent判断大类）：
```
[行业/领域] + [覆盖的子领域列表] + [方法总括] + [内容类型] + [语言]
```
- ✅ "Energy industry research repository covering thermal power plant auxiliary equipment diagnostics: coal mill fault prediction (CNN-LSTM/MSET), boiler tube leak detection, steam turbine vibration analysis, fan-and-pump condition monitoring. Methods include deep learning, signal processing, and statistical modeling. English and Chinese academic papers. For power plant equipment health management and intelligent early warning scenarios."

**子KB**（聚焦精准，让Agent精确匹配）：
```
[特定设备/子领域] + [核心技术方法] + [适用场景] + [文档数量] + [语言]
```
- ✅ "Coal mill (pulverizer) fault prediction and early warning research. Covers CNN-LSTM, MSET, BP-SVR methods for coal choking, coal blockage, and grinding roller wear detection. Real 660MW power plant data verified. For coal mill condition monitoring, early warning system configuration, and residual threshold tuning scenarios. 5 documents. Chinese."
- ✅ "Steam turbine and generator condition monitoring. Covers vibration analysis, exciter fault detection, and coupling misalignment diagnosis. For turbine-generator unit predictive maintenance and vibration trend analysis scenarios. 3 documents. English."

### A4c — 自检（写完必做）

问自己：**"如果未来有人遇到[我描述的场景]，他只读这一句description，能100%确定这篇文档就是他要找的吗？"**
答案必须是"能"。否则重写。

**不同抽象层的自检重点：**
- 父KB description → 帮助Agent决定"是否进入这个大类"
- 子KB description → 帮助Agent决定"这就是我需要的精确匹配"
- 文档 description → 辅助验证精确片段

### A4d — 读内容验证（必做）

在 description 写入 KB 后，执行最后的验证：

```
# 1. 对比 description 断言与真实内容
kb_doc_read(kb_id, doc_path, max_chars=500)
# 2. 检查 description 中的关键断言是否在真实内容中出现
#    - 如果 description 说"CNN-LSTM方法"→ 内容中应有 CNN、LSTM
#    - 如果 description 说"提前315min预警"→ 内容中应有 315
# 3. 如果断言无法在内容中找到 → description 可能靠猜测生成 → 退回重写
```

**自动检测规则：**
```
if "CNN-LSTM" in description and "CNN-LSTM" NOT in content_first_500:
    ⚠️ "Description mentions CNN-LSTM but content doesn't. Revise."

if "accuracy 94.5%" in description and "94.5" NOT in content_first_500:
    ⚠️ "Description claims 94.5% accuracy but not found in content. Verify."
```

## A5 — Choose Tags

1. `kb_tags_list()` was loaded in A1. Use it.
2. Pick 2-5 tags per document from existing vocabulary (>90% reuse).
3. Only create new tags (`kb_tag_create("tag")`) if the concept is totally absent.
4. Tag quality: lowercase, 1-3 words, domain-specific. Same tag convention applies to sub-KBs.

## A5b — Smart Size Check & Intelligent Document Splitting ⭐

> **核心原则**：大文档必须拆分才能被检索和阅读。一个文档超过2000行或50KB时，Agent的
> `kb_doc_read` 无法一次加载全部内容，向量搜索也会因为chunk太泛而精度下降。
> **拆分不是分块（chunking），而是分章（sectioning）**——按文档的逻辑结构拆成
> 多个独立文档，每章有自己的description、标签、向量索引。
>
> ⚠️ 大文档拆分必须在 parse 完成之后执行（对于 Parse-path 文件）。
> 在 parse_task_status 返回 "done" 之前，你无法读取内容进行拆分。

### A5b-0 — 大小检测

**自动检测阈值（任一超过即触发拆分）：**

| 指标 | 阈值 | 触发条件 |
|------|------|---------|
| **文件大小** | `file_size` > 50KB | 总是检查 |
| **行数估算** | > 2000行 | 总是检查（`wc -l` 或 content.count('\\n')） |
| **字符数** | > 80,000 char | 总是检查（超过这个值 `kb_doc_read` 无法一次读完） |

**检测时机（Parse-path）：**
```
1. parse_task_status(task_id) 返回 "done"
2. 检查 result 中的 markdown_chars:
   - markdown_chars > 80000 → 必拆分
   - markdown_chars > 50000 → 建议拆分，检查节标题数
3. 文件系统中读取实际行数
```

### A5b-1 — 预读大纲（Table of Contents Scan）

在拆分之前，**必须先读文档结构**，而不是盲拆。

**Step 1: 提取章节标题 + 行号（关键！）**
```
# 文档已入库，读取 web/storage 中的副本
DOC_PATH="web/storage/tree-file-system/{KB_NAME}/{doc_name}"

# 用 grep -n 提取所有标题及其行号
grep -n "^# \|^## " "$DOC_PATH"
# 输出示例：
# 1:## ABSTRACT
# 3:# Simulation of Micro-Void Development...
# 598:## CHAPTER ONE
# 654:## CHAPTER TWO
# 883:## CHAPTER THREE
# ...
```

**Step 2: 分析章节结构**
```
# 统计各章节的行数跨度
# Chapter 1: line 598-653  (56 lines)
# Chapter 2: line 654-882  (229 lines)
# Chapter 3: line 883-1142 (260 lines)
# ...

# AI 分析输出：
文档结构分析：
- 总行数: {N}  (wc -l < "$DOC_PATH")
- 总字符数: {N}
- 一级/二级标题数: {count}
- 主要章节: [章节列表 with 行号范围]
- 推荐拆分点: [章节边界行号]
- 每节估算大小: [节1: ~N行, 节2: ~N行, ...]
```

**⚠️ 关键规则**：章节边界用**行号**，不用字符数。后续内容提取用 `sed -n 'start,end p'`。

### A5b-2 — 确定拆分方案

**拆分决策矩阵：**

| 文档结构特征 | 推荐拆分策略 | 每块大小目标 |
|-------------|-------------|-------------|
| 有 `#` 或 `##` 章节标题 | 按章节拆分，一章一个文档 | 1000-2000行 |
| 有 `###` 小节但无大节 | 按 `##` 节拆分，`###` 自然归属 | 800-1500行 |
| 纯段落无标题（小说/报告） | 每 ~800 行找一个句子边界拆分 | 500-1000行 |
| 论文（Abstract→Intro→Method→Result→Conclusion） | 按标准论文结构分 4-6 段 | 每段500-1500行 |
| 教科书/手册（多级嵌套） | 按 `#` 一级章节拆分，保留 `##` 归属 | 每章 < 2000行 |

**分块命名规则：**
```
{原文件名}_s{N}_{简短节标题}.md
# 例如：
# 03-Micro-Void-AM-2025_s01_Introduction.md
# 03-Micro-Void-AM-2025_s02_Methodology.md
# 03-Micro-Void-AM-2025_s03_Results.md
# 03-Micro-Void-AM-2025_s04_Conclusion.md
```

### A5b-3 — 逐段读取 + 智能摘要生成

**这是核心步骤 —— 对每一段进行独立的内容验证和描述生成。**

对每个拆分段 index=1..M，已知该段行号范围 [start_line, end_line]：

```
Step 1: 从入库后的文档中提取该段内容（用 sed 按行号精确提取）
  DOC_PATH="web/storage/tree-file-system/{KB_NAME}/{doc_name}"

  # 提取该章节的完整内容
  SECTION_CONTENT=$(sed -n '${start_line},${end_line}p' "$DOC_PATH")

  # 验证提取成功
  echo "$SECTION_CONTENT" | wc -l   # 应该 ≈ end_line - start_line

  # ⚠️ 备选方案：如果 sed 不可用，用 kb_doc_read 的 offset/limit 分页读取
  # kb_doc_read(kb_id, doc_path, offset=start_line/10, limit=(end_line-start_line)/10)
  # 但 offset/limit 是按 chunk 不是按行，所以 sed 更精确

Step 2: AI 分析该节内容，生成结构化元数据
  # 可以委托子 Agent 分析 SECTION_CONTENT，避免主上下文膨胀：
  Agent(
    subagent_type="general-purpose",
    prompt="""分析以下文档章节内容，输出 JSON：

    章节标题: {从内容第一行提取}
    文档主标题: {从文档顶部提取}

    内容（{end_line-start_line}行）:
    {SECTION_CONTENT的前2000字符}

    输出 JSON:
    {
      "section_title": "本章节标题",
      "content_summary": "1-2句核心内容摘要",
      "methods": ["方法1", "方法2"],
      "scenario": "本节回答什么问题/解决什么场景",
      "key_data": "关键数据/结论（如有）",
      "section_tags": ["该节特有标签1", "标签2"],
      "section_description": "完整的 A4 格式 description"
    }"""
  )

Step 3: 写入 description（A4 规范）：
  "{文档主标题} — {章节标题}。{1-2句核心内容摘要}。
   适用于{场景描述}。{语言}。"

Step 4: 生成该段的独立标签：
  - 继承原文档的通用标签
  - 加上该章节特有的领域标签（来自子 Agent 的 section_tags）
  - 确保每段 3-6 个标签
```

### A5b-4 — 分块创建文档

对每个拆分段，使用 `kb_doc_create` 创建独立文档：

```
# SECTION_CONTENT 已在 A5b-3 Step1 通过 sed 提取
# SECTION_DESCRIPTION 已在 A5b-3 Step3 生成

kb_doc_create(
  kb_id=same_kb_id,
  name="{原文件名}_s{index}_{节英文slug}.md",
  content=SECTION_CONTENT,                    # ← sed 提取的章节文本
  description=SECTION_DESCRIPTION             # ← A4 格式的真实描述
)
```

**工具签名确认（kb_doc_create）：**
- `kb_id` (必填): 目标 KB 的 UUID
- `name` (必填): 分块文档名，如 `03-Micro-Void-AM-2025_s01_Chapter1_Introduction.md`
- `content` (必填): 该章节的完整 markdown 文本（来自 sed 提取）
- `description` (可选但必写): A4 格式的真实内容描述

**注意事项：**
- 每段内容必须**完整**包括该节标题及其下的所有子标题和正文
- 不要截断句子或段落（以章节边界为准，不以行数为准）
- 图片引用保持不变（涉及图片的 markdown 保留原路径 `![](images/xxx.jpg)`）
- 参考文献部分作为独立一段或附加到最后一节
- **content 大小限制**：如果单个章节 > 100KB（罕见），需要进一步按 `###` 子标题拆分

### A5b-5 — 复制标签到各分块

```
# 对每段分块文档，应用统一继承标签 + 独有标签
kb_doc_update_tags(kb_id, "{分段文档路径}", 
  ["继承标签1", "继承标签2", "该节特有标签1", "该节特有标签2"])
```

**标签策略：**
- 父文档标签全部继承（保证检索时仍能找到）
- 每段额外增加该节特有的领域标签（提高精度）
- 示例：Methodology 节 → 加 "methodology", "experimental-setup"
- 示例：Results 节 → 加 "results", "discussion"

### A5b-6 — 删除原始大文档

当所有分块创建成功并验证后，删除原始文档：

```
kb_doc_delete(kb_id, original_doc_path)
```

**验证条件（全部满足才删除）：**
1. ✅ 所有 M 个分块通过 `kb_get_documents()` 确认存在
2. ✅ 至少随机抽查 1 个分块用 `kb_doc_read()` 验证内容完整
3. ✅ 标签已分配给所有分块

### A5b-7 — 分块文档向量索引

```
# 对所有分块文档路径执行批量索引
kb_batch_index(kb_id, [part1_path, part2_path, ...], force=true)

# 验证
kb_search_stats(kb_id)  → 确认 chunk_count 覆盖了所有分块
```

### A5b-8 — 拆分报告模板

```
📄 大文档拆分报告
  原文档: {文件名} ({size}KB, {lines}行)
  拆分为: {M} 个独立文档

  ├── s01_{节标题}: {description简写} ({size}KB)
  ├── s02_{节标题}: {description简写} ({size}KB)
  ├── ...
  └── s0M_{节标题}: {description简写} ({size}KB)

  标签: 统一继承 [{tag1, tag2}] + 每节独有标签
  向量索引: {total_chunks} chunks ✅
  原始文档已删除: ✅
```

### A5b-9 — 大文档拆分的特殊情况处理

| 情况 | 处理方式 |
|------|---------|
| **文档太大无法一次读取**（>500KB md） | 先读目录/前3K字符 → 确定章节边界 → 用 `head/tail` 或 `split` 分段提取内容 |
| **有图表的论文** | 每个分块保留其图表和图片引用，不拆分图表与其解释段落 |
| **参考文献列表** | 附加到最后一节作为附录，或单独一节的参考文献 |
| **JSON/CSV 等结构化文件** | 按逻辑分组拆分（按年份/按类别/按表），每块加 schema 描述 |
| **代码文件** | 按模块/函数/类拆分，每块前加 import 声明保证可独立阅读 |
| **多语种混合文档** | 不拆分语言，但 description 标注"中英双语"

## A6 — Execute Storage

> **流程改进**：解析前不要写最终 description，只写临时 placeholder（如 "Parsing..."）。
> 解析完成后，再读取真实内容生成 description（A4-0 黄金法则），用 `kb_doc_update_meta` 更新。

### Parse-path files (PDF, Word, DOCX, XLSX, PPTX, images)

**Step 1: 提交解析（先用 placeholder description）**
```
parse_doc(
  file_path="<absolute path>",
  kb_id="<target UUID (sub-KB if applicable, parent if not yet split)>",
  description="Parsing in progress...",   # 临时占位，解析后替换
  tags=["tag1", "tag2"]                    # 初步标签，可后续调整
)
```
→ Returns `{task_id, status:"running"}` immediately.
→ Poll `parse_task_status(task_id)` every 10-15s until `status:"done"` or `"error"`.

**Step 2: 解析完成后，基于真实内容生成 description（A4-0 黄金法则）**
```
# 方式 A: 主 Agent 直接读（适合少量文档）
head -c 3000 <markdown_path>    # 或
kb_doc_read(kb_id, doc_path, max_chars=3000)
# AI 分析内容 → 生成 description

# 方式 B: 委托子 Agent（适合 ≥3 篇文档批量入库，节省主上下文）
Agent(
  subagent_type="general-purpose",
  prompt="""读 {markdown_path} 的前 2000 字符，生成结构化摘要。
  输出 JSON: title/content_preview/domain/methods/scenario/key_results/
  language/suggested_tags/suggested_description（A4格式）"""
)
# 主 Agent 接收 JSON → 写入

# Step 3: 用真实 description 覆盖 placeholder
kb_doc_update_meta(
  kb_id, doc_path,
  description="<A4-1 子Agent生成或主Agent读取后生成的真实description>"
)
```

**Step 4: 进入大小判断（拆分决策）**

**📐 解析结果自动跟踪 + 拆分决策：**
```
parse_result = parse_task_status(task_id)

# 记录关键指标
source_size = <原PDF文件大小 KB>
markdown_chars = parse_result.result.markdown_chars
markdown_lines = wc -l <markdown_path>
image_count = parse_result.result.image_count

if markdown_chars > 80000:
    → ⚠️ 大文档触发：跳转到 A5b 执行智能拆分
    → 此时原始文档已在 KB 中（parse 自动保存）
    → 读取大纲 → 按章节拆分 → 各分块独立入库 → 删除原始文档
    → 拆分完成后再执行 A7（标签分配）
elif markdown_chars > 50000 and markdown_lines > 1000:
    → ⚠️ 中等大小文档：建议拆分
    → 检查是否有明确的章节结构（# 标题数量 ≥ 3）
    → 有章节 → 执行 A5b 拆分
    → 无章节（长段落）→ 保留不拆，但标注"长文档"
else:
    → ✅ 正常文档，继续 A7
```

### Direct-path files (MD, TXT, CSV, JSON, HTML, LOG, code)
```
kb_doc_create(kb_id, name="filename.md", content="<content>", description="<from A4a>")
```

### Batch parse-path
```
parse_doc_batch(file_paths=[...], kb_id, descriptions=[...], tags=[...])
```

## A7 — Assign Tags After Storage

```
kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])
```

For parse-path: wait for `parse_task_status("done")`, then `doc_path` from `kb_get_documents(kb_id)`.

**但如果 A5b 拆分被执行了**，则标签分配到每个分块文档上，原始文档已删除。
此时不在 A7 操作原始文档。

## A7b — 分块文档汇总验证（当 A5b 拆分发生时）

当一个文档被拆分为 M 个分块后，在 A7 标签分配和 A8 验证之间执行：

```
1. kb_get_documents(kb_id) → 确认原始文档已删除，M 个分块文档存在
2. 对每个分块文档：
   kb_doc_read(kb_id, doc_path, max_chars=300) → 确认内容完整、首字符匹配
3. kb_search_stats(kb_id) → 确认向量索引 chunk_count 覆盖所有分块
4. 验证分块描述质量：随机抽查 20% 分块的 description 是否按 A4 标准
```

## A8 — Verify

1. Parse done? Check `parse_task_status`.
2. Doc appears? `kb_get_documents(kb_id)` — find the new entry.
3. Tags applied? `kb_doc_get_by_tag(tag, kb_id)`.
4. KB description poor? Offer to update.

## A9 — Sub-KB Creation Check ⭐

**This is the step that makes your knowledge base scale.** After every ingest
operation, evaluate whether the target KB needs sub-KB restructuring.

### A9a — Threshold Assessment

```
AFTER storage AND verification:

parent_kb = the KB where documents were stored
doc_count = kb_get_documents(parent_kb.kb_id).count  
parent_desc = parent_kb.description (from kb_list)

IF doc_count >= 8:
    # Check if documents fall into ≥2 distinct sub-domains
    for each doc:
        kb_doc_read(kb_id, doc.doc_path, max_chars=500)
        classify doc's sub-domain from content (not filename)
    
    distinct_subdomains = unique(sub-domains)
    IF distinct_subdomains >= 2:
        → Proceed to A9b (create sub-KBs)
    
ELSE:
    → "KB has [doc_count] documents — below 8-doc sub-KB threshold. Flagging for
       re-evaluation when collection grows."
```

### A9b — Create Sub-KBs

For each distinct sub-domain with ≥2 documents:

```
# Create sub-KB with parent_id linking to parent
sub_kb = kb_create(
    name="<ParentDomain>-<SubDomain>",        # e.g. "Thermal-Power-Coal-Mill"
    description="<from A4b template — focused, 2-3 sentences>",  
    parent_id=parent_kb.kb_id
)
```

**Sub-KB naming convention:**
```
<Parent-Domain>-<Sub-Domain>
# Examples:
#   Thermal-Power-Monitoring → Thermal-Power-Coal-Mill
#   AI-ML-Research → AI-ML-Time-Series-Forecasting
#   Wind-Power → Wind-Turbine-Gearbox-Diagnostics
```

**Sub-KB description convention** (must be more precise than parent):
```
[Equipment/Sub-domain] specific research. [Methods used]. 
[Scenario the sub-KB addresses]. 
[N documents]. [Languages].
```

### A9c — Move Documents to Sub-KBs

```
for each doc in parent_kb that belongs to this sub-domain:
    kb_doc_move(doc.doc_path, sub_kb.kb_id)
```

### A9d — Update Parent KB Description

After creating sub-KBs and moving docs, UPDATE the parent description
to mention its sub-structure:

```
kb_update(
    kb_id=parent_kb.kb_id,
    description="[Updated description]. Sub-KBs: [Sub-KB1], [Sub-KB2], [Sub-KB3]"
)
```

This is critical — the parent description must tell the Agent "I'm organized
hierarchically, look at my sub-KBs" during Search's Step 1.

### A9e — Verify Sub-KB Structure

```
kb_list()                          → confirm sub-KBs appear
kb_get_documents(parent_kb_id)     → confirm docs were moved OUT
kb_get_documents(sub_kb_id)        → confirm docs moved IN
fs_get_tree(include_files=False, max_depth=3)  → tree shows hierarchy
```

**Report to user:**
```
"The [Parent-KB] KB has grown to [N] documents across [M] sub-domains, so I've
organized it into focused sub-KBs:

├── [Sub-KB-name]: [description snippet] ([N] docs)
├── [Sub-KB-name]: [description snippet] ([N] docs)
└── [Sub-KB-name]: [description snippet] ([N] docs)

This means future searches can pinpoint the right sub-domain at a glance.
Parent KB description updated to reference these sub-KBs."
```

### A9f — Reindex for Vector Search

After moving documents, reindex affected KBs:

```
kb_batch_index(kb_id=sub_kb.kb_id, force=True)
```

---

## A10 — Report Summary

In your warm precise voice, summarize:
- **What**: filename(s), type, quantity
- **Where**: In which KB (and sub-KB, if applicable)
- **Tags**: list applied
- **Parse status**: completed/failed/still running
- **Hierarchy**: "Created new sub-KB [name] under [parent] for [sub-domain] documents"
- **Quality notes**: "The KB description still reads 'test' — shall I update it?"

---

## CRITICAL: Do NOT Skip
- A1: MUST do `fs_get_tree(max_depth=3)` to understand KB hierarchy before deciding
- A2: classify sub-domain for sub-KB routing, not just top-level domain
- A3: prefer creating a sub-KB (with `parent_id`) over putting in parent when sub-domain is clear
- **A4: 先读内容再写 description 是 GOLDEN RULE**
  - 禁止根据文件名/来源猜测 description
  - 禁止用 "Parsed from XXX.pdf" 作为 description
  - ≥3 篇文档入库时必须用子Agent提取摘要，保持主上下文干净
  - description 必须包含从真实内容中提取的方法/场景/亮点
  - 写入后用 A4d 验证 description 中的关键断言是否在内容中出现
- **A5b: 大文档拆分是 MANDATORY 而非 OPTIONAL** — markdown_chars > 80000 或行数 > 2000 行的文档必须拆分。
  拆分时不能盲拆，必须先读目录确定章节结构，每段生成独立 description 再入库。
- A6 → A5b: 解析完成后立即检查大小，大文档走拆分流程，拆分完成才进 A7。
- A8: verify 确认分块文档完整、description 达标、原文档已删除
- A9: sub-KB check prevents retrieval degradation as KB grows

## 大文档拆分流程总览
```
解析完成 (A6)
   ↓ 检查 markdown_chars > 80000 或 lines > 2000
   ↓
[是] → A5b-0 大小检测
         ↓
        A5b-1 预读大纲（读前 3000 字符提取章节结构）
         ↓
        A5b-2 确定拆分方案（按 #/## 节标题或标准论文结构）
         ↓
        A5b-3 逐段读取 + 智能摘要（每段独立分析）
         ↓
        A5b-4 分块创建文档（kb_doc_create）
         ↓
        A5b-5 复制标签（继承 + 独有）
         ↓
        A5b-6 删除原始文档（验证全部成功后）
         ↓
        A5b-7 分块向量索引（kb_batch_index）
         ↓
        继续 A7 确认 + A8 验证

[否] → 正常文档，继续 A7
```

## Sub-KB Health Warning Signs (for Organize/Verify)
- Parent KB with ≥8 docs but NO sub-KBs → strong signal for sub-KB creation
- Sub-KB with 1 doc → evaluate if it should be merged back
- Sub-KB with description same as parent → defeats purpose, rewrite to focus
- KB with parent_id but description parent-KB-style → rewrite to sub-domain focus
