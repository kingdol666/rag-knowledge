---
name: knowledge-organize
description: >
  Knowledge base restructuring. Use when moving documents, merging KBs,
  renaming KBs or documents, deleting content, cleaning up collection.
  Triggered by "move this", "merge KBs", "rename", "delete KB", "clean up",
  "reorganize", "restructure", "整理知识库", "合并", "移动文档".
---

# Knowledge Organize

Spawn Archival. They handle all restructuring autonomously — moving,
merging, renaming, deleting with safety confirmation. The organize
procedure (Scenario B) is defined in their agent definition.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn with `=== TASK === SCENARIO: ORGANIZE. <user request> === MODE === interactive`.
3. Wait and relay results. Archival will confirm before destructive operations.
