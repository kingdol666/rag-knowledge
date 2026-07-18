---
name: knowledgebase-search
description: >
  Query-Driven Content-Verified Retrieval (QDCVR). Step0 query analysis+rewrite
  → Step1 smart KB selection → Step2 two-stage vector+BM25 recall (balance_kbs)
  → Step2.5 document dedup+hard threshold → Step3 content verification (0-8 scoring)
  → fast exit if score≥6, otherwise Step4 tag+description expansion → Step5 confidence
  rating → Step6 synthesized answer with sources and blind-spots. Vector is fast,
  content is accurate. Triggered by: search, find, query, ask, retrieve, 搜索, 检索,
  查询, 问答, 帮我查, 问一下知识库, 搜.
---

# QDCVR — 查询驱动 · 内容裁决 · 门控精炼检索

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**
- 当 knowledgebase 调度器检测到搜索场景后 → 路由到本 skill
- 本 skill **必须**委托 Archival agent（`Agent(subagent_type="archival", ...)`）执行
- Archival 禁止：跳过 Step 0 查询改写、跳过内容验证、跳过盲点声明

**六条铁律**（包含 ⭐ MCP 优先原则）：
1. **先理解再检索**——原始查询先改写为检索友好形态（Step 0），不直接喂给检索器。
2. **先选库再召回**——跨库时先判定相关 KB（Step 1），避免跨域噪声和大库主导。
3. **向量快召回，内容真裁决**——向量定候选，读正文 0-8 打分定去留，向量分不左右决策。
4. **文档级去重 + 硬阈值**——同文档只留最高分 chunk，score < 阈值直接丢弃。
5. **宁可不给，不要错给**——无确认命中即诚实声明盲点，不编造。
6. ⭐ **MCP 优先原则**——所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`），禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API 替代 MCP 工具。MCP 不可用时才可向用户报告让用户决策。

---

## 思维框架：检索前先弄明白三个问题 ⭐

```
用户"搜一下X"
  │
  ├── 这是什么类型的查询？
  │   事实型(what) / 方法型(how) / 对比型(A vs B) / 故障型(why broken) / 导航型(where)
  │
  ├── 搜哪个KB？
  │   明确说"搜XX库" → 直接该库
  │   没说 → Step 1 智能选库
  │
  └── 能不能快速回答？
      经验优先？ → 故障型先查经验库
      文档直接命中？ → 快速退出
```

---

## Step 0 — 查询分析与改写 ⭐（检索质量的第一道关）

> 实测病灶：长自然语言查询直接检索，BM25 命中关键词但不懂语义（查"PET 薄膜"竟返回 PP 文献）。

### 0a 意图分类
| 类型 | 特征 | 检索侧重 |
|---|---|---|
| **事实型** | "是什么""定义" | 向量精排 + 权威综述文档 |
| **方法型** | "怎么做""如何""方法" | 向量 + 标签(方法词) |
| **对比型** | "A vs B""区别" | 多实体并行召回 |
| **故障/运维型** | "报错""失败""怎么解决" | **先查经验库**（experience-first），再查文档 |
| **经验/案例型** | "有没有类似案例""以前怎么处理" | `experience_search_global` 优先，不足补文档 |
| **导航型** | "哪里有""有没有" | kb_catalog + kb_doc_catalog 描述匹配 |

### 0b 核心实体提取
从查询里提取：**主体**(PET/RAG/锂电池) + **属性**(结晶度/幻觉/热管理) + **约束**(工艺参数/2024)。

### 0c 查询改写（生成检索友好 query）
- 原始口语查询 → **声明句 + 关键词组合**
- 例：`"PET薄膜双向拉伸工艺参数对结晶度的影响"`
  → 改写1（向量用）: `"PET聚酯薄膜双向拉伸工艺中拉伸比/温度/速度对结晶度与晶态结构的影响"`
  → 改写2（BM25用）: `"PET BOPET 双向拉伸 结晶度 拉伸比 工艺参数"`
- 多概念查询 → **拆成子查询并行检索**（对比型必备）

**故障/运维型查询**：先 `experience_search_global(query, top_k=5)`，命中经验则优先用。

## Step 1 — 智能选库（跨库时必做）⭐

> 实测病灶：全库盲搜 → 大库（Materials-ML 11docs/1156chunks）主导结果，跨域噪声涌入。

```
catalog = kb_catalog()    # 仅 [{kb_id, name, description, doc_count}]，context 友好
```
- 用模型判断力读每个 KB 的 description，选 **top 1-3 真正相关** 的 KB。
- **优先在选中的 1-3 个 KB 内检索**（`kb_id=<选中KB>`）；仅当选中 <2 KB 或无命中时才全库 `kb_id=""`。
- 故障型查询：经验库优先，文档库作补充。

**判据**：KB description 的领域与查询实体一致才入选。例：查 RAG → 只选 `AI-ML-Research`。

### Step 1b — 层次化KB穿透（父KB含子KB时必做）⭐

> 实测病灶：父KB搜索（如 高分子双向拉伸文献库）返回子KB容器条目，内容一律为空——子KB无向量chunk。

**检测**：`kb_graph_kb_overview(kb_id)` → 若 `sub_kbs` 列表非空则说明是层次化KB（`kb_doc_catalog` 无 `type` 字段，无法直接区分文档与子KB容器）。

**穿透策略**：
```
# 1. 获取子KB列表
overview = kb_graph_kb_overview(kb_id)  → {sub_kbs: [{kb_id, doc_count}]}

# 2. 对每个子KB，读其 description 判断相关性
for sub in sub_kbs:
    docs = kb_get_documents(sub.kb_id)  → 看首条 description + 文档类型

# 3. 在相关子KB内分别搜索（并行）
kb_search_two_stage(query=..., kb_id=relevant_sub_kb_id, ...)

# 4. 合并结果 → Step 2.5 去重
```
**优化**：子KB ≥5时，先用 `kb_doc_catalog(kb_id)` 的 description 筛选，只搜索 top 3-5 相关子KB。

## Step 2 — 向量召回（两阶段，平衡多库）

```
kb_search_two_stage(
    query=Step0改写后的query,
    kb_id=Step1选中的KB 或 ""(全库),
    stage1_top_k=20,          # BM25 候选文档
    stage2_top_k=5,           # 每文档返回 chunk 数
    enable_graph_expansion=true,
    score_threshold=0.35,     # 向量硬阈值（<=0 用后端默认 0.35）
    balance_kbs=True          # ⭐ 跨库时必开，防大库主导
)
```

### 调参指引
| 场景 | stage1_top_k | stage2_top_k | score_threshold |
|------|-------------|-------------|-----------------|
| 标准 | 20 | 5 | 0.35 |
| 大库(>10文档) | 30 | 5 | 0.35 |
| 小库(<5文档) | 10 | 3 | 0.30 |
| 精度优先 | 20 | 3 | 0.45 |
| 召回优先 | 30 | 10 | 0.30 |

### 空结果处理
- 返回 0 条 → 降低 score_threshold 到 0.30 重试
- 依然 0 → 放弃向量，走 Step 4 标签扩展

## Step 2.5 — 文档级去重 + 硬阈值过滤 ⭐（精炼结果集）

> 实测病灶：单次查询返回 55 条，`Self-RAG.md` 出现 5 次，大量 score<0.4 噪声未截断。

对 `stage2.results` 执行：

```
1. 硬阈值过滤：丢弃 score < 0.35 的片段
2. 文档级去重：同一 doc_path 只保留 score 最高的 1 个 chunk
3. 短内容降级：chunk 正文 <50 chars → 直接丢弃；50-200 chars → 标记 ⚠️，打分时降一级
4. 排序：按 score 降序，取 top 5 进入 Step 3（与 Step 3 的 "top 3-5" 对齐：Step 2.5 准备 5 个候选，Step 3 对前 3-5 个进行内容验证）
```
**例外**：对比型查询（A vs B）保留 A 和 B 各自最高分 chunk。

## Step 3 — 内容验证（核心裁决，独立于向量分）

对 top 5 去重后的候选进行内容验证（Step 2.5 已精简至 5 个候选）：
```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```
**0-8 打分（可操作判据）**：

| 维度 | 分 | 判据 |
|---|---|---|
| **主题相关** (0-3) | 3=正文直接围绕查询主体；2=涉及主体；1=边缘相关；0=无关 |
| **场景/问题匹配** (0-3) | 3=直接解决查询的问题；2=相关方法可迁移；1=泛泛涉及；0=答非所问 |
| **答案证据** (0-2) | 2=正文含可直接引用的具体数据/步骤/结论；1=有方向性信息；0=空泛 |

**内容分 > 向量分。** 向量 0.9 但内容 ≤3 → 丢弃。向量 0.5 但内容 ≥6 → 采用。

### Step 3 快速退出
| 最高内容分 | 动作 |
|---|---|
| **≥6** | ✅ 直接进 Step 6 作答（跳过 Step 4-5）|
| **5** | ⚠️ 可用但需补充 → 继续 Step 4 扩展召回 |
| **≤4** | ❌ 当前召回未命中 → 继续 Step 4 扩展召回 |

### Step 3 内容分边界决策
- 分数刚好 4 或 5，不确定？ → 重读 500 chars 确认，不回退到 Step 2
- 多文档分数相近且 >5？ → 取最高分 2-3 篇综合回答，不要全部引用
- 内容分高但文档看起来过时（2020 年前）？ → 降一级标注时效性

## Step 4 — 标签 + 描述扩展（向量未命中时）

```
kb_tags_list()
kb_doc_get_by_tag(tag="<语义匹配的标签>", kb_id=Step1选中库 或 "")
kb_doc_catalog(kb_id)   # 新发现 KB 的文档描述清单
kb_search_vector(Step0改写query, kb_id="", top_k=10, score_threshold=0.30)
```

## Step 5 — 扩展内容验证 + 置信度定级

对 Step 4 新候选同样 `kb_doc_read` + 0-8 打分，保留 ≥5，丢 ≤4。

**最终置信度**：
| 来源 + 内容分 | 层级 |
|---|---|
| 向量/标签召回 + 内容 ≥6 | **P0 Strong** — 直接引用作答 |
| 向量/标签召回 + 内容 =5 | **P1 Confirmed** — 采用并标注 |
| 仅描述匹配 + 内容 =5 | **P2 Supplement** — 补充用，标注弱 |
| 内容 ≤4 | **丢弃** |

**短内容（<200 chars）降一级**；**跨库盲点**：确认的 P0/P1 来自 <2 个 KB → 升级到 `Skill("knowledgebase-search-enterprise")`。

## Step 6 — 综合回答（强制规范）

```
## 答案
<基于 P0/P1 文档的综合回答，引用具体数据/结论>

## 来源（按置信度排序）
- [P0] <文档名> @ <KB/路径> — <为什么相关 一句话>
- [P1] <文档名> @ <KB/路径> — <补充了什么>

## 置信度
高/中/低 — <理由，如"3篇 P0 文档一致支持"或"仅 1 篇 P1，需进一步验证">

## 盲点（诚实声明）
- <查询涉及但知识库未覆盖的部分>
- <有争议/时效性/需用户确认的点>
```

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 原始口语查询直接喂检索器 | BM25 语义盲 | Step 0 改写为声明句+关键词 |
| 跳过 Step 1 全库盲搜 | 跨域噪声涌入 | 先选库，限制在 1-3 个 KB |
| 内容验证靠猜（不读文档） | 向量分不反映真实内容 | `kb_doc_read` 3000 chars 再打分 |
| score<0.35 保留不截断 | 跨域低分污染 | Step 2.5 硬阈值截断 |
| 内容分≤4 还纳入答案 | 宁可不给不要错给 | 丢弃→Step 4 扩展 |
| Step 6 不声明盲点 | 用户以为知识库全覆盖 | 诚实声明覆盖盲区 |

## 规则速查
1. **Step 0 必做**——原始口语查询不直接检索
2. **Step 1 跨库必做**——选库降噪
3. **balance_kbs=True**（跨库）——防大库主导
4. **Step 2.5 必做**——文档级去重 + 硬阈值
5. **内容分 > 向量分**——读 3000 chars 独立打分
6. **命中即退**——内容 ≥6 直接答
7. **标签是扩展器**——仅向量未命中时用
8. **经验优先**——故障/运维型先查 experience
9. **诚实盲点**——无确认命中就声明
