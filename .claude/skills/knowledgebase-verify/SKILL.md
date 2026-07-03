---
name: knowledgebase-verify
description: >
  Knowledge base integrity and quality validation. V1→V6: check KB health,
  validate index consistency, verify parse quality, detect corruption,
  cross-reference tree vs documents, generate structured integrity report.
  Invoked by Archival when the collection needs a health check, validation,
  or after operations to confirm everything is consistent.
---

# Knowledge Verify — Collection Integrity & Quality Validation

Invoked by Archival when the scenario involves **verification, validation,
health check, integrity scan, or quality audit**.

**Read-only.** Never modify any KB, document, or tag — unless explicitly
instructed to fix the issues found.

## V1 — Metadata Integrity Scan

Check that the tree file system and KB search index are in agreement.

### V1a — Survey
```
kb_list()                   → all KBs from search index
fs_get_tree(include_files=True, max_depth=0)  → full tree from filesystem
fs_get_count()              → quick folder/file counts
```

### V1b — Cross-Reference

Compare the tree structure against the KB catalog:

1. **KB consistency**: For each KB in `kb_list()`, verify there is a matching
   folder node in `fs_get_tree()`. Flag any KB that has no tree node.

2. **Doc counts**: For each KB, run `kb_get_documents(kb_id)` and compare
   the document count against what `kb_list()` reports. Discrepancies suggest
   stale index data.

3. **Orphan nodes**: Walk `fs_get_tree()` for file nodes that have no
   corresponding entry in any KB's `kb_get_documents()`. These are orphan
   files existing in the tree but not searchable.

**Report format:**
```
Metadata Integrity:
  KBs in catalog: N
  KBs in tree: N
  Mismatched: N (list)
  - KB "Name" has no tree folder
  - Orphan files: N (list)
```

## V2 — Document Integrity Check

For each KB, verify that its documents are actually accessible.

### V2a — Survey
```
kb_get_documents(kb_id)     → all documents in one KB
```

### V2b — Spot-Check

For each document in a KB:
- Try `kb_doc_read(kb_id, doc_path, max_chars=100)` — if this fails with
  a 404, the document reference exists in the index but the file is missing
  from disk. This is a **broken reference**.

- Check description: is it empty, a filename only, or meaningful?
  Flag poor descriptions: empty, "test", filename without extension.

- Check tags via `kb_doc_get_by_tag()`. If a doc has no tags, flag it.

**Optimization**: Don't test ALL documents in large KBs. Sample:
- 1-10 docs: check all
- 11-50 docs: check first 50%
- 50+ docs: check first 20 (focus on recent additions)

**Report format:**
```
Document Integrity:
  KB "Name" (N docs):
    Broken references: N (list)
    Missing descriptions: N
    Untagged: N
    Healthy: N
```

## V3 — Parse Quality Validation

Check that documents that went through MinerU parsing have valid content.

### V3a — Find Parse Results

For documents with `.pdf`, `.docx`, `.pptx`, `.xlsx` sources (inferred from
description or name pattern):
```
kb_doc_read(kb_id, doc_path, max_chars=2000)
```

### V3b — Quality Checks

For each parsed document:

| Check | Pass criteria | Red flag |
|-------|---------------|----------|
| **Empty content** | Content length > 100 chars | "No content", "Parse failed", empty |
| **OCR garbage** | Sentences are coherent | Random chars, garbled CJK, repeated patterns |
| **Binary residue** | No binary characters | `\x00`, `\xff\xfe`, base64 noise |
| **Only headings** | Has paragraph text | Only `# Title`, markdown structure but no body |
| **Image extraction** | Images present (inferred from images_dir) | Zero images for a PDF with diagrams |

**Report format:**
```
Parse Quality:
  KB "Name":
    Document "doc.md": [HEALTHY / GARBLED / EMPTY / ONLY HEADINGS]
    Document "doc2.md": [HEALTHY / GARBLED]
```

## V4 — Index Consistency Repair

**Only do this if the user explicitly asks to fix issues.**

For broken references (document in `kb_get_documents()` but not readable):
```
kb_doc_delete(kb_id, doc_path)
```
This removes the stale index entry. The file on disk is kept (it's just
no longer referenced by the index).

For orphan files (in tree but no KB doc entry):
No automated fix — `fs_get_tree()` to find them, report the path.
User can decide to re-import or delete.

## V5 — KB Structure Health Scorecard

Generate a summary of the overall collection health:

```
## Collection Health Scorecard

### Metadata Consistency      X/25
  KB catalog matches tree:     X/10
  No orphan nodes:              X/10
  No broken references:         X/5

### Document Quality           X/30
  Parsed content healthy:       X/20
  Images extracted:             X/10

### Tag Coverage               X/25
  Tagged documents:             X/15  (tagged / total × 15)
  No orphan tags:               X/10

### Description Quality        X/20
  KB descriptions set:          X/10
  Doc descriptions meaningful:  X/10
  ──────────────────────────────────────
  TOTAL: X/100

### Issues Found
- Critical (broken refs): N
- Warning (poor quality): N
- Info (untagged, weak desc): N
```

## V6 — Report

"I've completed the integrity scan of the collection.

**Score:** XX/100 — [EXCELLENT / GOOD / FAIR / NEEDS ATTENTION]

**Key findings:**
- N KBs, N documents scanned
- [N critical / N warning / N info]
- Top recommendation: [single most impactful action]

Full details above."

---

## CRITICAL RULES
1. **Read-only by default.** V4 repair requires explicit user instruction.
2. V2 sampling avoids overwhelming large collections.
3. V1 cross-reference catches issues no other skill detects.
4. V3 parse quality catches OCR failures that look "successful" at the API level.
5. The scorecard in V5 provides a single-number health metric useful for tracking over time.
