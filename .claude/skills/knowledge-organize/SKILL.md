---
name: knowledge-organize
description: >
  Full collection restructuring engine. O1→O8 workflow: survey every KB,
  read document content to classify true domains, categorize KBs (proper/
  test/empty/overlapping/misclassified), execute merges/moves/
  renames/descriptions, verify each change, produce structured report,
  and split oversized documents into smaller logical chunks.
  Invoked by Archival when the collection needs deep reorganization.
---

# Knowledge Organize — Full Collection Restructuring

Invoked by Archival when the scenario is diagnosed as **Organize**
(全盘整理, 整理, 清洗, 审计, audit, restructure, cleanup, reorganize).

This is the deep reorganization engine. Survey every KB, read content,
and restructure so the collection reflects the truth.

## O1 — Full Survey (KB + Experience)

```
kb_list()         → all KBs with names, descriptions, document counts
kb_tags_list()    → all registered tags
fs_get_tree(include_files=True, max_depth=0)  → full structural view
```

### O1-E — Experience Survey

For each KB in `kb_list()`:
```
experience_list(kb_id)          → list all experiences
experience_summary(kb_id)       → statistics (total, by_category, by_severity)
```
Check for orphaned `{KB_PATH}/experience/` dirs whose KB was deleted.

## O2 — Evaluate Every KB

For each KB, evaluate these metrics:

| Metric | How to evaluate | Red flag |
|--------|----------------|----------|
| Name quality | Meaningful? Describes the domain? | Gibberish: "213", "333333", "test" |
| Description quality | Does it describe the domain? | Empty, "test", meaningless |
| Document count | How many docs inside? | 0 = stale → ask user or delete |
| **Experience health** | Are exps consistent with KB domain? | scenario=test, empty title, 0 rating |
| Domain match | Do the docs match the KB name? | KB says "AI" but doc content is energy |
| Overlap | Same content in another KB? | Duplicate domain coverage |
| Vector coverage | What % docs have vector_index set? | <50% → prompt reindex |
| **Oversized docs** | `file_size` per doc | >50KB or >2000 lines → flag for O8 smart split |

For each KB with documents:
- Read 1-2 documents: `kb_doc_read(kb_id, <doc>, max_chars=300)`
- Classify the KB's TRUE domain based on content evidence, not its name.

## O3 — Categorize Every KB

| Category | Characteristics | Action |
|----------|----------------|--------|
| **Proper domain KB** | Meaningful name + description + matching content | Keep. May offer rename/rediscribe. Auto-index missing docs. |
| **Test/scratch** | Gibberish name, meaningless description | Merge content (if any) into an existing KB, delete shell |
| **Empty stale** | 0 documents | Ask user → delete or keep as placeholder |
| **Domain overlap** | Same domain as another KB | Merge into the better-named KB |
| **Misclassified** | KB name says X, content is Y | Move docs to correct KB, rename or delete shell |

### O3-E — Experience Alignment

For each experience found:

| Condition | Action |
|-----------|--------|
| scenario=test or title is test gibberish | Delete (test residue) |
| rating=0, key_lessons empty, applied=0 | Flag as draft → ask user |
| related_docs paths stale after KB rename | Update via experience_update() |

## O4 — Execute

### Merge A into B
```
docs = kb_get_documents(A.kb_id)
for each doc:
    kb_doc_move(doc.doc_path, B.kb_id)
# Also migrate experiences (if any)
exps_resp = experience_list(kb_id=A.kb_id)
for exp in exps_resp.experiences:
    exp_full = experience_read(kb_id=A.kb_id, exp_id=exp.id)
    exp_data = exp_full.experience
    experience_create(
        kb_id=B.kb_id, title=exp_data.title, scenario=exp_data.scenario,
        category=exp_data.category, problem=exp_data.problem,
        solution=exp_data.solution, result=exp_data.result,
        key_lessons=exp_data.key_lessons, tags=exp_data.tags,
        severity=exp_data.severity, related_docs=exp_data.related_docs,
        prerequisites=exp_data.prerequisites, metrics=exp_data.metrics,
    )
    experience_delete(kb_id=A.kb_id, exp_id=exp.id)
kb_delete(A.kb_id)    # only AFTER all docs moved
```

### Move misclassified doc
```
kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id="target-UUID")
```
**After moving**: check if any experience in the target KB has `related_docs`
that reference the doc's old path. If so, update:
```
experience_update(target_kb_id, exp_id, related_docs=["NewKB/new-path.md"])
```

### Rename/rediscribe KB
```
kb_update(kb_id, name="New-Name", description="<1-3 sentences>")
```
**Bug**: path won't refresh. Use UUID for subsequent calls.
**Experience impact**: related_docs in experiences still reference OLD path.
After renaming, update all affected experiences:
```
exps = experience_list(kb_id)
for exp in exps.experiences:
    old_related = exp.related_docs
    if any(doc.startswith("Old-Name/") for doc in old_related):
        new_related = [doc.replace("Old-Name/", "New-Name/") for doc in old_related]
        experience_update(kb_id, exp.id, related_docs=new_related)
```

### Index documents (if vector coverage < 100%)
```
# For each KB with unindexed docs:
kb_get_documents(kb_id) → filter for doc_paths where vector_index is missing
kb_batch_index(kb_id, unindexed_doc_paths)
```

### Rename/rediscribe
```
kb_update(kb_id, name="New-Name", description="<1-3 sentences>")
```
**Bug**: path won't refresh. Use UUID for subsequent calls.

### Delete empty KBs (confirm first unless Module Mode)
```
kb_delete(kb_id)
```

### Delete test documents
```
kb_doc_delete(kb_id, doc_path)
kb_doc_batch_delete(kb_id, ["KB/doc.md"])    # ⚠️ MUST use full paths
```

### Fix document descriptions (read content first, never guess)
```
kb_doc_update_meta(kb_id, doc_path, description="<1-2 sentences from content>")
```

### Fix KB descriptions
```
kb_update(kb_id, description="<1-3 sentences: domain + content types + language>")
```

### Apply missing tags
```
kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])
```

## O5 — Verify Each Change

After each mutation (move, delete, merge, rename, update), immediately verify:
- **For moves**: `kb_get_documents(target_kb_id)` → confirm doc arrived
- **For deletes**: `kb_get_documents(kb_id)` or `fs_get_tree()` → confirm removal
- **For renames**: `kb_list()` → check new name reflects
- **For merges**: verify source KB is gone + target KB has combined docs
- **For reindex**: `kb_search_stats(kb_id)` → check chunk_count increased
- **For experience updates**: `experience_read(kb_id, exp_id)` → verify content
- **For .tree-fs.json integrity**: `fs_get_tree()` → confirm JSON parseable

## O6 — Orphan Cleanup

Check for orphaned experience directories:

1. List all directories under the storage root (fs_get_tree)
2. Cross-reference against KB paths from kb_list()
3. For any experience/ directory whose KB no longer exists:
   - List its experiences: read .experience-index.yml
   - Report to the user and delete if confirmed

## O7 — Integrity Report

Generate a structured summary with a **quantitative scorecard**:

```
## Collection Health Report

### Scorecard
  ├── Tag Coverage:    X/30  (tagged docs / total docs × 30)
  ├── Description Quality: X/25  (good descriptions / total × 25)
  ├── Uniqueness:      X/25  (unique docs / total × 25)
  └── KB Structure:    X/20  (proper-named KBs / total × 20)
  ───────────────────────
  TOTAL: X/100

### Overview
- Total KBs: N, Total Docs: N
- Unique documents: N (duplicates: N)
- Total Tags: N, Orphan tags: N

### Actions Completed
- KBs Deleted: N (list)
- KBs Merged: N (list)
- Documents Moved: N
- Descriptions Updated: N
- Tags Applied: N
### Remaining Issues
- Orphan tags (no tool to delete): list
- Weak descriptions: list
```

## O7 — Tag Hygiene Audit

Check the health of the tag vocabulary.

### O7a — Survey
```
kb_tags_list()         → all tags
```

### O7b — Check Each Tag
For each tag:
```
kb_doc_get_by_tag(tag)  → count of documents using this tag
```

Flag these issues:
- **Orphan tags**: 0 documents use this tag (can't be deleted — MCP limitation)
- **Near-duplicate tags**: pairs like "ML" / "machine-learning", "CNN" / "CNN-LSTM"
- **Low-usage tags**: tags used on only 1 document — too specific?
- **Generic tags**: "test", "doc", "misc", "important"

### O7c — Report
```
Tag Health:
  Total tags: N
  Orphan tags: N (no documents) — cannot delete, no MCP tool
  Low-usage tags (1 doc): N
  Near-duplicate pairs: N
  Suggestions:
  - "tag-a" and "tag-b" should be merged (kb_doc_update_tags to replace)
```

### O7d — Orphan Tag Resolution

When you find orphan tags (tags with 0 documents), use this workaround:

1. For orphan tag "dead-tag":
   - Check if the tag was used on a now-deleted document's KB
   - If the KB still has related documents: create a replacement tag with
     `kb_tag_create("rescue-tag")` and assign it via `kb_doc_update_tags()`
   - This "migrates" the usage away from the orphan

2. If no documents remain in the orphan tag's original domain:
   - Report: "Tag 'dead-tag' is orphaned with no related content. 
     It remains in the registry (no MCP tool to delete orphan tags)
     but does not affect search or operations."

3. If the orphan is a misspelling and you find documents that should use it:
   - Apply `kb_doc_update_tags(kb_id, doc_path, ["correct-tag"])` to the right docs
   - The orphan stays in the registry but is now unused and harmless
## CRITICAL RULES
1. O2 (read content) is NOT optional. Never classify a KB by name alone.
2. Merges: move docs FIRST, delete SECOND. Deleting first loses data.
3. Confirm destructive operations unless Module Mode.
4. O5 (verify) catches mistakes. Do not skip.
5. O7 (tag audit) cannot delete orphan tags — MCP limitation. Report and suggest manual cleanup.

## O8 — Smart Document Chunk Splitting

When an oversized document is flagged in O2 (>50KB file_size or >2000 lines),
offer to split it into smaller logical documents for better readability and
more precise vector search.

**Ratio rule guard**: The "single doc >60% of KB total" check only activates
when the KB has ≥3 documents AND total KB content >50KB. On small KBs (1-2
docs or tiny content), this rule is skipped to avoid false positives.

### O8a — Confirm

```
"The document [name] is [size KB / N lines]. I can split it into [N] smaller
documents based on its section headings. Shall I proceed?"
```

### O8b — Read & Analyze

```
kb_doc_read(kb_id, doc_path, max_chars=50000, offset=0, limit=5000)
```

Agent analyzes the content to find logical split points:

| Signal | Split Point |
|--------|-------------|
| `# Title` or `## Section` | Strong chapter break — split here |
| `Abstract`, `Introduction`, `Method`, `Results`, `Conclusion` | Standard paper sections |
| `---` horizontal rule | Possible thematic shift |
| No structural markers | Every ~400 lines, try to find a natural sentence boundary |

### O8c — Create Chunks

For each chunk N of M:

```
kb_doc_create(
  kb_id=same_kb_id,
  name="original-name_part-N.md",
  content="<chunk content>",
  description="Part N/M: <section title> — <1-sentence summary>"
)
```

Copy tags:
```
kb_doc_update_tags(kb_id, "original-name_part-N.md", ["tag1", "tag2", ...])
```

### O8d — Remove Original

After ALL chunks created successfully:
```
kb_doc_delete(kb_id, original_doc_path)
```

### O8e — Verify

```
kb_get_documents(kb_id)             → N new docs visible, original gone
kb_batch_index(kb_id, [chunk_paths], force=true)  → rebuild vector index for chunks
kb_doc_read(kb_id, chunk_1_path, max_chars=300)   → spot-check content integrity
```

### O8f — Report

```
Smart Chunk Splitting Complete:
  Original: [name] ([size])
  Split into: [N] chunks
  - Part 1: [section title] — [summary]
  - Part 2: [section title] — [summary]
  - ...
  Vector index rebuilt: ✅
  KB now has [new doc count] documents
```
