# Plan: Knowledge-Base Skill Enhancement — Phase 2

## Requirements Summary

Extend the existing Archival agent + 5 knowledge-base skills with 6 new features:

| # | Feature | Type | Current Gap |
|---|---------|------|-------------|
| 1 | Ingest dedup check (A0) | New step in `knowledge-ingest` | No pre-ingest duplicate detection → manual cleanup |
| 2 | Tag hygiene (C7) | New step in `knowledge-organize` | Orphan tags accumulate; no automated detection |
| 3 | Search scenario | New skill `knowledge-search` | `kb_search()` exists but no structured search workflow |
| 4 | Content update (B6) | New step in `knowledge-manage` | Update content exists in toolkit but no procedure |
| 5 | Health scorecard (C6→C7) | Upgrade `knowledge-organize` | Current report is qualitative, not quantified |
| 6 | Housekeeping | 1-time actions | Test-Scratch delete, orphan tag detection |

## File Changes

### Files to Modify (4 skills + agent routing)

| File | Lines | Changes |
|------|-------|---------|
| `.claude/skills/knowledge-ingest/SKILL.md` | 141→165 | +A0 Dedup check step before A1 |
| `.claude/skills/knowledge-manage/SKILL.md` | 107→120 | +B6 Content update procedure |
| `.claude/skills/knowledge-organize/SKILL.md` | 143→170 | +C7 Tag hygiene, upgrade C6→scorecard |
| `.claude/agents/knowledge-admin.md` | 549 | +Search to Step 0 diagnostics, add Search to sub-skills table |

### File to Create (1 new)

| File | Lines | Purpose |
|------|-------|---------|
| `.claude/skills/knowledge-search/SKILL.md` | ~80 | S1-S5 structured search workflow |

### Files NOT changed

| File | Reason |
|------|--------|
| `knowledge-store/SKILL.md` | Route table already covers dispatch; Search added via agent routing |
| `knowledge-list/SKILL.md` | Read-only discovery; search is a distinct scenario |
| `openai.yaml` | Not affected |

## Implementation Steps (Sequential, No Cross-File Dependencies)

### Step 1: knowledge-ingest — Add A0 Dedup Check

**Location**: Insert before A1 in `knowledge-ingest/SKILL.md`
**Logic**:
```
A0 — Duplicate Pre-Check
  For each document:
    kb_search(query="<filename without extension>", top_k=5) 
    If results found: check if any result has matching name/content hash
    If duplicate found: report to user, ask to skip or re-parse
    If no duplicate: proceed to A1
```
**Tool used**: `kb_search()` — already in tools, requires no new permissions

### Step 2: knowledge-manage — Add B6 Content Update

**Location**: Insert after B5 in `knowledge-manage/SKILL.md`
**Procedure**:
```
B6 — Update Document Content
  1. kb_doc_read() to show current content
  2. Confirm user wants to overwrite
  3. kb_doc_update_content(kb_id, doc_path, new_content)
  4. Note: file_size stays stale (Known Gotcha #3)
  5. Verify: kb_doc_read() to confirm change
```

### Step 3: knowledge-organize — Add C7 Tag Hygiene + Upgrade C6 Scorecard

**C6 Scorecard upgrade**: Add quantitative scoring to the existing C6 report:
```
Health Scorecard:
  ├── Tag Coverage: X/30 (documents tagged / total docs × 30)
  ├── Description Quality: X/25 (good descriptions / total × 25)
  ├── Uniqueness: X/25 (unique docs / total × 25)
  └── KB Structure: X/20 (proper-named KBs / total × 20)
  ─────────────────
  Total: X/100
```

**C7 Tag Hygiene**:
```
C7 — Tag Hygiene Audit
  1. kb_tags_list() → all tags
  2. For each tag: kb_doc_get_by_tag(tag) → count
  3. Flag orphan tags (0 docs), near-duplicate tag pairs
  4. Report: "N orphan tags, N near-duplicate pairs"
  5. Cannot delete tags (MCP limitation) — record list for manual cleanup
```

### Step 4: knowledge-search — New Skill

**Structure** (following existing skill pattern with YAML frontmatter):
```
S1 — Parse Query Intent (keyword search / tag search / combined)
S2 — kb_search(query, top_k=15) for keyword search
S3 — kb_doc_get_by_tag(tag) for tag-based search  
S4 — Group results by KB
S5 — Present with score, KB name, snippet
```

### Step 5: Agent Routing Update

Add "Search" to Step 0 diagnostics + sub-skills table in agent definition.

### Step 6: One-Time Housekeeping

- Confirm deletion of Test-Scratch (empty KB)
- Detect orphan tags (already identified: `测试`, `turbine-test`)
- Clean up batch_parse_test images (already deleted)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| A0 dedup check false positive (different docs same name) | Skip valid new doc | Use content length comparison as secondary check |
| `kb_search()` returns stale file_size | Scorecard inaccuracy | Use `fs_get_children()` for real size (already documented) |
| C7 cannot delete orphan tags | Tags accumulate | Detect + report; document MCP limitation |
| New skill not registered until session restart | Cannot invoke | `/reload-skills` required |
| Scorecard arbitrary weights | Misleading metrics | Document that weights are heuristic |

## Acceptance Criteria (All Testable)

1. **A0**: Ingest a doc that already exists → Archival detects and warns
2. **B6**: Update a document's content → `kb_doc_read()` shows new content
3. **C6**: Run full organize → report includes numeric score
4. **C7**: Run tag audit → report correctly lists orphan tags
5. **Search**: Call `Skill("knowledge-search")` → loads with S1-S5 workflow
6. **Housekeeping**: Test-Scratch deleted, orphan tags identified

## Verification Steps

1. After writing all files: `grep` each new section to confirm presence
2. `Skill("knowledge-search")` — confirm it loads
3. `Skill("knowledge-ingest")` — confirm A0 appears
4. Agent definition — confirm "Search" added to Step 0
5. No leftover `spawn_agent()` references anywhere

## ADR

**Decision**: Implement all 6 enhancements as procedural additions to existing skill files + one new skill.
**Drivers**: Zero new MCP tools needed, no backend changes, no new dependencies.
**Alternatives**: Creating a separate "knowledge-quality" skill for audit — rejected because audit is already part of Organize workflow.
**Why chosen**: Each feature uses only existing MCP tools (`kb_search`, `kb_doc_read`, `kb_doc_update_content`, `kb_tags_list`, `kb_doc_get_by_tag`). Minimal blast radius.
**Consequences**: All features work immediately after `/reload-skills`. Scorecard weights are heuristic and may need tuning.
**Follow-ups**: If backend adds `kb_tag_delete`, extend C7 to actually clean tags.

## RALPLAN-DR Summary

**Principles**:
1. Zero new MCP tools or backend changes
2. Each feature must be testable in under 30 seconds
3. No breaking changes to existing skill dispatch routes

**Decision Drivers**:
1. User pain: duplicate docs are the #1 quality issue → dedup check highest priority
2. Efficiency: search needs a dedicated workflow, not just List edge case
3. Completeness: tag audit without delete is still valuable (visibility)

**Viable Options**:
- Option A (chosen): Add steps to existing skills + 1 new skill — minimal disruption
- Option B: Merge search into knowledge-list — rejected because List is read-only discovery, search needs distinct workflow
- Option C: Create standalone knowledge-quality skill — rejected because quality is already part of Organize (C-series)

**Pre-mortem — 3 Failure Scenarios**:
1. A0 dedup check fires on every ingest (too aggressive) → mitigation: check exact name match first, then content length
2. Scorecard weights criticized as arbitrary → mitigation: document clearly that weights are heuristic
3. User expects Search to modify KB → mitigation: CRITICAL banner "Read-only. Never modify."
