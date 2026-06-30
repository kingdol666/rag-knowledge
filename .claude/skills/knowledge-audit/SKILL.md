---
name: knowledge-audit
description: >
  Knowledge base quality audit and maintenance. Use when the user wants to audit
  KB health, check for problems, find duplicate documents, review and fix tags,
  verify parse quality, clean up the knowledge base, run diagnostics, or any task
  involving "audit", "check health", "find duplicates", "fix tags", "clean up
  tags", "verify parse", "quality check", "diagnose", "审查知识库", "检查", "清理".
  Also handles proactive recommendations about KB health.
---

# Knowledge Audit

Audit and maintain knowledge base quality. Delegate ALL work to Archival.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn Archival with Scenario C+E (Maintain + Advise) framing:

```
spawn_agent(
  agent_type="default",
  message="<FULL knowledge-admin.md>

=== TASK ===
SCENARIO C+E: AUDIT & ADVISE. Perform quality maintenance on the knowledge base.

<the user's exact request or 'Full health audit of all KBs'>

Check for:
- Documents with no tags or empty descriptions
- Near-duplicate tags that should be consolidated
- KBs with no documents (stale)
- Parse quality issues in recent documents
- KBs with overlapping domains that could merge

After the audit, offer to fix any issues found.",
  items=[{ type: "skill", name: "knowledge-audit", path: ".claude/skills/knowledge-audit/SKILL.md" }]
)
```

3. `wait_agent`, present results with actionable recommendations.
