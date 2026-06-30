---
name: knowledge-ingest
description: >
  Document ingestion. Use when storing documents, parsing files (PDF, DOCX,
  XLSX, PPTX, images), uploading to KB, importing content, saving text to
  knowledge base, adding documents, batch-import. Triggered by "store this",
  "parse to KB", "upload document", "import", "save to KB", "文档入库", "解析上传".
---

# Knowledge Ingest

Spawn Archival. They handle all ingestion autonomously — format detection,
KB matching, tag selection, description writing. The ingest procedure
(Scenario A) is defined in their agent definition at `.claude/agents/knowledge-admin.md`.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn with `=== TASK === SCENARIO: INGEST. <user request> === MODE === interactive`.
3. Wait and relay results.
