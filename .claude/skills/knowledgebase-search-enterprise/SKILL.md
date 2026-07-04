---
name: knowledgebase-search-enterprise
description: >
  企业级智能检索 — 多策略自适应路由。当标准 kb_search_two_stage BM25 stage1
  跨库搜索无法覆盖语义不同的知识库时，自动将向量语义搜索作为 fallback。
  支持 Agentic 判断优先 + 多路召回 + 交叉验证 + 内容重排序。适用于复杂
  跨域联表查询、多 KB 交叉检索、精度要求极高的企业级场景。由 knowledgebase-search
  在检测到跨库搜索需求或 BM25 召回不足时自动路由。
  Trigger keywords: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观,
  cross-KB, all KBs, enterprise search, 全局搜索, 全面的,
  thorough search, comprehensive.
---

# Enterprise-Grade Multi-Strategy Retrieval

当 `knowledgebase-search` 的标准 Agentic RAG 流程遇到下列场景时，自动升级到本 Skill：

## 触发条件（任一即触发）
1. 跨库搜索返回的候选来自 <2 个不同的 KB（BM25 盲区）
2. 用户明确要求"全部 KB"或"全库搜索"
3. stage1 候选数 < 3（关键词覆盖面不足）
4. 同时存在中文和英文 KB，表述差异大

## 企业级检索流程（5 阶段）

### Phase 1 — 多路召回（并行）

对同一查询，并行触发 **3 条检索路径**：

```
# 路径 A: Agentic Catalog 判断（轻量，Agent 推理）
kb_catalog()  # Agent 读 KB description 判断相关性

# 路径 B: 两阶段检索（关键词 + 向量）
kb_search_two_stage(query, kb_id="", stage2_top_k=3)

# 路径 C: 纯向量跨库检索（作为语义 fallback）
kb_search_vector(query, kb_id="", top_k=5)
```

**并行执行，避免串行延迟。** 3 条路径各自独立，覆盖不同的匹配策略。

### Phase 2 — 交叉验证与去重

从 3 条路径收集的所有候选文档中：

1. **路径 A 结果**（Agentic 判断）：Agent 对每条路径的候选 KB 评分
2. **路径 B 结果**（BM25+向量）：有 BM25 keyword 信号支撑，信度最高
3. **路径 C 结果**（纯向量语义）：补全路径 B 的 BM25 盲区

**去重**：同一条 doc_path 出现在多条路径中 → 合并 score（取最高），标记"多路命中"（信号更强）

**交叉验证打分规则**：
| 命中模式 | 信度 | 处理 |
|----------|:----:|------|
| A+B+C 三路命中 | ★★★★★ | P0 强推，最高优先级 |
| B+C 双路命中 | ★★★★ | P0 强推 |
| A+C 双路命中 | ★★★ | P1 输出（有语义但无关键词，可能是同义表述） |
| A 单路命中 (Agentic) | ★★ | P1 输出（Agent 判断有理论依据但被关键词和向量忽略） |
| C 单路命中 (纯向量) | ★ | P2 灰区（需要更严格的内容验证才能提升） |

### Phase 3 — 短文本过滤（关键增强 ⚠️）

向量搜索可能返回短文本 chunk（如 "## 问题"、"## 方案" 等仅标题的片段），这些片段 score 可能虚高但内容无意义。

**短文本过滤规则：**
```
if len(chunk_content.strip()) < 50 characters:
    → 降级到 P2 或丢弃
    → 除非该 chunk 的 doc_path 已有 P0/P1 候选（短 chunk 可能只是该文档的某一部分）
```

多于 50% 的 chunk 为短文本 → 该文档整体降级。

### Phase 4 — 内容重排序（Content Rerank）

对经过交叉验证和过滤后的最终候选（≤10 条），逐条读取内容并评分：

```
kb_doc_read(kb_id, doc_path, max_chars=1500)
```

| 维度 | 权重 | 评分标准 |
|------|:----:|---------|
| 主题对齐 | 0-3 | 文档是否在讲查询涉及的核心主题？ |
| 场景匹配 | 0-3 | 故障/设备/方法是否与查询一致？ |
| 可执行性 | 0-2 | 文档是否提供具体可操作的信息？ |
| 领域纯度 | -2~0 | 文档是否属于错误的 KB 分类？ |

**总分 ≤4 → 丢弃**  
**总分 ≥6 → P0 优先呈现**  
**总分 5 → P1 标注**

### Phase 5 — 融合展示

```
## 检索结果

### 多策略召回摘要
- 路径 A (Agentic): N 个 KB 候选
- 路径 B (两阶段): M 篇文档候选
- 路径 C (纯向量): K 个 chunk 候选
- 去重后合并: J 个独立候选
- 内容验证后保留: L 个

### 最终文档排名（按信度从高到低）

| # | 文档 | KB | 命中模式 | 信度 | 内容评分 |
|---|------|----|----------|:----:|:----:|
| 1 | doc_path | KB | A+B+C | ★★★★★ | 8/8 |
| 2 | doc_path | KB | B+C  | ★★★★ | 7/8 |
| ... | ... | ... | ... | ... | ... |

### 推荐的答案
[融合组织。P0 内容优先，P1 补充，P2 不呈现]

**盲区声明**: 本次搜索未覆盖的 [领域/语言/KB]
**确定性**: 高/中/低
```

## 与 knowledgebase-search 的集成

在 `knowledgebase-search/SKILL.md` 的 Step 4（向量确认）中增加判断：

```
如果 kb_search_two_stage 跨库搜索返回 <2 个不同 KB 的候选：
   → 触发 knowledgebase-search-enterprise 的多路召回流程
```

## CRITICAL RULES

1. **3 路并行** — 不要让各阶段串行执行。并行启动 kb_catalog + kb_search_two_stage + kb_search_vector。
2. **短文本必须过滤** — 低于 50 字符的 chunk 不是有效内容，即使 score 高也不能盲目采纳。
3. **跨库必须至少 2 个 KB** — 如果最终结果只来自 1 个 KB，必须在盲区声明中说明哪些 KB 未命中。
4. **A+C 单路命中必须有内容验证** — 仅有语义信号没有关键词信号时，kb_doc_read 验证不可跳过。
5. **向量 ≠ 权威** — 向量是辅助手段，当 Agentic 判断与向量结果冲突时，以 Agentic 判断为准（重新读内容验证）。
