# Organize Execution Details — L1-L7 Fix Operations

> Referenced by knowledgebase-organize O4. Read when executing fixes.

## L1 Description Repair (metadata · zero risk)

```
for each doc with desc_quality ≠ OK:
    kb_doc_update_meta(kb_id, doc_path, description=<新描述>)
for each KB with generic/empty description:
    kb_update(kb_id, description=<新描述>)
```

**Description quality standard** (4 elements): ① core topic (from 1000 chars) ② data type (paper/report/standard/manual) ③ tech domain/sub-domain ④ key entities/equipment/process.

## L2 Tag Hygiene (metadata · zero risk)

> **Blacklist authority**: full T1 blacklist in [tag-quality-rules.md](../../knowledgebase-ingest/references/tag-quality-rules.md). Execute against that source.

```
# T1 blacklist removal (section headings, test tags, meta tags, format-illegal)
for each doc:
    tags = doc.tags
    cleaned = filter(tags, not matches T1 blacklist)
    kb_doc_update_tags(kb_id, doc_path, tags=cleaned)

# T2 synonym merge + normalization (see tag-quality-rules.md §T2 full map)
# T3 count fix (2-5 tags/doc)
for each doc with tags < 2:
    kb_doc_update_tags(kb_id, doc_path, tags=[补全 from O2 suggested_tags])
```

## L3 Document Reclassification (move · needs verify)

```
for each doc with kb_alignment = MISMATCH:
    kb_doc_move(doc_path, correct_kb_id)
    kb_index_document(kb_id=correct_kb_id, doc_path=<新路径>)
```

## L4 Sub-KB Split (structure · needs user confirm)

```
# 1. Show split plan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 KB 拆分建议: <KB名称> (<N> 篇)
  ┌─────────────┬────────┬──────────────┐
  │ 子KB        │ 文档数 │ 内容子领域    │
  ├─────────────┼────────┼──────────────┤
  │ <Sub-KB-1>  │ <N>    │ <领域>       │
  │ [根KB保留]  │ <N>    │ 跨领域/通用   │
  └─────────────┴────────┴──────────────┘
  是否执行？[Y/n/修改]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 2. After user confirm
for each sub_domain:
    kb_create(name="<KB>-<Sub>", description="...", parent_id=parent_kb_id)
    for doc_path in sub_domain.docs:
        kb_doc_move(doc_path, sub_kb_id)

# 3. Update parent KB description
kb_update(kb_id=parent_kb_id, description="<更新>。子KB：[Sub1], [Sub2]...")

# 4. Rebuild index
for each new sub_kb:
    kb_batch_index(kb_id=sub_kb_id, force=true)
```

## L5 Cross-KB Merge (structure · needs user confirm)

```
# Show merge plan → user confirm → execute
target_kb = kbA (keep);  source_kb = kbB (merged in)

# If kB docs form independent sub-domain → create sub-KB
target_sub = kb_create(name="<target>-<sub>", parent_id=target_kb_id)
for doc in source_kb.docs:
    kb_doc_move(doc.doc_path, target_sub_kb_id)
# Else: direct merge
for doc in source_kb.docs:
    kb_doc_move(doc.doc_path, target_kb_id)

kb_delete(source_kb_id)
kb_batch_index(target_kb_id, force=true)
kb_graph_build(target_kb_id, force=true)
```

## L6 KB Hierarchy Restructure (structure · needs user confirm)

```
# flat → create parent KB
kb_create(name="<父-KB>", description="...")
for each sub_kb: kb_update(parent_id=new_parent_kb_id)

# rename / reposition
kb_update(kb_id=<id>, name="<新名称>", description="<新描述>")

# delete empty/test KB
kb_delete(test_kb_id)
```

## L7 Index + Graph Rebuild (infrastructure)

```
# 7a. Vector index coverage
for each kb:
    docs = kb_get_documents(kb_id)
    missing = [d for d in docs if not d.vector_index]
    if missing: kb_batch_index(kb_id, [d.path for d in missing], force=true)

# 7b. Knowledge graph per KB
for each kb: kb_graph_build(kb_id, force=true)

# 7c. Global graph (if KB count > 5 and all have docs)
kb_graph_build(kb_id="", force=true)
```

## O5 Per-Layer Verification

| Layer | Verify method |
|-------|--------------|
| L1 desc | `kb_doc_read` 500 chars confirm new desc |
| L2 tags | `kb_get_documents` check tags array |
| L3 reclassify | `kb_get_documents(source)` left, `(target)` arrived |
| L4 sub-KB | `kb_list()` sub-KB visible, `kb_get_documents(sub_kb)` correct |
| L5 merge | source KB deleted, target KB + sub-KB docs correct |
| L6 hierarchy | `fs_get_tree(max_depth=3)` correct |
| L7 index | `kb_search_stats(kb_id)` collection + chunks ≥ 1 |

## O5b Three-Way Metadata Consistency (mandatory after L3/L4/L5/L6)

> **MCP constraint**: Archival agent cannot read raw `.tree-fs.json`/`.knowledge-base.yml` directly. Use MCP tool cross-referencing instead (same approach as [knowledgebase-verify V1](../../knowledgebase-verify/SKILL.md)).

```
for each affected KB:
    docs = kb_get_documents(kb_id)          # YAML-layer metadata (name, path, tags, vector_index, graph_index)
    tree = fs_get_children(parent_id)       # tree-layer (disk + .tree-fs.json synced by backend)
    for each doc in docs:
        # Cross-reference three layers via MCP (not raw file reads):
        in_yaml   = doc in docs             # .knowledge-base.yml layer
        in_treefs = any entry in tree matches doc.path   # .tree-fs.json + disk layer
        readable  = kb_doc_read(doc.path) succeeds       # disk content layer
        # UUID sync: doc.vector_index.collection should contain kb_id (not stale name)
        # Random 20% content readback: kb_doc_read → correct content
```

**Repair rules**:
- Missing on disk → `kb_doc_delete` (ghost entry cleanup)
- Missing in treefs → `kb_doc_create` (re-register)
- Missing in YAML → `kb_doc_update_meta` (fill metadata)
- UUID divergence → clean stale path residue after `kb_doc_move`

## O7 Custom Compliance Strategies

| Strategy | Meaning | Layer |
|----------|---------|-------|
| `strict_descriptions` | Every doc 4-element desc | L1 |
| `clean_tags` | No blacklist + normalized + ≥2 tags | L2 |
| `align_docs` | All docs in correct KB | L3 |
| `split_kbs` | ≥6 docs + ≥2 sub-domains → split | L4 |
| `merge_kbs` | Overlap → merge | L5 |
| `hierarchy` | Complete hierarchy tree | L6 |
| `full_index` | Vector + graph coverage | L7 |

Default: all execute. User says "只修描述和标签" → only L1+L2+L7.
