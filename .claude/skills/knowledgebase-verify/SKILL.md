---
name: knowledgebase-verify
description: >
  Knowledge base integrity and quality validation. V1→V9: three-way metadata consistency (disk↔.tree-fs.json↔.knowledge-base.yml), document integrity, parse quality, index coverage+repair, scorecard (max 115), report, tag health (orphan+trash detection), experience health (stale+orphan+test pollution), auto-fix (repeat collections, orphan tags, missing indexes). Read-only by default; repair requires explicit instruction. Triggered by: validate, cross-check, integrity, health check, verify, check, consistency, verify, validate, integrity, health check, quality audit, check KB, detect issues, audit the knowledge base.
---

## ⭐ Related Skills
- KB organize & cleanup → `skill://knowledgebase-organize` (O1-O8 full flow)
- Document/KB management → `skill://knowledgebase-manage` (move/delete/merge)
- Batch operations → `skill://knowledgebase-batch` (B1-B7 batch flows)
- Experience health check → V8 experience health of `skill://knowledgebase-experience`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`
- Update to the latest version → `skill://knowledgebase-update`

## Sequential Workflow (When the User Requests Validation/Checking)

**Step 1 — Determine the validation scope**: quick check (V1+V5 10% sampling) / regular health (V1→V9) / deep audit (V1→V9 full).
**Step 2 — V1 three-layer metadata consistency**: kb_list() vs fs_get_tree() vs kb_get_documents() cross-validation.
**Step 3 — V2 document integrity**: per the sampling strategy, doc_read to check documents are readable.
**Step 4 — V3 parse quality**: check OCR/Markdown quality of PDF/DOCX-sourced documents.
**Step 5 — V4 index coverage+repair**: check vector index and graph index coverage.
**Step 6 — V5 scorecard**: compute the composite health score on the 115-point scale.
**Step 7 — V6 report**: output the total score + key findings + top recommendation.
**Step 8 — V7 tag health**: detect orphan tags and junk patterns.
**Step 9 — V8 experience health**: detect stale/orphan/test-polluted experiences.
**Step 10 — V9 auto-fix (requires user confirmation)**: fix detected issues.

# Knowledge Verify — Integrity & Quality

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- **Read-only by default.** V4/V7/V9 repair requires explicit user instruction.

## Mental Framework: First Judge the Validation Focus ⭐

```
The user says "validate/check"
    │
    ├── Suspects metadata inconsistency → V1 Three-Way Metadata
    ├── Document fails to open/404 → V2 Document Integrity
    ├── Garbled content after parsing a PDF → V3 Parse Quality
    ├── Document can't be found in search → V4 Index Coverage
    ├── "Thorough audit" → V1→V9 full flow
    └── A specific KB specified → run that KB's complete flow only
```

### Validation Strategy Selection

| Scenario | Breadth | Depth | Time |
|------|------|------|------|
| Quick check | V1 + V5 stats only | 10% sampling | ~10s |
| Regular health check | V1→V9 | Normal sampling | ~60s |
| Deep audit | V1→V9 full | Every document | ~5min+ |
| Post-fix verification | V4 index + V5 score | Before/after comparison | ~30s |


**Freedom Map** (freedom level per step):
| Step | Freedom | Notes |
|------|--------|------|
| V1-V4 detection / V5 scoring / V7 tag health | 🔒 **Mandatory** (low freedom) | Detection flows must be complete; no skipped steps; scoring follows formulas, not subjectivity |
| V6 report / V8 experience health | 🎯 **Execute** (medium freedom) | Output per the template; prioritize findings by actual impact |
| V9 auto-fix | 🧠 **Judgment** (high freedom) | Requires explicit user instruction to execute; reversible fixes can be batched; irreversible ones need per-item confirmation |
| Sampling strategy | 🎯 **Execute** (medium freedom) | Pick the sampling ratio by library size; no full scans (>100 docs) and no laziness (<10%) |
---

## V1 — Three-Way Metadata Integrity

Verify `kb_list()` and `kb_get_documents()` document-count consistency, plus `fs_get_tree()` path cross-references (note: MCP tools cannot directly access the raw `.tree-fs.json`/`.knowledge-base.yml` files; UUID-level consistency is guaranteed by the tools' internal atomic operations).

1. `mcp__kb-mcp__kb_list()` vs `mcp__kb-mcp__fs_get_tree()` — flag KBs with no tree node, orphan nodes, doc count mismatches.
2. For each KB: `mcp__kb-mcp__kb_get_documents(kb_id)` — check each doc has a matching file on disk via path cross-reference.
3. ⚠️ UUID-level consistency is guaranteed by MCP tools' atomic operations (every CRUD updates all three layers in sync); V1 validation is based on path cross-references rather than direct UUID comparison.
4. Flag: phantom entries (metadata but no disk file), orphan files (disk but no metadata).

> **Known normal behavior** (not an inconsistency): the entry count returned by `kb_get_documents()` may exceed the `doc_count` from `kb_list(lightweight=true)` — the extra entries are **sub-KB containers** (`file_type: knowledge-base`, not real documents). Use `fs_get_tree(max_depth=2)` to distinguish parent/child levels.

## V2 — Document Integrity

`mcp__kb-mcp__kb_get_documents(kb_id)` → sample `mcp__kb-mcp__kb_doc_read` using the sampling strategy below.
Flag: broken 404s, empty descriptions, untagged docs.

### Sampling Strategy

| Library size | Sampling ratio | Minimum samples |
|--------|---------|---------|
| 1-10 | 100% | all |
| 11-50 | 50% | at least 10 |
| 51-100 | 25% | at least 25 |
| >100 | 15% | at least 50 |

---

## V3 — Parse Quality

`mcp__kb-mcp__kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names).
Flag: empty content (<100 chars), OCR garbage, binary residue, heading-only (no body).

Use `mcp__kb-mcp__backend_status()` for MinerU health (authoritative).

## V4 — Index Coverage & Repair

### Vector
`mcp__kb-mcp__kb_get_documents(kb_id)` → check `vector_index` field per doc. `mcp__kb-mcp__kb_search_stats(kb_id)` → check chunk counts.
**Repair**: `mcp__kb-mcp__kb_index_document(kb_id, doc_path)` or `mcp__kb-mcp__kb_batch_index(kb_id, [paths], force=true)`.

### Graph
`mcp__kb-mcp__kb_graph_stats()  # check neo4j_available field` → Neo4j available? `mcp__kb-mcp__kb_graph_kb_overview(kb_id)` → doc_count vs actual.
**Repair**: `mcp__kb-mcp__kb_graph_build(kb_id, force=true)`.
**Clean stale**: `mcp__kb-mcp__kb_graph_delete_document(doc_path)` for deleted docs.

## V5 — Scorecard (max 115)

Metadata Consistency (25) | Document Quality (30) | Tag Coverage (25) | Description Quality (10) | Graph Health (15) | Vector Coverage (10)

| Dimension | Max | Scoring method |
|------|------|---------|
| Metadata consistency | 25 | matched entries / total entries × 25 |
| Document quality | 30 | sampled pass rate × 30 |
| Tag coverage | 25 | tagged documents / total documents × 25 |
| Description quality | 10 | content-based description ratio × 10 |
| Graph health | 15 | graph coverage × 15 |
| Vector coverage | 10 | vector index coverage × 10 |

## V6 — Report

Score + key findings + single most impactful recommendation.

### Report Template
```
## Validation Report: <KB name>
Total score: XX/115

| Dimension | Score | Status |
|------|------|------|
| Metadata consistency | XX/25 | ✅/⚠️/❌ |
| Document quality | XX/30 | ✅/⚠️/❌ |
| Tag coverage | XX/25 | ✅/⚠️/❌ |
| Description quality | XX/10 | ✅/⚠️/❌ |
| Graph health | XX/15 | ✅/⚠️/❌ |
| Vector coverage | XX/10 | ✅/⚠️/❌ |

### Key Findings
- <finding 1>
- <finding 2>

### Top Recommendation
<the single most cost-effective fix>
```

## V7 — Tag Health

Detect 0-reference orphan tags and junk patterns like section titles/test tags.

**Recommended method**: `kb_tags_cleanup(dry_run=true)` — a single O(M) scan of the whole library, returning the orphan classification immediately.
- After the 2026-07-30 optimization: changed from O(N×M) with N HTTP probes to a single `/api/kb/tags/analysis` call; measured <100ms for 151 tags
- Returns `{orphan_tags: [{tag, refs, reason}], referenced, orphan}`
- reason has two classes: `unreferenced` (0 document references) + `garbage_pattern` (section titles/test residue/special characters, identified by the web layer's `isGarbageTag`)
- Domain core-word protection: PET/PVA/DL/RAG/polymer/embodied intelligence, etc., are protected by MCP-layer protected_patterns and are not cleaned even with 0 references
- `dry_run=false` executes the cleanup (delegates to web `removeOrphanTags`; irreversible; preview first recommended)

## V8 — Experience Health

`mcp__kb-mcp__experience_check_stale()` (empty kb_id = whole-library check)
`mcp__kb-mcp__experience_dashboard(kb_id)` — for every KB with experiences

- Orphan experiences: related documents deleted → recommend `mcp__kb-mcp__experience_delete` or updating `related_docs`
- Stale experiences: documents updated but experiences not synced → recommend `mcp__kb-mcp__experience_sync_kb`
- Test pollution: rating=0, applied=0, age>7d → recommend cleanup
- Low-quality experiences: rating<2, review≥3 (disputed) → recommend review

## V9 — Auto-Fix

After V1-V8 detect issues, the executable auto-fix paths:

| Detected issue | Auto-fix path |
|------------|------------|
| Duplicate collection | `mcp__kb-mcp__kb_cleanup_orphan_collections(dry_run=false)` |
| Orphan tags | `mcp__kb-mcp__kb_tags_cleanup(dry_run=false)` |
| Document missing vector index | `mcp__kb-mcp__kb_index_document(kb_id, doc_path)` |
| Document missing graph index | `mcp__kb-mcp__kb_graph_build(kb_id, force=false)` |
| Metadata inconsistency | `mcp__kb-mcp__kb_reindex(kb_id, force=true)` rebuild |
| Orphan experience | `mcp__kb-mcp__experience_delete(kb_id, exp_id)` or `mcp__kb-mcp__experience_update(related_docs=[])` |
| Test experience pollution | `mcp__kb-mcp__experience_delete(kb_id, exp_id)` (after confirmation) |

**Auto-fix principle**: only fix issues that are auto-detectable + auto-fixable; destructive operations (delete documents/delete KBs/merge KBs) require user confirmation.

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Run V4/V7/V9 repairs without user instruction | Read-only violated — validation becomes operation | Report results first; act only when the user says "fix" |
| Judge KB health with `kb_list` alone | Missing document-level checks — KB-level OK ≠ document-level OK | Must pair `kb_get_documents` + disk verification |
| Large doc_read batches without progress reporting | The user thinks it hung — >50 docs takes non-trivial time | Report progress "x/N checked" |
| Skip all other checks when Neo4j is down | V1-V4, V6 don't depend on Neo4j | Skip V5 Graph Health; proceed with the rest |
| Score reports without fix recommendations | The user doesn't know what to fix first | V6 must contain a "top recommendation" (most cost-effective fix) |
| Trust `kb_list(lightweight=true)`'s `doc_count` as the real document count | Includes sub-KB container entries — actual document count is lower | Filter by `file_type: knowledge-base` or confirm with `fs_get_tree` |
| Run V3 Parse Quality on non-parsed documents | MD/TXT direct-created documents have no OCR traces — pointless | V3 runs only on `.pdf`/`.docx`/`.pptx`-sourced documents |
| Emit a report with sampling below the minimum | Statistically insignificant — small samples mask systemic issues | Strictly follow the sampling table minimums (at least 10/25/50) |
