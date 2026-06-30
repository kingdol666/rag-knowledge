---
name: knowledge-store
description: >
  Knowledge base management. Use for ANY knowledge-base task: storing documents,
  uploading files, parsing PDFs/DOCX/XLSX, importing content, organizing KBs,
  moving documents, merging knowledge bases, renaming, deleting, auditing health,
  finding duplicates, cleaning tags, verifying parse quality, searching,
  listing, discovering content, browsing KBs, finding documents. Triggered by
  phrases like "knowledge base", "KB", "知识库", "文档管理", "store this",
  "parse to KB", "upload", "organize knowledge", "audit", "find documents",
  "what KBs do I have", and any task involving kb-mcp tools. Spawns the
  Archival sub-agent to handle all work autonomously.
---

# Knowledge Base — Entry Point

Spawn Archival, the autonomous knowledge administrator sub-agent.
Do not handle KB tasks yourself.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md` completely.
2. Pass the FULL content as the `message` to spawn_agent, followed by:

```
=== TASK ===
<user's request with file paths and context>

=== MODE ===
<"interactive" for user-facing tasks, "MODULE MODE" for agent-to-agent calls>
```

3. `spawn_agent(agent_type="default", message="<above>")`.
4. `wait_agent`. Present Archival's response to the user or relay to caller.

Archival is fully autonomous. Do not micro-manage. Give clear context and
let them work. They will diagnose the scenario, survey the collection, and
execute the appropriate procedure from their agent definition.
