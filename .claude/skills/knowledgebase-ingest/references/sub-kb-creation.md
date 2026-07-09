# Sub-KB Creation Procedure

## Trigger
Parent KB has **≥8 docs** spanning **≥2 distinct sub-domains** (classified by content, not filename). Each sub-domain needs ≥2 docs.

## Steps

### 1. Assess
Read 500 chars per doc via `kb_doc_read`. Classify sub-domain from content. Count distinct sub-domains.

### 2. Create Sub-KBs
```
kb_create(
    name="<Parent>-<SubDomain>",        # e.g. "Thermal-Power-Coal-Mill"
    description="<focused, 2-3 sentences>",
    parent_id=parent_kb.kb_id
)
```

### 3. Move Documents
```
for each doc in sub-domain:
    kb_doc_move(doc.doc_path, sub_kb.kb_id)
```

### 4. Update Parent Description
```
kb_update(kb_id=parent_kb.kb_id,
    description="<updated>. Sub-KBs: [Sub1], [Sub2], [Sub3]")
```

### 5. Reindex
```
kb_batch_index(kb_id=sub_kb.kb_id, force=true)
```

### 6. Verify
```
kb_list()                          # sub-KBs appear
kb_get_documents(parent_kb_id)     # docs moved OUT
kb_get_documents(sub_kb_id)        # docs moved IN
fs_get_tree(include_files=False, max_depth=3)  # hierarchy visible
```
