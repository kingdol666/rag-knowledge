# Sub-KB Creation and Merge Guide

> **⭐ Authoritative threshold source (single source of truth)**: the document-count thresholds defined in this file are **jointly referenced** by Ingest A8 and Organize O3a/O3b.
> Changing a threshold here updates both skills' behavior at once, avoiding divergence.
>
> | Threshold | Value | Purpose |
> |------|-----|------|
> | `SUB_KB_CHECK_THRESHOLD` | **≥6 docs** | Triggers the split/merge check (Organize O3a whole-library scan) |
> | `SUB_KB_AUTO_SPLIT_THRESHOLD` | **≥8 docs and ≥2 sub-domains** | Auto-creates a sub-KB during Ingest A8 single-document ingest |
> | `SUB_KB_MIN_GROUP_SIZE` | **≥2 docs/sub-domain** | Minimum documents per sub-domain |
> | `MERGE_OVERLAP_THRESHOLD` | **≥60%** | Content-overlap threshold for cross-KB merges |

## ═══════════════════════════════════════════
# SIMILARITY DETECTION METHODOLOGY
## ═══════════════════════════════════════════

### Multi-Dimensional Similarity Scoring

When the organize skill says "overlap ≥60%" or "distinct sub-domain", it needs
a concrete, reproducible method to compute these from content alone. Use the
following **3-axis scoring protocol** for EVERY content comparison:

#### Axis 1: Tag Overlap (weight 0.3)
```
kb_tags_list() → global tag vocabulary
kb_get_documents(kb_id) → each document's tags array

tag_similarity(a, b) = |tags(a) ∩ tags(b)| / |tags(a) ∪ tags(b)|
```

- 0.0-0.2: weak overlap (different domains)
- 0.2-0.5: moderate overlap (possibly same domain, different sub-domains)
- 0.5-1.0: strong overlap (highly related, may warrant a merge)

#### Axis 2: Key Entity Overlap (weight 0.4)
Extract **key entities** (technical terms, equipment names, process names,
material names, parameter names) from 1000 chars of each document. Two extraction strategies:

**Strategy A: quick extraction (default; for 1-50 documents)**
```
Read 1000 chars → human/Agent identifies key entities → list:
  doc_n_entities = ["pet", "双向拉伸", "薄膜", "拉伸比", "温度", ...]
```

**Strategy B: graph-assisted extraction (when the KB already has a graph)**
```
kb_graph_document(doc_path, limit=30) → extract entity labels from graph nodes
```

```
entity_similarity(kb_a, kb_b) = 
    |entities(a) ∩ entities(b)| / |entities(a) ∪ entities(b)|
```

- 0.0-0.15: different domains
- 0.15-0.40: same broad domain, different sub-domains (splittable)
- 0.40-0.70: same sub-domain, different granularity (mergeable)
- 0.70-1.0: highly overlapping (nearly identical → merge required)

#### Axis 3: Domain Classification (weight 0.3)
```
# Three-level classification from content
level_1: major class (energy/chemicals/machinery/IT/medical/legal/finance/...)
level_2: middle class (electric power/petroleum/polymers/automotive/software/...)
level_3: minor class (steam turbine/biaxial stretching/engine/database/...)
```

```
domain_similarity(kb_a, kb_b):
  if l1 differs → 0.0 (different major classes; do not merge)
  if l1 same but l2 differs → 0.2 (same broad domain, different sub-domains → parent KB)
  if l1 and l2 same but l3 differs → 0.5 (may merge into parent; sub-KBs kept)
  if l1, l2 and l3 all same → 0.8 (should merge)
```

#### Combined similarity
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
| Unrelated KBs | <0.2 | <0.15 | l1 differs | <0.25 | **Keep separate** |
| Same domain, flat | 0.2-0.4 | 0.15-0.4 | l1 same, l2 same, l3 differs | 0.25-0.50 | **Create parent KB**, group as sub-KBs |
| Overlapping KBs | 0.4-0.6 | 0.40-0.7 | l1 same, l2 same | 0.40-0.70 | **Merge** into one parent + sub-KBs |
| Near-identical KBs | 0.5+ | 0.7+ | l1 same, l2 same, l3 same | 0.60+ | **Merge flat** (no sub-KB needed) |
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
# CLASSIFICATION TREE (reference)
## ═══════════════════════════════════════════

L1 major class → L2 middle class → L3 minor class examples:

| L1 Energy | L2 Electric Power | L3 Steam turbine/boiler/generator/substation/transmission |
|         | L2 Petroleum | L3 Exploration/drilling/refining/pipeline/storage & transport |
|         | L2 New Energy | L3 Solar PV/wind/energy storage/hydrogen/nuclear |
| L1 Chemicals | L2 Polymers | L3 PET/PVA/PE/PP/PS/stretching/extrusion/injection molding |
|         | L2 Fine Chemicals | L3 Catalysts/separation/synthesis/distillation |
| L1 Machinery | L2 Power Machinery | L3 Engine/compressor/pump/fan/turbine |
|         | L2 Processing Machinery | L3 Machine tools/molds/welding/3D printing |
| L1 Information | L2 Software | L3 Architecture/database/networking/security/algorithms |
|         | L2 Hardware | L3 Chips/circuits/embedded/communications |

The classification tree is a reference, not a constraint; new domains may extend it.
The purpose of classification is to **widen the separation**, not to slot items precisely into preset categories.
When unsure, take the closest L1/L2 and describe the sub-domain characteristics at L3.

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
