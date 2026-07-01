---
name: knowledge-store
description: >
  Knowledge base management — primary entry point. Use for ANY knowledge-base
  task: storing documents, uploading files, parsing PDFs/DOCX/XLSX/PPTX/images,
  importing content, organizing KBs, moving documents, merging KBs, renaming,
  deleting, auditing health, finding duplicates, cleaning tags, verifying parse
  quality, searching, listing, browsing. Triggered by: "knowledge base", "KB",
  "知识库", "文档管理", "store this", "parse to KB", "upload document",
  "import to KB", "save to KB", "organize knowledge", "audit KB", "find
  documents", "what KBs do I have", "show KB", "list KBs", "merge KBs",
  "delete KB", "整理", "入库", "上传", "搜索知识库", "查看", and any phrase
  referencing knowledge base operations, documents, tags, or parsing.
---

# Knowledge Base — Entry Point & Dispatcher

## For Main Claude (when triggered by user query)

Delegate all knowledge-base work to **Archival**, the autonomous knowledge
administrator subagent. Do not handle KB tasks yourself.

### Dispatch Procedure

1. Read `.claude/agents/knowledge-admin.md` (the Archival agent definition).
2. Use the `Agent` tool with `subagent_type: "archival"`:
   ```
   Agent(
     subagent_type="archival",
     prompt="<the user's full request, with file paths, descriptions, context>"
   )
   ```
3. Relay Archival's response to the user.

Do NOT add `=== SCENARIO ===` tags or hardcoded scenario hints. Archival
will diagnose the scenario autonomously.

### Multi-Scenario Dispatch Order

When the user's request covers multiple knowledge-base operations,
invoke Archival with scenarios ordered for maximum efficiency:

1. **Organize first** — Clean up the collection before new intake
2. **Ingest second** — New documents enter a clean, well-structured KB
3. **Manage third** — Post-ingest adjustments (move, rename, delete)
4. **List/Search last** — Present final state of the collection

This prevents Archival from moving documents twice (once during ingest,
once during organize). Describe the full workflow in a single prompt
so Archival can plan the entire session.

---

## For Archival (preloaded at subagent startup)

When you (Archival) are running and need to choose a sub-skill:

| You diagnosed | Invoke | Procedure |
|---|---|---|
| **Ingest** | `Skill("knowledge-ingest")` | Survey → classify → match KB → tag → write → verify |
| **Manage** | `Skill("knowledge-manage")` | Confirm → execute → verify |
| **Organize** | `Skill("knowledge-organize")` | Survey all → read content → categorize → execute → verify → report |
| **List** | `Skill("knowledge-list")` | Inventory → drill-down → tree |
| **Mixed** | Invoke in order: organize → manage → ingest → list | |

Each sub-skill contains the complete step-by-step procedure. Follow it
EXACTLY. Do not skip steps. If `Skill()` is unavailable, the full
procedures are in your agent definition.
