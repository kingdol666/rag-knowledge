# CRUD & Migration — Experience Create/Update/Delete + Following KB Moves

> The full create/update/delete lifecycle of experiences, plus experience follow-migration when documents move.

## Table of Contents
- [Create](#create)
- [Update](#update)
- [Delete](#delete)
- [Following document moves](#following-document-moves-experience-related_docs-follow)
- [Following KB moves](#following-kb-moves-whole-kb-experience-migration)
- [Verification checklist](#verification-checklist-after-every-operation)

---

## Create

```
experience_create(kb_id, title, scenario, category, problem, solution, result,
                  key_lessons, tags, severity, related_docs, prerequisites, metrics)
→ {success, experience: {id, ...}}
```

**The backend does this automatically** (three-layer consistency): (1) writes the disk .md (2) updates .experience-index.yml (3) vector index (shared KB collection).

Mandatory verification after create:
```
experience_read(kb_id, exp_id) → confirm fields are correct + vector_index.total_chunks ≥ 1
```

Common causes of create failures:
- `KB not found` → wrong kb_id; confirm with `kb_list`
- Vector index 0 chunks → experience content too short; flesh out problem/solution

---

## Update

```
experience_update(kb_id, exp_id, **fields)  # pass only the fields to update
→ {success, experience: {...}}
```

**The backend does this automatically**: (1) rewrites the disk .md (2) updates the index (3) re-indexes vectors (content changed → vectors recomputed).

### Update Scenarios

| Scenario | Which fields to update | Trigger |
|------|-------------|------|
| Meditation adds new lessons | `key_lessons`, `solution`, `updated_at` | Meditation Phase 4 |
| Document updated; experience stale | `problem`, `solution`, `key_lessons` | E6 stale detection |
| User reviews and scores | (automatic) `rating_avg`, `review_count` | `experience_review` |
| Experience applied | (automatic) `applied_count` | `experience_apply` |
| Supplementing related_docs | `related_docs` | Fixing links after a document move |

> ⚠️ `updated_at` does not refresh automatically — pass `updated_at=now` manually on content updates (or the backend does it automatically).
> Vector re-indexing triggers automatically when content fields (problem/solution/key_lessons/title) change.

---

## Delete

```
experience_delete(kb_id, exp_id)
→ {success, deleted_id}
```

**The backend does this automatically**: (1) deletes the disk .md (2) removes the index entry (3) deletes the vectors.

### Delete Decision Matrix

| Condition | Action | Rationale |
|------|------|------|
| Test pollution (rating=0, applied=0, age>7d) | Delete directly | Zero-value residue |
| Orphan experience (all related_docs broken) + applied=0 | Delete directly | No references, no applications |
| Orphan experience + applied>0 | Keep the content, clear related_docs | Experience still useful; repair the broken links |
| User explicitly requests deletion | Delete directly | User sovereignty |
| Outdated but still worth reference | `experience_update(status="archived")` | Soft delete: not hit by retrieval but preserved |

> Deletion is irreversible. Before deleting, use `experience_read` to look at the content and confirm it is not a mistake.

---

## Following Document Moves: experience related_docs Follow

**This is the most critical linkage.** When `kb_doc_move` moves a document, experiences referencing that document become orphans.

### Backend Status Quo (Important)

`kb_doc_move` **does not migrate experiences automatically** — it only handles the document's three layers (disk / tree index / KB metadata).
The `related_docs` paths in the experience index `.experience-index.yml` are **not updated automatically**.

**Therefore: after a document move, the Agent must repair experience links manually.**

### Manual Follow Flow (Mandatory After a Document Move)

```
Trigger: after kb_doc_move(source_kb, doc_path, target_kb) succeeds

Step 1: find the affected experiences
  # experiences in the source KB that reference the document
  experience_list(source_kb) → filter experiences whose related_docs contain doc_path

Step 2: decide where each experience goes
  For each affected_exp:
    ├─ Experience core content strongly bound to the document (the document is the only evidence source)
    │   → migrate the experience to target_kb as well:
    │     a) experience_read(source_kb, exp_id) → read the full content
    │     b) experience_create(target_kb, **content, related_docs=[new path])
    │     c) experience_delete(source_kb, exp_id)
    │     d) Verify: experience_read(target_kb, new_exp_id)
    │
    ├─ The document was only a reference; the experience can stand alone
    │   → keep the experience in its original KB; update the related_docs path:
    │     experience_update(source_kb, exp_id,
    │       related_docs=[old path → new cross-KB path, or removed])
    │
    └─ The experience references multiple documents, some of which moved
        → update related_docs: replace the moved paths, keep the unmoved ones
```

### Path Replacement Rules

```
Document move: source_kb/old_doc.md → target_kb/new_doc.md
related_docs replacement inside the experience:
  old: ["source_kb/old_doc.md", "source_kb/other.md"]
  new: ["target_kb/new_doc.md", "source_kb/other.md"]  # replace only the moved one
```

---

## Following KB Moves: Whole-KB Experience Migration

When a whole KB is renamed/moved/merged (see the knowledgebase-manage skill), all experiences under that KB
follow automatically — because experiences are stored in the KB directory's `experience/` subfolder, the
whole directory moves together with the KB.

**But note**:
- **Vector index** needs rebuilding: after a KB move the collection naming may change → `kb_reindex(force=true)`
- **Cross-KB reference** pointer experiences: experiences in other KBs pointing at this KB need their paths updated

### Experience Repair After a KB Rename

```
Trigger: KB renamed from old_name to new_name

Step 1: experiences inside the KB follow automatically (directory relocation) ✓ backend automatic
Step 2: vector re-index:
  kb_reindex(kb_id=new_name, force=true) → rebuild the collection
Step 3: cross-KB reference repair:
  # find experiences in other KBs referencing the old KB path
  experience_search_global(query="old_name") → check related_docs
  → experience_update(<other KB>, exp_id, related_docs=[new path])
Step 4: verify:
  experience_list(new_name) → confirm the experience count is unchanged
  experience_search_global(new_name, "test query") → confirm retrieval works
```

---

## Verification Checklist: After Every Operation

```
After create:
□ experience_read(kb_id, exp_id) fields correct
□ vector_index.total_chunks ≥ 1
□ new experience present in .experience-index.yml

After update:
□ experience_read confirms the updated fields took effect
□ if content changed, vector_index.indexed_at has refreshed
□ related_docs paths still exist (verify with kb_doc_read)

After delete:
□ experience_read returns not found
□ experience_list count down by 1
□ (vector deletion is fire-and-forget and may lag)

After move:
□ source KB: affected experiences handled (migrated or path-updated)
□ target KB: migrated experiences read fine via experience_read
□ related_docs all point to documents that really exist
□ cross-KB reference paths updated
```
