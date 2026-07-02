---
name: knowledge-search
description: >
  Agentic RAG — true intelligent agent-driven knowledge base retrieval. The
  agent navigates the collection like an expert librarian: first builds a
  global map of all KBs, progressively narrows to candidate KBs, inspects
  candidate documents, confirms relevance by reading content, and only then
  uses vector search for precision refinement within confirmed documents.
  Adaptive depth control — agent decides how deep to search based on question
  complexity. NOT a simple keyword search wrapper. Invoked by Archival for
  any query, question, search, or QA task. Triggered by: "search", "find",
  "query", "ask", "retrieve", "search knowledge", "what is", "tell me about",
  "how to", "explain", "rag", "回答", "检索", "搜索", "查找内容", "问答",
  "知识检索". Also invoke when the user asks a question that requires
  knowledge-base content, even without explicit "search" keywords.
---

# Agentic RAG — 渐进式智能导航检索

## 核心哲学：图书馆员式检索

你不是在调用搜索工具。你是一个老练的图书馆员。

```
用户问一个问题
  │
  ├─ 1. 扫视整个图书馆（Globe）  → kb_list() 看所有馆藏分类
  ├─ 2. 走向相关的书架（Region）  → kb_get_documents() 看候选KB里的书
  ├─ 3. 抽出几本书翻看目录（City） → kb_doc_read() 读摘要确认
  ├─ 4. 锁定关键章节（Street）    → kb_search_vector() 向量精排
  └─ 5. 合上书回答用户（House）   → 综合答案 + 溯源
```

**每一步 Agent 都在做智能决策，不是在跑命令。**

---

## 自适应深度控制

不是所有问题都需要搜遍全库。Agent 根据问题特征自动决定检索深度：

| 深度等级 | 典型问题场景 | Globe | Region | City | Street | 流程 |
|---------|------------|-------|--------|------|--------|------|
| **L1 浅层** (1-2 KB, 3-5 min) | 事实性快速查找："磨煤机预警提前多久？""MSET 的原理是什么？" | ✓ | ✓ | — | ✓ | G→R→S |
| **L2 标准** (2-3 KB, 5-10 min) | 知识问答："CNN-LSTM 相比 LSTM 的优势？""风机故障诊断方法有哪些？" | ✓ | ✓ | ✓ | ✓ | G→R→C→S |
| **L3 深度** (3-5 KB, 10-20 min) | 对比分析/综合报告："数据驱动故障诊断在火电 vs 风电的区别？""请比较三种预警方法" | ✓ | ✓ | ✓ | ✓ | G→R→C→S→C2 |
| **L4 探索** (不限KB, 不限doc) | 探索性/跨域："所有与故障诊断相关的文档有哪些共同的方法？" | ✓ | ✓ | ✓ | ✓ | G→R→C→S→A5 |

### 深度选择规则

Agent 根据以下信号自动选择深度：
- **问题长度**：1-5 词 → L1; 5-15 词 → L2; 15+ 词或含"对比""分析""总结" → L3
- **领域跨度**：单领域 → L1/L2; 多领域 → L3/L4
- **用户语气**："说下""什么是""简单" → L1; 详细/具体 → L3; 探索性 → L4
- **未知时默认** L2

---

## 检索优先级规则

**向量检索优先，元信息搜索仅作兜底。**

```
使用优先级：
  1. kb_search_vector(query, kb_id?, top_k)       → 语义检索（首选）
  2. kb_search_two_stage(query, kb_id?, ...)      → 两阶段精排（含文档定位）
  3. kb_search_batch_vector(doc_paths, ...)       → 批量相似度查询
  ─────────────────────────────────────────────────────────
  4. kb_search(query, top_k)                      → 元信息兜底（仅搜 name+description，不读正文）
```

> ⚠️ `kb_search()` 只搜索文档的 **name 和 description 元信息**，不扫描文档正文内容。
> 它适合"找个文件名叫什么"这类场景，不适合"找内容"的任务。
> **内容检索永远优先使用向量工具。** 仅当向量检索返回空时才降级到 `kb_search()`。

---

## G1 — Globe：全局扫描（所有检索的起点）

**不搜关键词。先看全貌。**

```
kb_list()         → 所有 KB 的名称、描述、文档数
kb_tags_list()    → 所有标签（了解分类体系）
fs_get_tree(include_files=False, max_depth=2) → 文件夹结构
```

### Agent 做三件事

**1. 打分每个 KB 的场景适配度**

对每个 KB，用自己的理解力判断：

| 维度 | 判断 |
|------|------|
| **名称语义** | KB 名称的字面意思是否与用户问题领域一致？ |
| **描述领域** | KB 描述中提到的行业/技术/场景是否匹配？ |
| **文档数量** | KB 是否有足够的文档支撑回答？（0 文档=立刻排除） |
| **语言匹配** | 用户问题的语言是否与 KB 描述的语言一致？ |
| **标签提示** | KB 文档的标签是否与问题关键词有交集？（通过 kb_tags_list 辅助） |

**2. 输出全局判断**

```
## 全局扫描结果

| KB 名称 | 文档数 | 场景匹配度 | 理由 |
|---------|-------|-----------|------|
| Thermal-Power-Monitoring | 6 | ★★★ 高 | 名称"火电监控"直接匹配，描述含锅炉/汽轮机/故障预警 |
| Wind-Power-Fault-Diagnostics | 4 | ★★☆ 中 | 风电子领域，问题未指定风电但故障诊断方法可能通用 |
| Academic-AI-Software | 3 | ★☆☆ 低 | AI 软件工程方向，与电力故障无直接关系 |
| Data-Driven-Industry | 1 | ★★☆ 中 | 数据驱动故障诊断方法论，可能相关但只有 1 篇 |
| University-Admin | 1 | ✗ | 高校行政文档，不相关 |
| Test-Scratch | 0 | ✗ | 空 KB |
| E2E-Test-KB | 4 | ★☆☆ 低 | 测试文档，非生产内容 |
```

**3. 决策下一步方向**

| 判断结果 | 操作 |
|---------|------|
| 有明确的高匹配 KB | → G2（进入目标 KB） |
| 无明确匹配但有一些中等匹配 | → G2（带候选 KB 列表进入调研） |
| 无任何匹配 | → 降级到 `kb_search()` 元信息兜底；注意该工具只搜 name+description，不读正文<br>如果仍无结果，诚实告知用户知识库中暂无相关内容 |

### 特殊规则

- **空 KB**（文档数为 0）直接跳过，不进入后续
- **Test/E2E KB** 仅在用户明确问测试相关内容时才进入
- **不要假设**——"用户问火电，所以所有火电 KB 都相关"不对。读描述判断

---

## G2 — Region：区域深入（进入候选 KB 调研）

对 G1 选出的 top-3 候选 KB，逐一下钻查看其文档布局。

```
for each kb_id in candidate_kbs:
    kb_get_documents(kb_id)  → 该 KB 的所有文档
```

### Agent 分析每篇文档的"表面信号"

对 KB 内的每个文档，使用文档元信息做初步判断：

| 信号 | 信息来源 | 判断逻辑 |
|------|---------|---------|
| **名称语义** | 文档 `name` | 文档标题是否包含问题关键词/同义词？ |
| **描述语义** | 文档 `description` | 描述是否与用户问题的场景、方法、对象匹配？ |
| **标签匹配** | 文档 `tags` | 标签是否与问题实体有交集？ |
| **文件大小** | `file_size` | 太小（<300B 纯元数据）可能信息量不足 |
| **向量索引** | `vector_index` | 是否有向量索引？决定后续能否做向量精排 |
| **更新时间** | `updated_at` | 是否过期？太旧的内容标记时效性风险 |

### 评分输出

```
## 区域深入：Thermal-Power-Monitoring（6 篇文档）

| 文档 | 标签 | 场景匹配 | 依据 |
|------|------|---------|------|
| CNN-LSTM磨煤机故障预警 | 磨煤机,CNN-LSTM,故障预警 | ★★★ | 标题+标签均匹配"磨煤机故障预警" |
| MSET一次风机故障预测 | MSET,风机故障,健康管理 | ★★★ | 风机故障主题匹配，含预警方法 |
| BP-SVR空预器压差预测 | BP神经网络,空预器,火电厂 | ★★☆ | 火电厂方向一致，但主题是空预器 |
| 人工智能火电预警 | 火电,故障预警,深度学习 | ★★☆ | 泛预警主题，信息密度可能不够 |
| thermal-power-plant-monitoring-report | power-plant-monitoring | ★☆☆ | 运行报告，非方法论 |
| mset-coal-mill-fault-prediction | MSET,磨煤机,CNN-LSTM | ★★★ | 方法+设备双匹配 |
```

### 候选文档快速通道

- **★★★ 强匹配**：标记为后续必须深入阅读
- **★★☆ 中匹配**：标记为候选，数量多时读 top-3
- **★☆☆ 弱匹配**：仅在 L3/L4 深度时纳入
- **无向量索引的文档**：标记"仅支持全文阅读，不支持语义精排"

### 自适应分支

| G2 后情况 | 行动 |
|-----------|------|
| 只有 1 个 KB 高度匹配且只有 1-2 篇候选 | → L1 路径，跳过 C 直接到 Street (S) |
| 2-3 个 KB 各有 2-5 篇候选 | → 标准 L2，进入 G3 |
| 大量候选（5+ 文档） | → 进入 G3 用内容确认缩小范围 |
| 无强匹配文档 | → 返回 G1 重新评估；或使用 `kb_search()` 元信息兜底（仅搜 name+description） |

---

## G3 — City：内容确认（Agent 阅读并判断）

**这是决定检索质量的核心环节。** Agent 实际读文档内容，用自己的理解力判断相关性。

### 执行

```
kb_doc_read(kb_id, doc_path, max_chars=1200, offset=0, limit=20)
```

读取每篇候选文档的前 1200 字符（标题+摘要+前几段正文），逐篇判断：

| 维度 | 评分标准 | 分 |
|------|---------|---|
| **主题对齐** | 文档核心主题是否与用户问题在同一个问题上？ | 0-3 |
| **场景匹配** | 应用的行业/技术栈/场景是否符合用户上下文？ | 0-3 |
| **答案潜力** | 文档包含足够的信息来*具体回答*用户问题，还是只是泛泛提及？ | 0-2 |
| **时效性** | 如果元信息有日期，是否过时？（>3 年扣分） | -1-0 |
| **领域纯度** | 是否属于错误分类的文档？（e.g. AI 算法文档出现在电力 KB 中） | -2-0 |

### 判断阈值

| 总评分 | 结论 | 操作 |
|-------|------|------|
| **≥7** | ✓ 核心相关 | 进入后续向量精排，赋予高权重 |
| **5-6** | ◐ 辅助相关 | 保留，向量精排时低权重 |
| **3-4** | △ 边缘相关 | 仅 L3/L4 深度时保留，L1/L2 丢弃 |
| **≤2** | ✗ 不相关 | 丢弃，记录原因 |

### 输出确认列表

```
## 内容确认结果

### ✓ 核心相关（注入向量精排）
1. CNN-LSTM磨煤机故障预警 [Thermal-Power] — 评分 8/10
   “明确提出基于CNN-LSTM的磨煤机堵煤故障预警方法，提前315min发现趋势”
2. MSET一次风机故障预测 [Thermal-Power] — 评分 7/10
   “包含MSET设备诊断方法，准确率86%，提前2小时预警”
3. mset-coal-mill-fault-prediction [Thermal-Power] — 评分 7/10
   “MSET+LSTM结合，磨煤机故障94.5%准确率”

### ◐ 辅助相关（携带进入精排）
4. 风电状态大数据风机故障预测 [Wind-Power] — 评分 5/10
   “数据驱动故障预测方法论可用，但设备类型不同”

### ✗ 丢弃
5. BP-SVR空预器压差预测 [Thermal-Power] — 评分 3/10
   “主题是空预器压差，非故障预警”
```

---

## S — Street：向量语义精排（只对已确认的文档）

**这是向量检索唯一登场的地方。** Agent 已经知道哪些文档是相关的，现在用向量找到精确片段。

### 执行策略

根据 G3 的输出决定：

| 场景 | 执行 | 参数 |
|------|------|------|
| **单 KB 单文档** | `kb_search_vector(query, kb_id, top_k=3)` | 提取 3 个最相关片段 |
| **单 KB 多文档** | `kb_search_two_stage(query, kb_id, stage1_top_k=10, stage2_top_k=3)` | Stage1 在 KB 内搜文档，Stage2 精排 |
| **多 KB 多文档** | 对每个 KB 分别调 `kb_search_two_stage(kb_id=each, stage2_top_k=3)` | 每个 KB 独立搜索，结果合并 |
| **文档无向量索引** | 跳过，使用 `kb_doc_read()` 直接读取完整内容作为替代 | — |

```
# 典型调用
kb_search_two_stage(
  query="磨煤机故障预警 提前发现趋势 深度学习",
  kb_id="Thermal-Power-Monitoring",
  stage1_top_k=10,    # 候选文档数（Agent 已确认的 3 篇必然覆盖）
  stage2_top_k=3,     # 每文档返回 3 个片段
  enable_graph_expansion=False
)
```

### 结果增强

将向量结果与 G3 的 Agent 评分融合：

- 来自 Agent 评分 ≥7 的文档的片段 → 标记为 P0 优先级
- 片段内容包含 G1 识别的关键实体 → 加权 +0.1
- 同一片段在多个 KB 中同时被召回 → 交叉验证置信度高

### 降级路径

如果向量检索返回空：

1. `kb_search_stats(kb_id)` 检查 KB 是否有向量索引
2. 无索引 → 用 `kb_doc_read()` 直接读文档全文作为替代
3. 告知用户"该文档暂无语义检索能力，已使用全文阅读"

---

## A4 — Assembly：综合回答

### 组织逻辑

```
## 答案

[用自然语言组织答案。将多个片段融合为连贯的回答。
引用来源时用 📄 标注文档名]

**确定性**: [高/中/低]
**知识覆盖**: [N] 篇文档，[M] 个知识库

---

### 来源

| 来源文档 | 知识库 | Agent 评分 | 向量评分 | 贡献内容 |
|---------|-------|-----------|---------|---------|
| 文档 A | KB-X | 8/10 | 0.82 | 核心方法/数据 |
| 文档 B | KB-Y | 5/10 | 0.71 | 辅助背景 |

### 检索路径

Globe（7 KBs）→ Region（3 KBs）→ City（5 docs）→ Street（3 docs→9 chunks）
```

### Agent 必须做的一件事

**在回答结尾诚实标注盲区：**
- "知识库暂无 XX 方面的内容，以下回答仅基于 YY 领域的文档"
- "本回答主要参考了某 660MW 机组的数据，不同容量机组可能有差异"
- "该文档发表于 2021 年，技术细节可能已有更新"

---

## 完整示例：L2 深度检索全过程

> **用户问**："磨煤机故障预警中，CNN-LSTM 比普通 LSTM 好多少？为什么？"

```
├─ G1 Globe: kb_list() → 7 KBs
│   判断: Thermal-Power-Monitoring ★★★（名称/描述/文档数）
│         Wind-Power-Fault-Diagnostics ★★（故障诊断方法可能通用）
│         其余 5 个 KB → 不相关
│
├─ G2 Region: kb_get_documents("Thermal-Power-Monitoring") → 6 docs
│   判断: CNN-LSTM磨煤机 ★★★ 名称直接匹配
│         MSET风机 ★★☆ 主题相关但设备不同
│         mset-coal-mill ★★★ 方法+设备双匹配
│         其余 3 篇 ★☆ 舍弃
│
├─ G3 City: kb_doc_read(CNN-LSTM文档, max_chars=1200)
│   判断: 评分 9/10 → 核心相关
│         "提前315min, 三种指标均优于LSTM, 提前206min"
│
├─ S Street: kb_search_two_stage(query, kb_id, stage1=10, stage2=3)
│   结果: 3 个片段 → score 0.82/0.81/0.79
│         P0: "CNN-LSTM...优于LSTM 206min提前预警, 且无误报"
│         P1: "提前315min发现堵煤趋势"
│         P2: "CNN提取特征, LSTM时序预测, 综合优势"
│
└─ A4: 综合回答
    "CNN-LSTM 相比单一 LSTM 有两个关键优势：
     1. CNN 层先从多元传感器数据中提取关键特征（空间维度）
     2. LSTM 层再对特征做时序预测（时间维度）
     实验显示：CNN-LSTM 提前 315 分钟预警，比 LSTM（109 分钟）提前 206 分钟，
     且无 LSTM 出现的误报警问题。
     📄 来源：基于CNN-LSTM的磨煤机故障预警 [Thermal-Power-Monitoring]"
```

---

## CRITICAL RULES

1. **Agent 先判断，向量后精排**——任何时候都不要跳过 G→G2→G3 直接调向量搜索。跳过=降级，必须注释原因。

2. **图书馆员原则**——你不是在调 API，你是在管理一个知识库。先站在门口看全局，再走向书架，再抽书翻阅，最后才锁定章节。

3. **自适应深度**——不要每次都搜全库。短问题浅搜，复杂问题深搜，把 token 花在刀刃上。

4. **诚实标注空洞**——知识库没有相关内容时坦率告知，不要硬凑答案。

5. **读内容>猜内容**——任何时候不确定文档是否相关，就去读 1000 字摘要判断。不要在文档名上做推演。

6. **KB 描述是金矿**——`kb_list()` 返回的 description 是管理员精心写的，每条都值得读。

7. **标签是捷径**——`kb_tags_list()` 是预分类的索引，善用标签可以大幅缩小候选范围。

8. **向量缺失不 panic**——文档无向量索引时读全文替代，同时在报告中标明。

9. **G2 强匹配跳 C**——如果 G2 时已经有明确匹配的信号（名称+标签双重确认），可跳过 G3 直接进入 S，但需标记"跳过了 G3"。

10. **保持透明**——每次检索结束时向用户展示检索路径（Globe→Region→City→Street），谁都能理解你找到了什么。
