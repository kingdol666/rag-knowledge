---
name: knowledgebase-search-enterprise
description: >
  企业级多策略查询驱动检索。从 knowledgebase-search 自动升级：
  向量+标签+描述三道门产出确认 P0/P1 文档来自 <2 个 KB，
  或用户明确要求 "全库搜索" / "全面" / "跨库"。
  并行 3 路（向量 + 标签语义 + BM25）召回 + 查询改写，balance_kbs 防大库主导，
  文档级去重，硬阈值过滤，交叉验证定级，内容裁决，融合呈现。
  Triggered by: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观,
  cross-KB, all KBs, enterprise search, 全局搜索, 全面的, thorough search, comprehensive.
---

# Enterprise Multi-Strategy Retrieval — 企业级多策略精炼检索

**⭐ MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API。MCP 不可用时才可向用户报告。

> **升级触发**：knowledgebase-search Step 5 发现确认 P0/P1 来自 <2 个 KB（跨库盲点），或用户明确要求全库/跨库/全面检索。

---

## 思维框架：什么时候用 Enterprise？ ⭐

```
用户查询
  ├── 标准 KB 搜索（指定了某个 KB）→ knowledgebase-search ✅
  ├── 全库搜索（不指定 KB）+ 普通查询 → knowledgebase-search ✅（Step 1 自动选库）
  └── 全库搜索 + 查询命中 <2 个 KB → knowledgebase-search-enterprise ⬆️
      或：用户强调"全库/跨库/全面/所有 KB" → 直接升级
```

> Enterprise 比标准 QDCVR 重 3 倍（3 路并行召回），不要默认使用。先跑 QDCVR，不满足再升级。

---

## Phase 0 — 查询改写（继承 QDCVR Step 0）

```
原始查询 → 意图分类 + 核心实体提取 → 生成检索友好 query
- 向量/BM25 用：声明句 + 关键词组合
- 标签路径用：领域概念词
- 多概念查询 → 拆子查询并行（对比型必备）
```
故障/运维型：先 `experience_search_global(query, top_k=5)`。

## Phase 1 — 并行 3 路召回（全部 balance_kbs=True 防大库主导）

```
# Path A — 向量（广网，两阶段精排）
kb_search_two_stage(
    Phase0改写query, kb_id="",
    stage1_top_k=30, stage2_top_k=10,
    score_threshold=0.30,         # 企业级放宽召回，Phase 3 再严筛
    balance_kbs=True              # ⭐ 必开
)

# Path B — 标签（语义概念匹配）
kb_tags_list()
→ 对查询核心实体，语义匹配 top 3-5 标签
→ kb_doc_get_by_tag(tag, kb_id="") 每标签取文档

# Path C — BM25 关键词（纯关键词，stage2 关闭）
kb_search_two_stage(
    Phase0改写query, kb_id="",
    stage1_top_k=25, stage2_top_k=0,   # 仅用 stage1 候选
    balance_kbs=True
)
```
**可选 Path D — 经验库**（故障/运维型）：`experience_search_global(query, top_k=5)` + `experience_search_vector(kb_id, query, top_k=5)`。

### 路径失败处理
- Path A 向量返回 0 条 → 降低 score_threshold 到 0.25 重试
- Path B 标签无匹配 → 用 `kb_search` 关键词检索标签描述
- Path C BM25 无结果 → 分词后核心词检索

## Phase 2 — 交叉验证 + 文档级去重

合并所有路径结果，**按 doc_path 去重**（同文档只留最高分 chunk，记录命中路径数）：

| 命中路径模式 | 候选置信度 |
|---|---|
| A + B + C 三路 | **P0 候选**（多路共识）|
| A + B 或 B + C 两路 | **P0 候选**（语义+关键词双重确认）|
| A + C 两路（向量+BM25）| **P1 候选** |
| 仅单路 | **P1/P2 候选**（需 Phase 3 内容验证）|

**硬阈值预过滤**：任一 chunk 向量 score < 0.30 → 丢弃（除非是标签路径命中且描述强相关）。
**短内容降级**：chunk <200 chars 标记 ⚠️，候选置信度降一级。

## Phase 3 — 内容裁决（独立打分，定最终去留）

对每个去重后候选（≤12 篇）：
```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```
**0-8 打分**（同 QDCVR Step 3）：

| 维度 | 分 | 判据 |
|---|---|---|
| 主题相关 (0-3) | 3=正文围绕主体 / 2=涉及 / 1=边缘 / 0=无关 |
| 场景匹配 (0-3) | 3=直接解决问题 / 2=可迁移 / 1=泛泛 / 0=答非所问 |
| 答案证据 (0-2) | 2=具体数据步骤结论 / 1=方向性 / 0=空泛 |

| 内容分 | 终判 |
|---|---|
| 6-8 | **P0** — 纳入答案 |
| 5 | **P1** — 补充用 |
| ≤4 | **丢弃** |

**内容分 > 一切**。三路命中但内容 ≤4 → 丢（多路可能共同跑偏）。

## Phase 4 — 图谱扩展（P0 <3 或需跨库桥梁时）

```
kb_graph_document_related(doc_path)     # 已确认 P0 的相关文档
kb_graph_central_documents(kb_id)       # hub/综述文档
kb_graph_cross_kb_documents(min_kbs=2)  # 跨库桥梁文档
```
新文档进入 Phase 3 内容裁决。**仅在 P0 不足或查询显式跨库时启用**，避免图谱噪声。

## Phase 5 — 融合呈现（强制规范）

```
## 搜索路径
A 向量 + B 标签 + C BM25（+ D 经验，如适用）→ 去重后 N 篇 → 内容裁决后 P0:x / P1:y

## 答案
<基于 P0 文档综合，引用具体数据/结论；P1 作为补充>

## 来源（按置信度+路径共识排序）
- [P0] [A+B+C] <文档名> @ <KB/路径> — <相关理由>
- [P0] [A+B]   <文档名> @ <KB/路径> — <相关理由>
- [P1] [A]     <文档名> @ <KB/路径> — <补充什么>

## 置信度
高/中/低 — <理由，如"3 篇 P0 跨 2 库一致"或"仅单路命中 1 篇">

## 盲点（跨库视角）
- <涉及但全库未覆盖的子领域>
- <某库可能有相关内容但本次未命中（建议手工复查）>
- <争议/时效/需确认点>
```

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 直接跑 enterprise 不做 QDCVR 先行 | 3 倍开销 | 默认 QDCVR，不够才升级 |
| balance_kbs=False 全库搜索 | 大库主导结果 | 全程 `balance_kbs=True` |
| Phase 3 跳过 doc_read | 内容分靠猜 | 读 3000 chars 正文打分 |
| 三路共同命中也跳过验证 | 共同跑偏是可能的 | 内容 ≤4 即使三路也丢 |
| 图谱扩展无节制 | 引入大量噪声 | 仅 P0 <3 或显式跨库时启用 |

## 规则速查
1. **Phase 0 必做**——原始查询不直接进三路召回
2. **balance_kbs=True 全程**——防大库主导
3. **Phase 2 文档级去重**——消灭冗余
4. **硬阈值 0.30 预过滤**——跨域低分截断
5. **Phase 3 内容分定去留**——内容 ≤4 即便三路共识也丢
6. **图谱扩展有节制**——仅 P0 不足或显式跨库时启用
7. **诚实盲点**——跨库视角的盲点尤其要声明
