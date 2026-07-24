# Cross-KB Synthesis — 跨知识库经验综合

> 当一个经验横跨多个 KB 的领域（如"RAG 检索优化"同时涉及 AI-ML-Research
> 和 Materials-ML），需要决定归属、去重、关联策略。

## Table of Contents
- [何时发生跨库综合](#何时发生跨库综合)
- [归属决策](#归属决策经验放哪个kb)
- [跨库去重](#跨库去重)
- [跨库检索验证](#跨库检索验证)
- [关联维护](#关联维护)

---

## 何时发生跨库综合

| 场景 | 示例 |
|------|------|
| 用户问题涉及多 KB 文档 | "RAG 在材料科学的应用" → AI-ML-Research + Materials-Science |
| 冥想发现的问题簇横跨多领域 | "向量索引碎片" → 所有有索引的 KB |
| 文档移动后经验需重新归属 | 文档从 KB-A 移到 KB-B，经验跟随 |

---

## 归属决策：经验放哪个 KB？

```
判断逻辑（优先级从高到低）：

1. 用户的显式归属（"放到 AI-ML-Research"）→ 直接用
2. related_docs 的多数归属 → 经验放文档最多的那个 KB
3. 核心领域归属 → 问题最核心的领域词匹配的 KB
4. 都不明确 → 放父级/通用 KB，tags 标明关联领域
```

### 决策树

```
该经验涉及哪些 KB？
  ├── 仅1个 KB → 放该 KB（简单）
  ├── 2-3个 KB，有主次 → 放主领域 KB，tags 含次要领域
  ├── 2-3个 KB，无主次 → 放相关文档最多的 KB
  └── 全库通用（如"ragctl 使用"）→ 放通用 KB 或每个 KB 各放一份
```

> ⚠️ **不要在多个 KB 各放一份完整副本**——会制造维护噩梦（更新时漏改）。
> 除非是"全库通用且各库独立检索"的场景。

---

## 跨库去重

创建前先跨库搜索：

```
experience_search_global(query="<核心关键词>", top_k=10)
  → 看是否已有跨库经验覆盖

已有覆盖：
  - 同 KB 已有相似 → experience_update（见 crud-and-migration.md）
  - 跨 KB 已有相似（别库）→ 评估是否需要本库独立副本：
    * 本库有独特上下文/文档 → 允许新建，tags 标关联
    * 纯重复 → 不新建，可在本库建一条"指针经验"（轻量，指向别库 exp_id）
```

### 指针经验（跨库引用）

当一个经验已在别库高质量存在，本库只需索引不需副本：

```yaml
title: "[跨库引用] 向量索引碎片整理（详见 AI-ML-Research）"
scenario: "cross-kb-ref-index-dedup"
category: tip
problem: "本库也可能遇到向量索引碎片化，完整经验见 AI-ML-Research/exp-87993d41a050"
solution: "参见 AI-ML-Research 的 exp-87993d41a050，核心步骤：kb_reindex(force=true)"
key_lessons:
  - "向量索引碎片问题通用解法见 AI-ML-Research/exp-87993d41a050"
tags: ["跨库引用", "索引", "去重"]
related_docs: []
```

> 指针经验轻量，避免内容重复，但保证本库检索能命中并指引到完整经验。

---

## 跨库检索验证

归纳跨库经验时，验证答案来源覆盖所有相关 KB：

```
对每个相关 KB：
  kb_search_two_stage(query, kb_id=<KB>) → 收集命中
  kb_doc_read(kb_id, top_doc) → 提取关键结论

合并多 KB 命中 → 确认 solution 不偏废任一 KB 的视角
```

---

## 关联维护

跨库经验需维护标签关联，便于跨库发现：

```
tags 中包含所有相关领域词：
  ["rag", "检索优化", "ai-ml", "materials-ml", "跨库"]

这样 experience_search_global 能通过标签跨库召回。
```

跨库经验文档移动时（见 [crud-and-migration.md](crud-and-migration.md)），
需重新评估归属是否仍合理。
