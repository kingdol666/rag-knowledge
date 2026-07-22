# Sub-KB Creation and Merge Guide

> **⭐ 阈值权威源（单一真相源）**：本文件定义的文档数阈值被 Ingest A8 和 Organize O3a/O3b **共同引用**。
> 修改此处阈值即同时更新两个 skill 的行为，避免不一致。
>
> | 阈值 | 值 | 用途 |
> |------|-----|------|
> | `SUB_KB_CHECK_THRESHOLD` | **≥6 篇** | 触发拆分/合并检查（Organize O3a 全库扫描时） |
> | `SUB_KB_AUTO_SPLIT_THRESHOLD` | **≥8 篇 且 ≥2 子域** | Ingest A8 单文档入库时自动创建子KB |
> | `SUB_KB_MIN_GROUP_SIZE` | **≥2 篇/子域** | 每个子领域最少文档数 |
> | `MERGE_OVERLAP_THRESHOLD` | **≥60%** | 跨KB 合并的内容重叠阈值 |

## ═══════════════════════════════════════════
# SIMILARITY DETECTION METHODOLOGY
## ═══════════════════════════════════════════

### Multi-Dimensional Similarity Scoring

When the organize skill says "overlap ≥60%" or "distinct sub-domain", it needs
a concrete, reproducible method to compute these from content alone. Use the
following **3-axis scoring protocol** for EVERY content comparison:

#### Axis 1: Tag Overlap (权重 0.3)
```
kb_tags_list() → 全局标签词表
kb_get_documents(kb_id) → 每篇文档的 tags 数组

tag_similarity(a, b) = |tags(a) ∩ tags(b)| / |tags(a) ∪ tags(b)|
```

- 0.0-0.2: 弱重叠（不同领域）
- 0.2-0.5: 中度重叠（可能同领域不同子领域）
- 0.5-1.0: 强重叠（高度相关，可能应合并）

#### Axis 2: Key Entity Overlap (权重 0.4)
从每篇文档 1000 chars 中提取**关键实体**（技术术语、设备名、工艺名、
材料名、参数名）。有两种提取策略：

**策略 A: 快速提取（默认，适用于 1-50 篇文档）**
```
读 1000 chars → 人工/Agent 识别关键实体 → 列表:
  doc_n_entities = ["pet", "双向拉伸", "薄膜", "拉伸比", "温度", ...]
```

**策略 B: 借图提取（当 KB 已有图谱时）**
```
kb_graph_document(doc_path, limit=30) → 图谱节点中提取实体标签
```

```
entity_similarity(kb_a, kb_b) = 
    |entities(a) ∩ entities(b)| / |entities(a) ∪ entities(b)|
```

- 0.0-0.15: 不同领域
- 0.15-0.40: 同大领域，不同子领域（可拆分）
- 0.40-0.70: 同子领域，粒度不同（可合并）
- 0.70-1.0: 高度重叠（几乎相同 → 强制合并）

#### Axis 3: Domain Classification (权重 0.3)
```
# 根据内容做三级分类
level_1: 大类（能源/化工/机械/IT/医疗/法律/财务/...）
level_2: 中类（电力/石油/高分子/汽车/软件/...）
level_3: 小类（汽轮机/双向拉伸/发动机/数据库/...）
```

```
domain_similarity(kb_a, kb_b):
  if l1不同 → 0.0（不同大类，不合并）
  if l1同但l2不同 → 0.2（大领域同，子领域不同 → 父KB）
  if l1同且l2同但l3不同 → 0.5（可合并为父，子KB保留）
  if l1同且l2同且l3同 → 0.8（应合并）
```

#### 综合相似度
```
total_similarity = 0.3 * tag_sim + 0.4 * entity_sim + 0.3 * domain_sim
```

| Score | Meaning |
|-------|---------|
| 0.0-0.25 | Different domain — keep separate |
| 0.25-0.40 | Same broad domain — could share parent KB |
| 0.40-0.60 | Related sub-domains — merge candidates |
| 0.60-0.80 | Highly related — merge recommended |
| 0.80-1.00 | Nearly identical — merge required |

---

### Sub-Domain Detection (for L4 split)

A "sub-domain" is defined by **all three** matching on an Axis 1-3 subset:

```
sub_domain_group = {docs where:
  entity_similarity(doc_a, doc_b) ≥ 0.4  AND
  domain_classification(doc_a).l2 == domain_classification(doc_b).l2
}
```

A KB has **distinct sub-domains** when its docs form ≥2 groups where:
- Intra-group similarity ≥ 0.4
- Inter-group similarity ≤ 0.25
- Each group ≥ 2 docs

---

## ═══════════════════════════════════════════
# DECISION MATRIX
## ═══════════════════════════════════════════

| Scenario | Axis 1 Tags | Axis 2 Entities | Axis 3 Domain | Total Sim | Action |
|----------|------------|----------------|---------------|-----------|--------|
| Unrelated KBs | <0.2 | <0.15 | l1不同 | <0.25 | **Keep separate** |
| Same domain, flat | 0.2-0.4 | 0.15-0.4 | l1同 l2同 l3不同 | 0.25-0.50 | **Create parent KB**, group as sub-KBs |
| Overlapping KBs | 0.4-0.6 | 0.40-0.7 | l1同 l2同 | 0.40-0.70 | **Merge** into one parent + sub-KBs |
| Near-identical KBs | 0.5+ | 0.7+ | l1同 l2同 l3同 | 0.60+ | **Merge flat** (no sub-KB needed) |
| Large KB, multi-domain | tags cluster | entity clusters | l2 split | — | **Split** into sub-KBs (L4) |

### Split + Merge Combo (the hard case)

When a KB is BOTH splittable AND mergeable with another KB:

```
1. Create parent KB for the merged set
2. Create sub-KBs for each distinct sub-domain from BOTH KBs
3. Move docs from both KBs into the correct sub-KBs
4. KB_update parent description
5. Delete the old KBs
```

---

## ═══════════════════════════════════════════
# CLASSIFICATION TREE (参考)
## ═══════════════════════════════════════════

L1大类 → L2中类 → L3小类示例:

| L1 能源 | L2 电力 | L3 汽轮机/锅炉/发电机/变电/输电 |
|         | L2 石油 | L3 勘探/钻井/炼油/管道/储运 |
|         | L2 新能源 | L3 光伏/风电/储能/氢能/核能 |
| L1 化工 | L2 高分子 | L3 PET/PVA/PE/PP/PS/拉伸/挤出/注塑 |
|         | L2 精细化工 | L3 催化剂/分离/合成/蒸馏 |
| L1 机械 | L2 动力机械 | L3 发动机/压缩机/泵/风机/ turbine |
|         | L2 加工机械 | L3 机床/模具/焊接/3D打印 |
| L1 信息 | L2 软件 | L3 架构/数据库/网络/安全/算法 |
|         | L2 硬件 | L3 芯片/电路/嵌入式/通信 |

分类树是参考，不是约束。新领域可以扩展。
分类的目的是**拉开差距**，不是精确归入预设类目。
当不确定时，取最接近的 L1/L2，在 L3 描述子领域特征即可。

---

## ═══════════════════════════════════════════
# SUB-KB NAMING CONVENTION
## ═══════════════════════════════════════════

```
{Parent-KB}-{SubDomain-Tag}
# Examples:
# Parent: "Thermal-Power"
# Sub-KBs: "Thermal-Power-Coal-Mill", "Thermal-Power-Turbine", "Thermal-Power-Boiler"
```

**Naming rules:**
- Sub-KB name starts with parent name for automatic grouping in UI
- Use Camel-Case-with-Hyphens (not underscores, not spaces)
- Max 3 segments: {Parent}-{SubType} (no deeper nesting)
- Description must be unique — not copy-pasted from parent

---

## ═══════════════════════════════════════════
# MERGE PROCEDURE
## ═══════════════════════════════════════════

```
# Case A: Merge + Sub-KB (KB A and KB B share parent domain but have distinct sub-domains)
1. Create parent KB: kb_create(name="<Parent>", description="<merged domains>")
2. kb_update(kb_id=a_id, parent_id=parent_id)
3. kb_update(kb_id=b_id, parent_id=parent_id)
4. kb_update(kb_id=parent_id, description="Sub-KBs: [A-name], [B-name]...")
5. kb_batch_index(parent_id, force=true)
6. kb_graph_build(parent_id, force=true)

# Case B: Merge Flat (KB A and KB B are nearly identical — no sub-KB needed)
target = kbA (name + description kept)
source = kbB (all docs moved, then deleted)

for doc in source_kb.docs:
    kb_doc_move(doc.doc_path, target_kb_id)
kb_delete(source_kb_id)
kb_batch_index(target_kb_id, force=true)
kb_graph_build(target_kb_id, force=true)
kb_update(kb_id=target_kb_id, description="<updated after merge>")

# Case C: Merge+Split Combo (both KBs splittable AND mergeable)
# → see Decision Matrix: Split + Merge Combo above
```

---

## ═══════════════════════════════════════════
# SPLIT PROCEDURE
## ═══════════════════════════════════════════

```
# Parent KB has ≥2 sub-domains, ≥2 docs each
1. for each sub_domain:
    kb_create(name="<Parent>-<Sub>", description="<sub-domain>$domain>", parent_id=parent_kb_id)
    for doc_path in sub_domain.docs:
        kb_doc_move(doc_path, sub_kb_id)
2. kb_update(kb_id=parent_kb_id, description="<updated with sub-KB list>")
3. for each sub_kb: kb_batch_index(kb_id=sub_kb_id, force=true)
4. One remaining doc per sub_domain or "general" remains in parent
```

---

## ═══════════════════════════════════════════
# VERIFICATION
## ═══════════════════════════════════════════

```
kb_list()                              → sub-KBs visible
kb_get_documents(parent_kb_id)         → docs moved OUT
kb_get_documents(sub_kb_id)            → docs moved IN
fs_get_tree(max_depth=3)               → hierarchy visible
kb_search_stats(kb_id)                 → vector index OK
kb_graph_kb_overview(kb_id)            → graph index OK
```

---

## NEVER

- Never split a KB where all docs belong to the same sub-domain (Intra-group sim < 0.4)
- Never merge KBs where total_similarity < 0.25
- Never create sub-KB for a single doc (needs ≥2)
- Never keep empty parent KB after moving all docs (delete it)
- Never guess domain from filename — must read content
- Never create duplicate sub-KBs for the same sub-domain
- Never decide split/merge without computing at least 2 of 3 similarity axes
