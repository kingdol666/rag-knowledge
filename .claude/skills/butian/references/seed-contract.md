# Seed Package Contract — The Unified Landing Format for Butian (补天) Distillation Artifacts

> Consumer: `ragctl soul distill` (command/ragctl.js) · Producers: dot-skill native /
> butian `nuwa_to_seed.py`. This contract is the single landing interface from
> "distillation artifacts → SOUL persona".

## 1. Directory Structure

```
seed-dir/
├── meta.json      # required — metadata (routing labels/impression)
├── persona.md     # required — identity/personality/expression style/honesty boundaries (→ soul-definition.md appended section)
├── work.md        # required — duties/thinking framework/decision heuristics/workflows (→ thinking-style.md appended section)
└── values.md      # optional — values and anti-patterns (→ values.md appended section, consumed via ragctl --values)
```

## 2. meta.json Fields

```json
{
  "slug": "steve-jobs",                    // KB name suffix: soul-<slug>
  "name": "Steve Jobs",                    // display name
  "display_name": "Steve Jobs",
  "character": "celebrity",                // colleague | relationship | celebrity
  "research_profile": "budget-unfriendly", // dot-skill compatibility field (default budget-friendly)
  "tags": { "personality": ["Steve Jobs", "聚焦即说不", "端到端控制"] },
  "impression": "乔布斯的思维框架与表达方式",  // first 12 chars participate in routing
  "source": "nuwa-skill"                   // producing engine (provenance)
}
```

- ragctl landing: `--name` defaults to `soul-<slug>`; `--labels` defaults to
  the first 3 of `tags.personality` + the first 12 chars of `impression`
- `impression` is also written into the KB description

## 3. persona.md Requirements (→ soul-definition.md)

- Content: identity card / role-play rules (summary) / expression DNA / honesty boundaries
- Landing fusion: `template soul-definition.md` + `# 补天蒸馏人格: <name>` (Butian-distilled persona) + persona.md
- **Template sections must be preserved** (the profile-summary generator and language-style parser
  depend on template structure); Butian content is appended sections only

## 4. work.md Requirements (→ thinking-style.md)

- Content: answering workflow (Agentic Protocol) / core mental models / decision heuristics /
  intellectual lineage / figure timeline (background) / failure modes and fallback rules
- Landing fusion: `template thinking-style.md` + `# 补天蒸馏工作方式: <name>` (Butian-distilled working style) + work.md

## 5. values.md (optional, Butian enhancement)

- Content: values and anti-patterns (what I pursue / what I reject / what I haven't thought through)
- Landing fusion: `template values.md` + `# 补天蒸馏价值观: <name>` (Butian-distilled values) + values.md
- **The constitutional layer is fixed once**: fused only at creation (ragctl --values); automated flows
  must not modify it after creation

## 6. Acceptance Criteria

| Check | Pass |
|---|---|
| meta.json is JSON.parse-able, slug non-empty | ✅ |
| persona.md / work.md non-empty | ✅ |
| tags.personality non-empty (otherwise ragctl falls back to --labels) | ✅ |
| ragctl soul distill outputs docs_created=4 + profile_summary_generated=true | ✅ |
| the new persona is visible in soul_list with correct domain_labels | ✅ |

## 7. Producer Alignment

| Producer | Alignment |
|---|---|
| dot-skill | Native artifacts are the contract (meta.json+persona.md+work.md); values.md is not produced |
| nuwa-skill | Converted via `python .claude/skills/butian/scripts/nuwa_to_seed.py <dir>`, additionally produces values.md |
| Backend text distillation | Skips the seed package; directly `ragctl soul distill-text/files` (LLM extracts persona/work/meta) |

## 8. Compatibility

- The ragctl contract reads only meta.json/persona.md/work.md → new fields/files do not break old artifacts
- Old dot-skill artifacts (no source field) → land normally (source defaults to "dot-skill")
- Seeds without values.md → ragctl omits --values, values stay pure template (behavior identical to existing)
