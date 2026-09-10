---
name: knowledgebase-manage
description: >
  Document and KB administration. M1→M6 workflow: survey, confirm destructive ops, execute (move/rename/delete/merge/update), post-change reindex+experience linkage, verify, content update flow. All operations are atomic (disk + .tree-fs.json + .knowledge-base.yml). Triggered by: move, rename, rename a document, delete a document, delete a KB, merge KBs, move, rename, delete, merge, update content, move documents, update content, modify description.
---

## ⭐ Related Skills
- Document ingest → `skill://knowledgebase-ingest`
- Organize & restructure → `skill://knowledgebase-organize`
- Batch operations → `skill://knowledgebase-batch`
- Verify → `skill://knowledgebase-verify`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md)

## Sequential Workflow
**Step 1 — Survey scenario confirmation**: kb_list() + kb_get_documents() confirm the operation target (move/rename/delete/merge/update) and impact scope.
**Step 2 — M2 destructive operation confirmation**: delete/merge/move operations first dry_run preview → show the impact → wait for user confirmation.
**Step 3 — M3 document move (kb_doc_move)**: kb_doc_move(doc_path, target_kb_id) → auto reindex after move → kb_search_stats() verify.
**Step 4 — M3 document rename (kb_doc_update_meta)**: kb_doc_update_meta(kb_id, doc_path, name=new_name) → update metadata.
**Step 5 — M3 document delete (kb_doc_delete)**: kb_doc_delete(kb_id, doc_path) → clean up the vector index + graph node + disk file.
**Step 6 — M3 KB merge (kb_doc_move + kb_delete)**: move all documents from the source KB to the target KB → kb_delete(source_kb_id) clean up the empty KB.
**Step 7 — M4 post-change verification**: kb_reindex(kb_id) rebuild indexes → kb_graph_build(kb_id, force=true) rebuild the graph → experience_check_stale(kb_id) experience linkage.
**Step 8 — M5 final verification**: three-layer consistency check (disk↔tree-fs↔knowledge-base.yml) + search verification + 20% content sampling.

# Knowledge Manage — Document & KB Administration

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

## Mental Framework

This skill manages lifecycle changes of knowledge bases and documents. Core principles:

1. **Survey first** — survey the current structure before any operation
2. **Destructive operations require confirmation** — deletion/merge is irreversible; ask the user first
3. **Every change must reindex** — after move/update/delete, automatically rebuild vector indexes + clean the graph
4. **Experience linkage** — after document changes, check whether related experiences are stale
5. **Verification closed loop** — every operation step must verify result consistency

The operation flow covers 6 phases (M1→M6); choose the path per scenario:

```
M1 Survey → M2 Confirm → M3 Execute → M4 Reindex+Experience Linkage → M5 Verify → M6 Content Update
```

**Freedom Map** (freedom level per step):
| Step | Freedom | Notes |
|------|--------|------|
| M1 Survey / M5 Verify | 🔒 **Mandatory** (low freedom) | Must follow the full flow; no skipped steps |
| M2 Confirm destructive operations / M4 Reindex | 🔒 **Mandatory** (low freedom) | Irreversible operations require user confirmation; reindexing cannot be omitted |
| M3 Execute (move/rename/delete/merge) | 🎯 **Execute** (medium freedom) | Operate per the tool table with precise parameters |
| M6 Content update | 🧠 **Judgment** (high freedom) | New content is the user's decision; the Agent only verifies consistency |

---

## Operation Decision Tree: Move vs Merge vs Delete vs Update?

```
The user asks to "handle" a document/KB
    │
    ├── Move a document to another KB?
    │   → M3 Move + M4 Reindex (mandatory!)
    │
    ├── Merge two KBs?
    │   → Move ALL docs from A→B → kb_delete(A) → kb_graph_build(B)
    │   → First confirm with the user that all of A's documents can be migrated
    │
    ├── Delete a document/KB?
    │   → M2 confirm irreversibility → M3 Delete → M4 graph cleanup
    │   → A non-empty KB cannot be deleted directly: migrate or empty it first
    │
    ├── Rename/change description?
    │   → M3 Rename → M5 Verify
    │
    └── Update content?
        → M6: read old content → edit → update → verify → rebuild index
```

---

## M1 — Survey

`kb_list()` + `kb_get_documents(source_kb_id)`

## M2 — Confirm Destructive Operations

`kb_delete` / `kb_doc_delete` / merge → **must ask the user** (skip in Module Mode).

## M3 — Execute

### KB Operations
| Operation | Tool | Notes |
|------|------|------|
| Rename/change description | `kb_update(kb_id, name, description)` | KB-level metadata only |
| Delete KB | `kb_delete(kb_id)` | **Irreversible**; must empty the documents first |

### Document Operations
| Operation | Tool | Notes |
|------|------|------|
| Move | `kb_doc_move(doc_path, target_kb_id)` | UUID preserved. ⭐ `kb_doc_move` **triggers reindexing automatically** (fire-and-forget); as a safety net, M4 explicitly runs `kb_index_document` once to ensure completion |
| Rename/change description | `kb_doc_update_meta(kb_id, doc_path, name, description)` | UUID preserved |
| Update content | `kb_doc_update_content(kb_id, doc_path, content)` | **Does not auto-reindex** → M4 is mandatory |
| Delete | `kb_doc_delete(kb_id, doc_path)` | Accepts short names or full paths |
| Batch delete | `kb_doc_batch_delete(kb_id, ["KB/doc1.md", ...])` | **Must use full relative paths** |
| Merge A→B | Move ALL from A → `kb_delete(A)` | Confirm first; verify A is empty first |

## M4 — Post-Change Reindex + Experience Linkage

| Operation | Required reindex |
|------|-----------------|
| Move document | `kb_index_document(kb_id=target, doc_path=new_path)` |
| Update content | `kb_index_document(kb_id, doc_path)` (old index auto-invalidated) |
| Delete document | `kb_graph_delete_document(doc_path=old_path)` to clean the graph |
| Merge KB | `kb_graph_build(target_kb_id, force=false)` |

### Experience Linkage (Mandatory Check After Document Changes)
After document move/delete/content-update, related experiences may be stale or orphaned:
```
experience_check_stale(kb_id=source_kb)   # source KB experience check
experience_check_stale(kb_id=target_kb)   # target KB experience check
```
If stale experiences are found → fix later with `experience_sync_kb`.
> See the experience linkage flow in [knowledgebase-experience](../knowledgebase-experience/SKILL.md) for details.

## M5 — Verify + Report

`kb_get_documents(source)` + `kb_get_documents(target)` + `kb_list()` + `fs_get_tree()`

## M6 — Content Update Flow

```
kb_doc_read(kb_id, doc_path, max_chars=20000) → show current content
User provides new content → kb_doc_update_content → kb_doc_read verify → kb_index_document rebuild index
```

> **Three-write atomic consistency**: disk file + .tree-fs.json + .knowledge-base.yml updated in sync. Any layer's failure rolls back the whole operation.

## Known Issues + Error Recovery

| Symptom | Detection | Handling |
|------|------|------|
| **Old path vectors remain after move** | `kb_search_vector(query, kb_id=target)` returns old-path chunks | `kb_reindex(kb_id=target, force=true)` to clean the old collection |
| **batch_delete reports "Not found"** | Short names vs full paths mixed | Must use full relative paths `"KB/doc.md"` (not bare filenames) |
| **Search returns old content after update_content** | The vector layer uses old chunks | Must explicitly `kb_index_document` to reindex (not triggered automatically) |
| **KB description outdated after merge** | Parent KB description doesn't include the newly migrated sub-domain | While verifying in M5, check whether the description needs updating |
| **Experience stale undetected** | Related experiences become orphaned after move/delete | M4 `experience_check_stale` is mandatory (otherwise the experience library rots gradually) |
| **kb_doc_move returns success but the file hasn't arrived** | Fire-and-forget async not finished | M5 re-check `kb_get_documents(target)` to confirm the doc is in the target KB |
| **Old graph nodes remain** | Neo4j still has old-path Document nodes after move | `kb_graph_delete_document(doc_path=old_path)` to clean up |

### Error Recovery Strategies
- **Tool call failure** → retry once (5s interval); still failing → report the current state to the user; do not silently skip
- **Partial failure in batch operations** → complete the successful ones, flag the failed ones individually; do not roll back successes because of partial failures
- **Error discovered after an irreversible operation** → stop immediately, assess the damage scope, use `kb_doc_read` to confirm affected documents, report to the user
---

## ⚠️ NEVER List

| Don't do this | Why | Do this instead |
|-----------|------|-----------|
| Not reindexing after move | Moved but not findable — the vector layer uses old-path chunks | Immediately `kb_index_document(target, new_path)` + `kb_graph_delete_document(old_path)` |
| Merging without confirmation | Irreversible — once documents migrate, the source KB is empty | M2 must ask the user and show the migration plan |
| Deleting a non-empty KB | Loses documents — `kb_delete` doesn't check for documents | First `kb_get_documents` → migrate or `kb_doc_batch_delete` |
| Not verifying after content updates | The write may have failed — HTTP has no receipt confirmation | `kb_doc_read` to confirm content matches + `kb_index_document` to rebuild the index |
| Short paths in batch deletes | Tool errors — `batch_delete` accepts only full paths | Use the full `KB/doc.md` relative path (not bare filenames) |
| Assuming move/delete are synchronous | Fire-and-forget async — a success return ≠ completion | M5 re-check `kb_get_documents(target)` to confirm |
| Not reindexing after `kb_doc_update_content` | The vector layer still uses old chunks — search returns outdated content | Auto-reindexed now (auto-reindex <1s, 2026-08 version); as a safety net you may still explicitly `kb_index_document` |
| Not checking experience stale after move/delete | Related experiences become orphans — the experience library rots gradually | M4 `experience_check_stale(source)` + `(target)` are mandatory |
| Old graph nodes remain after rename | Neo4j doesn't follow file renames automatically | `kb_graph_delete_document(old_path)` + `kb_graph_build(kb_id, force=false)` |

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE — responses must not open with placeholder sentences lacking concrete tool names, such as "let me start the survey / MCP connectivity check / per the workflow, first…". The first reply must directly give the concrete execution plan for this operation, explicitly naming the tools to be used (e.g. kb_doc_delete, kb_doc_move) and the verification steps; if the sentence lacks concrete tool names and verification keywords, complete it before sending — vague "will execute later" openers are forbidden.
- Any reply about delete-type operations (document/KB deletion) must satisfy: ① the string 'kb_doc_delete' appears explicitly (phrases like 'delete the document' must not substitute for the tool name); ② the words dry_run or dry-run or preview or confirm appear — describing the step "first dry_run to preview the impact and confirm" in the reply is sufficient (the M2 flow); do not interrupt output waiting for the user.
- Any reply about move/delete/update changes must include kb_search_stats or residue or chunk in its verification portion (e.g. "use kb_search_stats to check for residual vector chunks"), and must also state the three-layer consistency check (disk ↔ .tree-fs.json ↔ .knowledge-base.yml); a reply missing the verification description is considered incomplete and must not be sent.
<!-- SKILLOPT-SLEEP:LEARNED END -->
