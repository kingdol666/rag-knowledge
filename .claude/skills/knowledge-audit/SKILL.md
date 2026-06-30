---
name: knowledge-audit
description: >
  Knowledge base quality audit and maintenance. Use when auditing KB health,
  checking for problems, finding duplicate documents, reviewing/fixing tags,
  verifying parse quality, cleaning up, running diagnostics. Triggered by
  "audit", "check health", "find duplicates", "fix tags", "clean up tags",
  "verify parse", "quality check", "diagnose", "审查知识库", "检查", "清理".
---

# Knowledge Audit

Spawn Archival. They handle all quality work autonomously — tag audits,
description reviews, duplicate detection, parse verification, health
reports. The audit procedure (Scenario C) is defined in their agent definition.

## Dispatch

1. Read `.claude/agents/knowledge-admin.md`.
2. Spawn with `=== TASK === SCENARIO: AUDIT. <user request or 'Full health audit'> === MODE === interactive`.
3. Wait and relay results with actionable recommendations.
