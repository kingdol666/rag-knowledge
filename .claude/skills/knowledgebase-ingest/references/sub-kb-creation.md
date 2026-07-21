# Sub-KB Creation and Management Guide

## When to Create Sub-KBs

A parent KB should have sub-KBs when:
- It has **≥6 docs** across **≥2 distinct content sub-domains** (based on content, not name)
- Each sub-domain group has **≥2 docs** minimum

## When to Merge KBs Into One Parent

Two or more KBs should merge when:
- Their **content domains overlap ≥60%** (same topic, different granularity)
- They are **hierarchically related** (e.g. "PET-Film" and "PET-Stretching" → "PET-Process" parent with sub-KBs)
- They cover **different aspects of the same domain** (splitting by format/year/author ≠ valid sub-domains)

## Sub-KB Naming Convention

```
{Parent-KB}-{SubDomain-Tag}
# Examples:
# Parent: "Thermal-Power"
# Sub-KBs: "Thermal-Power-Coal-Mill", "Thermal-Power-Turbine", "Thermal-Power-Boiler"
```

Descriptions must be unique and precise — not copy-pasted from parent.

## Creation Steps

```
kb_create(
    name="<Parent>-<SubDomain>",
    description="<2-3 sentences: what THIS sub-domain covers>",
    parent_id=parent_kb_id
)
```

## Document Movement

Move docs to correct sub-KB:
```
kb_doc_move(doc_path, sub_kb_id)
```

After ALL moves complete:
```
kb_batch_index(sub_kb_id, force=true)     # reindex sub-KB docs
kb_batch_index(parent_kb_id, force=true)  # update parent index
kb_graph_build(parent_kb_id, force=true)  # rebuild graph links
```

## Parent Description Update

```
kb_update(
    kb_id=parent_kb_id,
    description="<updated>. Sub-KBs: [Sub1], [Sub2]..."
)
```

## Verification

```
kb_list()                              → sub-KBs visible
kb_get_documents(parent_kb_id)         → docs moved OUT
kb_get_documents(sub_kb_id)            → docs moved IN
fs_get_tree(max_depth=3)               → hierarchy visible
```

## Cross-KB Merge Procedure

```
# Step 1: Move all docs from source to target
for doc in source_kb.docs:
    kb_doc_move(doc.doc_path, target_kb_id)

# Step 2: Update target description to reflect union
kb_update(kb_id=target_kb_id, description="Merged from: [Source] + ...")

# Step 3: Delete empty source KB
kb_delete(source_kb_id)

# Step 4: Reindex + rebuild
kb_batch_index(target_kb_id, force=true)
kb_graph_build(target_kb_id, force=true)
```

## NEVER

- Create sub-KB for a single doc (needs ≥2 docs per sub-domain)
- Create sub-KB when parent has <6 docs total
- Merge KBs with <60% domain overlap
- Merge without checking content first
- Keep empty parent after moving everything out (delete it)
- Create duplicate sub-KBs for the same sub-domain
