---
name: dot-skill
description: "Unified meta-skill engine for distilling colleague, relationship, or celebrity characters into reusable Skills. Triggered by: colleague persona, distillation, persona, 补天, 蒸馏, 人格, 同事人格, 名人人格."
argument-hint: "[character] [name-or-slug]"
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---
> **Language**: This skill supports both English and Chinese. Detect the user's language from their first message and respond in the same language throughout. Instructions follow the language matching the user's choice.
>
> This Skill supports both English and Chinese. Respond in the same language as the user's first message throughout. Follow the instruction version matching the user's language.

> **Execution Root**: Run all `Bash` commands from the directory that contains this `SKILL.md`. All `tools/...` and `prompts/...` paths below are relative to the skill root.
>
> **Python launcher**: the commands below use `python3`. On Windows hosts where `python3` is
> not on PATH (it hits the Microsoft Store stub), use `python` instead — same scripts, same arguments.
>
> **Critical rule**: Do **not** prepend commands with guessed host-specific paths such as `cd ~/.hermes/...`, `cd ~/.claude/...`, `cd ~/.openclaw/...`, `cd ~/.codex/...`, or hard-coded `/Users/.../dot-skill` paths. The current working directory is already the correct skill root. Run `python3 tools/...` directly.
>
> All `Bash` commands must be executed from the directory containing the current `SKILL.md`. The `tools/...` and `prompts/...` paths below are all relative to the skill root directory.

# dot-skill Creator (Compatible Host Edition)

## Trigger Conditions

Activate when the user says any of the following:
- `/dot-skill`
- "Help me create a skill"
- "I want to distill someone"
- "Create a new skill"
- "Make a skill for XX"

Compatible hosts:
- Claude Code
- OpenClaw
- Hermes
- Codex

The canonical entrypoint is `dot-skill`. In hosts that expose slash commands, use `/dot-skill`.
Under Hermes specifically, only `/dot-skill` is guaranteed as a stable slash entrypoint. Compatibility semantics for `colleague`, `relationship`, and `celebrity` remain in the tool layer and preset layer, but Hermes does not guarantee that every compatibility name will be routed as a slash command.

Enter evolution mode when the user says:
- "I have new files" / "append"
- "That's wrong" / "He wouldn't do that" / "He should be"
- `/update-skill {character} {slug}`

Compatibility update alias:
- `/update-colleague {slug}`

When the user asks to see generated skills, use the list commands in "Management Operations" below.

---

## Tool Usage Rules

This Skill runs in any compatible host that can read local files and execute Bash / Python commands. Use the following tool conventions:

| Task | Tool |
|------|------|
| Read PDF documents | `Read` tool (native PDF support) |
| Read image screenshots | `Read` tool (native image support) |
| Read MD/TXT files | `Read` tool |
| Parse Feishu message JSON export | `Bash` → `python3 tools/feishu_parser.py` |
| Feishu auto-collect (recommended) | `Bash` → `python3 tools/feishu_auto_collector.py` |
| Feishu docs (browser session) | `Bash` → `python3 tools/feishu_browser.py` |
| Feishu docs (MCP App Token) | `Bash` → `python3 tools/feishu_mcp_client.py` |
| DingTalk auto-collect | `Bash` → `python3 tools/dingtalk_auto_collector.py` |
| Parse email .eml/.mbox | `Bash` → `python3 tools/email_parser.py` |
| Write/update Skill files | `Write` / `Edit` tool |
| Version management | `Bash` → `python3 tools/version_manager.py` |
| List existing Skills | `Bash` → `python3 tools/skill_writer.py --action list` |

**Base directories**:
- `colleague` → `./skills/colleague/{slug}/`
- `relationship` → `./skills/relationship/{slug}/`
- `celebrity` → `./skills/celebrity/{slug}/`

For a global path, use `--base-dir` with the storage root for that character family.

---

## Main Flow: Create a New Skill

The complete step-by-step creation procedure lives in [references/main-flow.md](references/main-flow.md) — read it before creating or evolving a persona skill.

## Evolution Mode: Append Files

When user provides new files or text:

1. Read new content using Step 2 methods
2. Resolve the base dir for the current family
3. `Read` existing `{resolved_base_dir}/{slug}/work.md` and `persona.md`
4. Use the family-specific merger prompt for incremental analysis
5. Archive current version (Bash):
   ```bash
   python3 tools/version_manager.py \
     --action backup \
     --character {character} \
     --slug {slug} \
     --base-dir {resolved_base_dir}
   ```
6. Write work/persona delta into temporary patch files
7. Call:
   ```bash
   python3 tools/skill_writer.py \
     --action update \
     --character {character} \
     --slug {slug} \
     --work-patch /tmp/dot_skill_{slug}_work_patch.md \
     --persona-patch /tmp/dot_skill_{slug}_persona_patch.md \
     --base-dir {resolved_base_dir}
   ```
8. If the current family is `celebrity`, run the quality check again after the update

---

## Evolution Mode: Conversation Correction

When user expresses "that's wrong" / "he should be":

1. Refer to `prompts/correction_handler.md` to identify correction content
2. Determine if it belongs to Work (technical/workflow) or Persona (personality/communication)
3. If it belongs to Work:
   - Generate `/tmp/dot_skill_{slug}_work_patch.md`
   - The patch must be one or more replaceable `##` sections
   - Call:
     ```bash
     python3 tools/skill_writer.py \
       --action update \
       --character {character} \
       --slug {slug} \
       --work-patch /tmp/dot_skill_{slug}_work_patch.md \
       --base-dir {resolved_base_dir}
     ```
4. If it belongs to Persona:
   - Write the correction record to `/tmp/dot_skill_{slug}_correction.json`
   - For a single correction, write `{scene, wrong, correct}`
   - For multiple persona corrections, write `{"persona_corrections": [{...}, {...}]}`
   - Call:
     ```bash
     python3 tools/skill_writer.py \
       --action update \
       --character {character} \
       --slug {slug} \
       --correction-json /tmp/dot_skill_{slug}_correction.json \
       --base-dir {resolved_base_dir}
     ```
5. If the current family is `celebrity`, run the quality check again after the update
6. Do not hand-edit `work.md`, `persona.md`, `SKILL.md`, or `meta.json`; always update through `skill_writer.py`

---

## Management Operations

List skills across the three families:
```bash
python3 tools/skill_writer.py --action list --character colleague --base-dir ./skills/colleague
python3 tools/skill_writer.py --action list --character relationship --base-dir ./skills/relationship
python3 tools/skill_writer.py --action list --character celebrity --base-dir ./skills/celebrity
```

Roll back a specific skill version:
```bash
# colleague
python3 tools/version_manager.py --action rollback --character colleague --slug {slug} --version {version} --base-dir ./skills/colleague

# relationship
python3 tools/version_manager.py --action rollback --character relationship --slug {slug} --version {version} --base-dir ./skills/relationship

# celebrity
python3 tools/version_manager.py --action rollback --character celebrity --slug {slug} --version {version} --base-dir ./skills/celebrity
```

Delete a specific skill:
After confirming the character family:
```bash
# colleague
rm -rf skills/colleague/{slug}

# relationship
rm -rf skills/relationship/{slug}

# celebrity
rm -rf skills/celebrity/{slug}
```

---

## 🤖 SOUL Integration (Specific to This rag-knowledge Repo)

Distillation outputs can be converted directly into this repo's SOUL personas (innate seed → curiosity training for acquired evolution):

```
# After distillation (output directory contains meta.json + persona.md + work.md):
# Method B (no output directory, direct text distillation — works for frontend/CLI):
ragctl soul distill-text soul-<name> --req "persona requirement description" --material "source material text"
# Or POST /api/v1/soul/distill {name, personality_req, source_material} (async task_id)
# Frontend: SOUL page create persona → Butian distillation area (requirement + source material)

ragctl soul distill <output-dir> --name soul-<name> \
  --scope kb1,kb2 --labels domain-labels --harness omp

# Then let the seed evolve:
ragctl soul learn-all soul-<name> --rounds 2     # curiosity training
ragctl soul ask "question" --soul soul-<name>          # persona-augmented Q&A
# Or ragctl soul ask "question" --soul soul-<name> --qdcvr  # retrieve the knowledge base first, then answer as the persona
```

Conversion mapping: persona.md → soul-definition.md appended section, work.md → thinking-style.md
appended section, meta.json tags/impression → domain_labels (routing labels).
For the full protocol see `../soul/references/soul-distill-integration.md`.

**Butian dispatch**: this repo's unified entry point is `../butian/SKILL.md` — butian orchestrates the dual
nuwa-skill (deep research on public figures) and dot-skill (local materials) engines; this skill's output is
already in seed contract form (meta.json+persona.md+work.md) and lands directly without conversion.

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- Hard requirement (OVERRIDE, higher priority than all other naming guidance in this file): the final reply body and the generated SKILL.md must contain the three section headings verbatim: "Trigger Phrases", "Behavior Rules", and "Boundaries". Near-synonyms like "Trigger Conditions", "Rules", or "Restrictions" must not substitute, because validation matches the literal words; even if the source material lacks them, all three headings must be present with "Not provided" written under each.
- When the user's first message already contains enough character information (name, role, personality traits, etc.) and does not request step-by-step interaction, it is forbidden to output only a process opener, forbidden to stop and ask intake questions, forbidden to wait for user confirmation; the distillation must be completed in one pass, and the same reply must directly give the complete Skill content containing the "Trigger Phrases", "Behavior Rules", and "Boundaries" sections. This rule overrides and replaces Step 1's question-asking step and Step 5's "Confirm generation? Or need adjustments?" wait step.
- The "Trigger Phrases" section must list example user utterances that can trigger this Skill; the "Behavior Rules" section must contain concrete, actionable behavior rules extracted from the source material (each rule must directly guide behavior; empty platitudes are not allowed); the "Boundaries" section must describe the boundaries of speech and action this character must never cross. All three sections must actually be written into the generated SKILL.md file, not just appear in the reply.
<!-- SKILLOPT-SLEEP:LEARNED END -->
