---
name: knowledge-discover
description: >
  Knowledge base discovery and search. Use when the user wants to list all KBs,
  search for documents, find content by tag, show what is in a KB, browse the
  collection, lookup specific documents, view the folder tree, or any task
  involving "list KBs", "show me", "what KBs do I have", "find documents about",
  "search knowledge base", "browse", "lookup", "what is in", "查看知识库", "搜索",
  "查找文档", "列出". Read-only operations that do not modify the collection.
---

# Knowledge Discover

Find and browse knowledge base content. Delegate ALL work to Archival.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn Archival with Scenario D (Discover) framing:

```
spawn_agent(
  agent_type="default",
  message="<FULL knowledge-admin.md>

=== TASK ===
SCENARIO D: DISCOVER. Find and present information from the knowledge base.

<the user's exact request>

This is read-only. Do not modify anything.",
  items=[{ type: "skill", name: "knowledge-discover", path: ".claude/skills/knowledge-discover/SKILL.md" }]
)
```

3. `wait_agent`, present results.
