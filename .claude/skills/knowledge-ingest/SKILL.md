---
name: knowledge-ingest
description: >
  Document ingestion into the knowledge base. Use when the user wants to store
  documents, parse files (PDF, DOCX, XLSX, PPTX, images), upload files to KB,
  import content, save text to knowledge base, add documents, batch-import, or
  any task involving "store this", "parse to KB", "upload document", "import",
  "save to knowledge base", "文档入库", "解析上传", "存入知识库". Handles
  format detection, KB matching, tag assignment, and description writing.
---

# Knowledge Ingest

Store documents into the knowledge base. Delegate ALL work to Archival.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn Archival with Scenario A (Ingest) framing:

```
spawn_agent(
  agent_type="default",
  message="<FULL knowledge-admin.md>

=== TASK ===
SCENARIO A: INGEST. Store the following content into the knowledge base.

Content: <file paths, in-memory text, or URLs the user provided>

Instructions:
- Detect format. Parse PDF/DOCX/XLSX/PPTX/images via parse_pdf_to_kb.
  Direct-upload MD/TXT/CSV/JSON via kb_doc_create.
- Survey existing KBs with kb_list(). Match by domain.
- If no matching KB, create one with a proper description.
- Load kb_tags_list() before tagging. Reuse existing tags.
- Write content-based descriptions — read the content, do not guess.
- For each parse task, note the task_id. Poll with parse_task_status.
- Report: which file went to which KB, with which tags.

<the user's exact request>",
  items=[{ type: "skill", name: "knowledge-ingest", path: ".claude/skills/knowledge-ingest/SKILL.md" }]
)
```

3. `wait_agent`, present results.

## Module Mode

Silent JSON output. Pass "MODULE MODE" in the task message.
