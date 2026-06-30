---
name: knowledge-store
description: >
  Knowledge base management. Use for ANY knowledge-base-related task including
  storing documents, uploading files, parsing PDFs, importing content, organizing
  KBs, moving documents, merging knowledge bases, renaming, deleting, auditing
  health, finding duplicates, cleaning tags, verifying parse quality, searching,
  listing, discovering content, browsing KBs, finding documents. Triggered by
  "knowledge base", "KB", "知识库", "文档管理", "knowledge management", or any
  task involving kb-mcp tools. When triggered, route to the appropriate scenario
  sub-skill (ingest/organize/audit/discover) or spawn Archival directly.
---

# Knowledge Base — Master Router

You are the entry point for ALL knowledge-base operations. When this skill
triggers, your job is to route the user's intent to the correct handler.

## Routing Table

| User intent | Route to |
|---|---|
| Store, upload, parse, import, save, add document | `knowledge-ingest` skill |
| Move, merge, rename, delete, restructure, clean up | `knowledge-organize` skill |
| Audit, check health, find duplicates, fix tags, verify quality | `knowledge-audit` skill |
| List, search, find, show, browse, lookup, what KBs | `knowledge-discover` skill |
| Unclear / mixed / general KB question | Spawn Archival directly |

## How to Route

For sub-skill routing, simply state which sub-skill should handle the request.
The sub-skill's description will trigger and its SKILL.md will handle the rest.

For direct Archival spawn:

1. Read `.claude/agents/knowledge-admin.md` — Archival's full identity.
2. Spawn:
```
spawn_agent(
  agent_type="default",
  message="<FULL content of knowledge-admin.md>

=== TASK ===
<user's exact request with context>",
  items=[{ type: "skill", name: "knowledge-store", path: ".claude/skills/knowledge-store/SKILL.md" }]
)
```
3. `wait_agent` for results, present to user.

## Module Mode

When called by another skill/agent, spawn Archival silently with:
"MODULE MODE. Operate silently. <content>. Return JSON only."
