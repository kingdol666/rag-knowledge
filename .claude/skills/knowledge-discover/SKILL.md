---
name: knowledge-discover
description: >
  Knowledge base discovery and search. Use when listing KBs, searching for
  documents, finding content by tag, showing KB contents, browsing collection,
  looking up documents, viewing folder tree. Triggered by "list KBs", "show me",
  "what KBs do I have", "find documents about", "search knowledge base",
  "browse", "lookup", "what is in", "查看知识库", "搜索", "查找文档", "列出".
  Read-only operations.
---

# Knowledge Discover

Spawn Archival. They handle all discovery autonomously — inventory,
drill-down, search, tree view. The discover procedure (Scenario D)
is defined in their agent definition.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn with `=== TASK === SCENARIO: DISCOVER. <user request> === MODE === interactive`.
3. Wait and relay results. Read-only, no modifications.
