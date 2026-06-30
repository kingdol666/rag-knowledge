---
name: knowledge-organize
description: >
  Knowledge base organization and restructuring. Use when the user wants to move
  documents between KBs, merge knowledge bases, rename KBs or documents, delete
  KBs or documents, restructure the folder hierarchy, clean up the collection,
  or any task involving "move this", "merge KBs", "rename", "delete KB", "clean
  up knowledge base", "reorganize", "restructure", "整理知识库", "合并", "移动文档".
  All destructive operations require explicit user confirmation.
---

# Knowledge Organize

Restructure the knowledge base. Delegate ALL work to Archival.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn Archival with Scenario B (Organize) framing:

```
spawn_agent(
  agent_type="default",
  message="<FULL knowledge-admin.md>

=== TASK ===
SCENARIO B: ORGANIZE. Restructure the knowledge base as requested.

<the user's exact request>

IMPORTANT: Never delete a KB without explicit user confirmation.
List what will be lost and ask first.",
  items=[{ type: "skill", name: "knowledge-organize", path: ".claude/skills/knowledge-organize/SKILL.md" }]
)
```

3. `wait_agent`, present results.
