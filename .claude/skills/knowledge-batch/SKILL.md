---
name: knowledge-batch
description: >
  High-volume and batch operations for knowledge base management. B1→B6:
  bulk tag migration, bulk description updates, directory-to-KB ingestion,
  mass document move between KBs, cross-KB content sync, and export summary.
  Invoked by Archival when operations involve multiple documents, batch
  processing, or repetitive updates across the collection.
---

# Knowledge Batch — Bulk & Batch Operations

Invoked by Archival when the scenario involves **batch, bulk, mass,
multi-document, repetitive, 批量, 批量操作, 大规模**.

## B1 — Bulk Tag Management

Apply, replace, or clear tags across multiple documents.

### B1a — Survey
```
kb_tags_list()         → all existing tags
kb_list()              → all KBs for context
```

### B1b — Batch Tag Application

**Add a tag to all untagged documents in a KB:**
```
docs = kb_get_documents(kb_id)
for each doc without tags:
    kb_doc_update_tags(kb_id, doc.doc_path, ["target-tag"])
```
Return a summary: "Applied tag 'x' to N documents in KB 'Name'."

**Replace a tag across all documents:**
```
kb_doc_get_by_tag("old-tag")    → all docs using this tag
for each doc:
    # Read current tags (parse from kb_get_documents data)
    # Replace "old-tag" with "new-tag"
    kb_doc_update_tags(kb_id, doc.doc_path, ["new-tag", ...other-tags])
```

**Remove a tag from all documents (migration):**
Use the same find-and-replace pattern but drop the old tag without adding a replacement.

### B1c — Verify
```
kb_doc_get_by_tag("old-tag")    → should now return 0 or fewer docs
kb_doc_get_by_tag("new-tag")    → should now return the migrated docs
```

## B2 — Bulk Description Updates

Fix empty or poor-quality descriptions across the collection.

### B2a — Survey
```
kb_list()            → find KBs with poor descriptions (empty, "test", etc.)
```

### B2b — Read Content
For each KB with a poor description:
- Read 1-2 representative docs: `kb_doc_read(kb_id, doc_path, max_chars=300)`
- Determine the actual domain based on content

### B2c — Update KB Descriptions
```
kb_update(kb_id, description="<1-3 sentences: domain + content types + language>")
```

### B2d — Batch Doc Descriptions
For a single KB with many untagged/poorly-described docs:
```
kb_get_documents(kb_id)
for each doc with weak or missing description:
    kb_doc_read(kb_id, doc_path, max_chars=300)
    kb_doc_update_meta(kb_id, doc_path, description="<1-2 sentences from content>")
```

**Sampling rule**: For KBs with >20 docs, only fix descriptions that are
empty or clearly placeholder ("test", "tbd", filename-only). Don't rewrite
every description — focus on the broken ones.

## B3 — Directory-to-KB Mass Ingestion

Import all files from a disk directory into a specified KB.

### B3a — Discover Files
Use `Glob` or `Bash` to list files in the target directory:
```
Glob(path="<directory>", pattern="**/*")
```

### B3b — Classify by Format
Sort discovered files by type:

| Extension | Method | Notes |
|-----------|--------|-------|
| `.pdf`, `.docx`, `.jpg` etc | `parse_pdf_to_kb()` | Non-blocking per file |
| `.md`, `.txt`, `.csv` etc | `kb_doc_create()` + `fs_upload_file()` | Direct content for text files |
| Other binaries | `fs_upload_file()` | Store without parsing |

### B3c — Execute in Order

1. **Parse-path files first** (MinerU is the bottleneck — start them early).
   Submit each: `parse_pdf_to_kb(file_path, kb_id, description, tags=["batch-import"])`
   Save all `task_id`s.

2. **Direct-path files**: Read content and create immediately.
   ```
   with open(file_path) as f:
       kb_doc_create(kb_id, name, f.read(), description)
   ```

3. **Binary uploads**: `fs_upload_file(file_path, parent_id, description)`

4. **Poll all parse tasks**: Check each `task_id` with `parse_task_status()` until done.

### B3d — Report
```
Batch Import Complete
  Discovered: N files
  Parsed (MinerU): N  (N succeeded, N failed)
  Direct-stored: N
  Binary-uploaded: N
  KB: [Name]
  Parse failures: [list filenames + errors]
```

## B4 — Mass Document Move

Move all documents from a source KB to a target KB.

### B4a — Survey
```
kb_list()                               → find source + target KBs
kb_get_documents(source_kb_id)          → all docs to move
```

### B4b — Confirm
"Move all N documents from [SourceKB] to [TargetKB]? This is non-destructive."
(No confirmation needed in Module Mode.)

### B4c — Execute
```
docs = kb_get_documents(source_kb_id)
for each doc in docs:
    kb_doc_move(doc.doc_path, target_kb_id)
```

**Note**: If the source KB has a large number of documents (>50), warn
the user: "Moving N documents — this may take a moment."

### B4d — Verify
```
kb_get_documents(source_kb_id)  → should be 0 (or decreased)
kb_get_documents(target_kb_id)  → should be increased by N
```

### B4e — Report
"Moved all N documents from [Source] to [Target]. Source KB is now empty.
Do you want to delete the empty source KB?"

## B5 — Cross-KB Content Sync

Identify documents that exist in multiple KBs (duplicates) and deduplicate.

### B5a — Survey
```
kb_list()             → all KBs
for each KB:
    kb_get_documents(kb_id)    → get doc list
```

### B5b — Find Cross-KB Duplicates
Compare document names across KBs:
- Same filename + similar size → likely duplicate
- Read first 500 chars of each: `kb_doc_read(kb_id, path, max_chars=500)`
- If content matches → confirmed duplicate

### B5c — Deduplicate
For each confirmed duplicate:
1. Keep the copy in the KB that best matches the content domain.
2. `kb_doc_delete(from the wrong KB, doc_path)`
3. If the "right" copy has no tags, copy tags from the deleted copy.

### B5d — Report
```
Cross-KB sync complete:
  Duplicates found: N across N KB pairs
  Removed: N
  Retained in: [correct KB names]
```

## B6 — Export Summary

Generate a structured markdown summary of the collection.

### B6a — Survey
```
kb_list()              → all KBs
kb_tags_list()         → all tags
fs_get_tree(include_files=True, max_depth=0)  → full tree
fs_get_count()         → totals
```

### B6b — For Each KB
```
kb_get_documents(kb_id)    → all docs with metadata
```
Collect: doc count, total size, tag count, addition dates.

### B6c — Write Report
Use `Write` to save a markdown report:
```
Write(
  file_path=".claude/collection-report.md",
  content="## Collection Summary\n\n..."
)
```

**Report structure:**
```
## Collection Summary
Generated: <date>

### Overview
- Total KBs: N
- Total Documents: N
- Total Tags: N
- Total Size: ~X MB

### KBs
| KB | Docs | Tags | Created | Description |
|----|------|------|---------|-------------|

### Tags
| Tag | Documents | KBs |
|-----|-----------|-----|

### Recent Activity
- Last added: doc name (date)
- Largest KB: name (N docs)
- Most tagged: name (N tags)
```

### B6d — Report to User
"Collection summary generated at .claude/collection-report.md"
Present the overview numbers.

---

## CRITICAL RULES
1. B3 (mass ingestion): Parse-path first, poll all after — parallelize MinerU.
2. B4 (mass move): Warn on >50 docs. Large batches take time.
3. B5 (dedup): Never delete without content comparison. Filename match is not enough.
4. B6 (export): Always `Write` to file. The report is useful beyond this session.
5. B1 (tag bulk): Tag replacement can be slow — 2-3 seconds per doc. Large collections may take a while.
6. All batch operations should report progress: "3/10 done, 7 remaining."
