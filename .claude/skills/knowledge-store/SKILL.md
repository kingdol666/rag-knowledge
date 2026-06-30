---
name: knowledge-store
description: >
  The knowledge base administrator. Use for ANY knowledge-base-related task:
  storing documents, organizing KBs, maintaining quality, discovering content,
  or advising on KB health. Triggered by "store this", "parse to KB", "upload",
  "organize knowledge", "manage KB", "知识库", "文档入库", "what KBs do I have",
  "move this doc", "merge KBs", "clean up tags", "audit", "check KB health".
  Also serves as silent storage module for other skills/agents. When triggered,
  delegate the work to the Knowledge Administrator sub-agent (Archival) by
  spawning it with the full agent definition and the user's task.
---

# Knowledge Administrator — Dispatcher

This skill delegates knowledge-base work to a specialized sub-agent:
**Archival**, a senior knowledge architect with deep domain expertise.

**Do not execute knowledge-base tasks yourself.** Instead, spawn Archival
as a sub-agent who will handle the work autonomously.

---

## When to Trigger

This skill triggers for any knowledge-base management task. The user's
request will fall into one of these scenarios:

- **Ingest**: store, parse, upload, save, import, add document
- **Organize**: move, merge, rename, delete, restructure
- **Maintain**: audit, check health, find duplicates, fix tags, verify
- **Discover**: list, show, search, find, what do we have
- **Advise**: (proactive) the agent notices issues and recommends fixes

---

## How to Dispatch

When this skill triggers:

1. **Read the agent definition** from `.claude/agents/knowledge-admin.md`.
   This is Archival's complete identity, expertise, toolkit reference,
   and operating framework.

2. **Spawn the sub-agent** using `spawn_agent`:
   ```
   spawn_agent(
     agent_type="default",
     message="<Archival's full agent definition from knowledge-admin.md>

   === TASK ===
   <the user's exact request, with full context>",
     items=[{
       type: "skill",
       name: "knowledge-store",
       path: ".claude/skills/knowledge-store/SKILL.md"
     }]
   )
   ```

   The `message` field must contain:
   - The COMPLETE content of `.claude/agents/knowledge-admin.md`
   - A clear `=== TASK ===` separator
   - The user's request with all relevant context (file paths, KB names, etc.)

3. **Wait for the result.** Use `wait_agent` to get Archival's response.
   Then present the results to the user (or, in module mode, pass the
   JSON output to the calling skill).

---

## Module Mode (called by other skills)

When another skill or agent pipeline triggers knowledge-store:

1. Read `.claude/agents/knowledge-admin.md`
2. Spawn Archival with the calling skill's content as the task
3. The task message should include: "MODULE MODE. Operate silently.
   Store the following content: <content>. Return JSON summary only."
4. Wait for and relay the JSON output

---

## Important

- Always pass the FULL agent definition to Archival. Do not truncate.
- The agent definition contains Archival's complete toolkit reference,
  so the sub-agent will know exactly which MCP tools to use and when.
- Archival operates autonomously. Give clear tasks and let them work.
- For complex multi-step tasks (e.g., "audit all KBs then store these
  files"), pass the full scope in one message. Archival can handle it.
