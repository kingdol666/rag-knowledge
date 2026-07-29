# Skill Quality Optimization Goal

## Objective
Improve the quality, clarity, and effectiveness of all 14 Claude Code skills in the knowledge-base management system to achieve a composite skill quality score of ≥ 0.85 (baseline: ~0.62).

## Target Metric
`skill_quality_score` — a composite score (0-1) measuring:
1. **Description quality** (0.30): Does the description accurately trigger on relevant phrases? Is it specific and comprehensive?
2. **Progressive disclosure** (0.25): Does the skill use layered loading? Are sub-skills properly referenced?
3. **Workflow clarity** (0.20): Are the step-by-step instructions clear, actionable, and complete?
4. **Tool usage accuracy** (0.15): Are MCP tools referenced correctly with proper parameters?
5. **Conciseness** (0.10): Is the skill free of redundancy, filler, and unnecessary complexity?

## Target
Achieve average skill_quality_score ≥ 0.85 across all 14 skills.

## Scope
Only modify `.claude/skills/*/SKILL.md` files. Do not modify backend code, MCP server, or any other project code.

## Skills to Optimize (14 total)
- knowledgebase (dispatcher)
- knowledgebase-ingest (A0-A9 pipeline)
- knowledgebase-search (QDCVR retrieval)
- knowledgebase-search-enterprise (cross-KB search)
- knowledgebase-experience (experience lifecycle)
- knowledgebase-experience-summarize (meditation)
- knowledgebase-list (catalog viewing)
- knowledgebase-manage (document/KB admin)
- knowledgebase-organize (restructuring)
- knowledgebase-verify (integrity validation)
- knowledgebase-batch (batch operations)
- knowledgebase-graph (Neo4j operations)
- knowledgebase-init (installation)
- knowledgebase-update (version management)
