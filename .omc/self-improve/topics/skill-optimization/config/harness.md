# Self-Improve Guardrails — Skill Optimization

## H001: One Hypothesis Per Plan
Each plan MUST propose exactly ONE testable hypothesis about skill quality improvement. Reject plans with 0 or >1 hypotheses.

## H002: No Repetition Streak
No approach_family may be used for >= 3 consecutive winning iterations. Track history.

## H003: Intra-Round Diversity
No two plans in the same round may share the same approach_family tag.

## Approach Families for Skill Optimization
- `description_enhancement`: Improve skill description for better triggering
- `workflow_clarity`: Clarify step-by-step instructions and decision trees
- `progressive_disclosure`: Improve layered loading and sub-skill references
- `tool_accuracy`: Fix MCP tool references, parameters, and examples
- `conciseness`: Remove redundancy, simplify language, reduce token waste
- `cross_referencing`: Improve links between related skills
- `error_handling`: Add clear error recovery paths and fallback instructions

## Regression Protection
- Skill quality score must not decrease by more than 0.03 from best_score
- If any skill's individual score drops below baseline (0.62), reject the change
