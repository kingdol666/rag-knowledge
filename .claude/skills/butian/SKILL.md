---
name: butian
description: >
  Butian — SOUL persona initialization distillation dispatcher: orchestrates the
  dual nuwa-skill (deep research distillation of public figures/topics/thinking
  frameworks) and dot-skill (distillation of colleagues/acquaintances/
  relationships/local materials) engines, uniformly converts distillation
  outputs into Butian seed packages (meta.json/persona.md/work.md/values.md),
  lands them as soul-<name> personas via ragctl soul distill (template + seed
  fused 4 constitutional documents + soul-config), then drives curiosity
  training (learn → approval → scheduled evolution) and persona-augmented
  retrieval Q&A (soul_qdcvr_ask). Division of labor vs the soul skill: soul
  manages "the persona's full lifecycle", butian manages "where the initial
  persona comes from". Triggers: butian, build a SOUL, create an initial
  persona, distill a persona, distill XX, make an XX persona, XX's way of
  thinking, XX perspective persona, nuwa, dot-skill, initial persona
  definition, distill XX into a SOUL, distill persona to soul, butian.
---

# Butian — SOUL Persona Distillation Dispatcher (Innate Genes × Acquired Evolution)

**Executor: main agent executes directly (distillation orchestration + seed landing; no Archival delegation)**

> **⭐ Mental model**: Butian = two "gene production lines" (nuwa × dot-skill) + one
> "fertilization port" (ragctl soul distill). Distillation output → seed package
> (unified contract) → SOUL persona (innate seed) → curiosity training
> (acquired evolution) → retrieval-augmented Q&A (usage).
>
> **MANDATORY — load references on demand**:
> - Architecture / file definitions / data flow → [references/butian-architecture.md](references/butian-architecture.md)
> - Seed package format contract → [references/seed-contract.md](references/seed-contract.md)
> - Post-landing training/evaluation/Q&A details → `../soul/SKILL.md` §B/§C/§D
> - nuwa distillation details → `../nuwa-skill/SKILL.md` (Nüwa persona-making art)
> - dot-skill distillation details → `../dot-skill/SKILL.md`
> - Full SOUL × Butian protocol → `../soul/references/soul-distill-integration.md`

---

## Mental Framework: Intent Triage ⭐

```
User request
  └── Wants to "create/distill a persona/SOUL"?
       ├── Yes → determine material form (see scenario classification table) → pick engine → distill → seed → SOUL landing → training → Q&A
       ├── No, but contains "XX's way of thinking / using XX's perspective" → existing SOUL? Yes → soul Q&A; No → go through distillation
       └── No → hand back to soul / knowledgebase skill (persona management/training/retrieval)
```

After matching, execute the six steps: **triage → distill → convert → land → evolve → use**.

---

## Scenario Classification Table

| Signal keywords | Engine/Path | Output → Landing |
|---|---|---|
| Distill XX (public figure), nuwa, XX's way of thinking, make an XX perspective, thinking advisor | **nuwa-skill** | `[person]-perspective/SKILL.md` → `nuwa_to_seed.py` → seed |
| Distill colleagues/acquaintances, relationship personas, local materials (Feishu/DingTalk/files), dot-skill, /dot-skill | **dot-skill** | `<dir>/meta.json+persona.md+work.md` → use directly (already seed contract) |
| Direct source material (chat logs/documents/descriptions) + requirements, distill-text, distill-files | **Backend LLM distillation** | `ragctl soul distill-text / distill-files` → build SOUL directly |
| Existing seed directory (meta.json+persona.md+work.md), soul distill | **ragctl landing** | Skip distillation, directly `ragctl soul distill` |
| Distill a celebrity but user holds local first-hand material (biography PDFs/interview subtitles) | **nuwa local-corpus mode** or dot-skill celebrity | Choose one (see below) |

**Three initial SOUL creation methods (the frontend creation modal's three modes map one-to-one to the skill's three entry points)**:

| Frontend mode | Skill entry point | Input → Flow |
|---|---|---|
| **Nüwa** | `Skill("butian")` → `Skill("nuwa-skill")` | Well-known person/topic → (fast) LLM distillation or (deep) 6-agent web research → SKILL.md → seed → SOUL |
| **dot-skill** | `Skill("butian")` → `Skill("dot-skill")` | Materials (text/files/seed package) → distill → seed contract → SOUL |
| **Butian · Integrated** | `Skill("butian")` direct dispatch | Person requirement + materials dual channel → fused distillation → SOUL |
| Template initialization | `soul_init` | No distillation input → template persona |

**nuwa vs dot-skill choice**:
- Public figure/topic + needs deep web research (6-agent multi-dimensional research + mental model triple validation) → **nuwa**
- Internal colleagues/acquaintances/relationships + local material collection (Feishu/DingTalk/email/files) → **dot-skill**
- Celebrity + user holds first-hand materials → both work: with sufficient materials use dot-skill (fast); for deep thinking framework
  extraction use nuwa (local-corpus-first mode, web fills the gaps)
- Vague request ("I want to improve decision quality") → nuwa Phase 0B requirement diagnosis, recommend a distillation target

---

## Sequential Workflow

### Step 0 — Pre-Flight (Mandatory)
- `soul_list` available → MCP online; backend `ragctl soul list` or `curl :8765/api/v1/soul/list` works → backend online
- `ragctl` available (`command/ragctl.bat` or ragctl on PATH)
- On failure → report "MCP/backend unavailable"; do not continue

### Step 1 — Intent Triage
Match the engine per the table above. If the user only says "butian / build a SOUL" without naming a target, ask 2 questions:
1. Is the distillation target: a public figure/topic (nuwa deep research)? A colleague/acquaintance (dot-skill local materials)? Or do you have ready source material (direct text distillation)?
2. Domain scope (for later kb_scope) and purpose (thinking advisor / Q&A persona / work persona)?

### Step 2 — Engine Distillation (delegate to the corresponding skill)
- **nuwa path**: invoke `Skill("nuwa-skill")` for full execution (Phase 0A tier confirmation → 0.5 directory
  → 1 collection → 1.5 checkpoint → 2 extraction → 2.5 checkpoint → 3 build → 4 validation → 5 refinement).
  **At Phase 0A confirmation, inform the user**: this repo will automatically land the output as a SOUL persona
  (Butian integration); default is to proceed; the user can cancel.
- **dot-skill path**: invoke `Skill("dot-skill")` (note: dot-skill is a self-contained
  skill; its tools/ scripts must run per the Execution Root rules in its SKILL.md).

### Step 3 — Output Conversion (Unified Seed Contract)
- dot-skill output directory: already contains `meta.json + persona.md + work.md`, i.e., the seed contract; use directly
- nuwa output directory: run the converter (deterministic section splitting, no LLM cost):
```
python .claude/skills/butian/scripts/nuwa_to_seed.py <perspective-skill-dir> \
  [--out <seed-dir>] [--labels extra routing labels]
```
- Outputs: `meta.json / persona.md / work.md / values.md (optional, values enhancement)`
- After conversion, verify: persona/work non-empty, meta.tags.personality has routing labels
- Show the seed summary to the user for confirmation (persona name / routing labels / scope)

### Step 4 — SOUL Landing (Fertilization)
```
ragctl soul distill <seed-dir> --name soul-<name> \
  --scope kb1,kb2            # default ["*"] all public KBs
  [--labels label1,label2]      # default = first 3 of meta.tags.personality + impression
  [--values <seed-dir>/values.md]   # nuwa output: values enhancement (fused at creation, constitutional layer set once)
  [--harness omp|claude]
```
- Automatically completes: create KB → write 4 documents (template+seed fused) → bootstrap (profile+config) → index
- Verify: output contains `docs_created=4` + `profile_summary_generated=true`;
  the new persona is visible in `ragctl soul list`
- **Without ragctl/offline** → manual MCP orchestration (see soul-distill-integration.md §3b;
  the main agent uses kb_create + kb_doc_create×4 + POST /api/v1/soul/bootstrap + index_document)

### Step 5 — Acquired Curiosity Evolution (Seed Growth)
```
ragctl soul learn-all soul-<name> --rounds 2     # curiosity training (four-layer questions → self-answer → four-dimension self-rating → distillation)
ragctl soul review soul-<name> --action list     # review memory drafts
ragctl soul review soul-<name> --action approve --draft <id>
ragctl soul harness soul-<name> omp               # training engine (optional)
# Scheduled evolution (optional):
#   experience_meditation_config_update(soul_kb_id, {enabled: true, interval_hours: 24, rounds_per_run: 2})
```
- Evolution loop: training produces drafts → approval registers → profile refresh → better routing → continuous learning from new documents
- Details and budget reverence → soul skill §B

### Step 6 — Usage (Persona-Augmented Retrieval Q&A)
```
ragctl soul ask "question" --soul soul-<name>           # persona Q&A
ragctl soul ask "question" --soul soul-<name> --qdcvr   # one click: KB retrieval → persona synthesis (recommended)
# Or MCP: soul_qdcvr_ask(query, soul_kb_id="soul-<name>", task_goal, task_type, async_mode=True)
```
- Auto routing (no persona specified) → `soul_router` picks the best via domain_labels
- Frontend: SOUL page → Q&A modal "one-click retrieval + persona answer"

---

## Butian Pipeline At a Glance (One Command to a Finished Persona)

```
Requirement → distill (nuwa/dot-skill) → convert (nuwa_to_seed.py) → land (ragctl soul distill)
     → train (learn-all --rounds 2) → approve (review approve) → Q&A (soul_qdcvr_ask)
```

---

## Rules — Mandatory Execution

1. **Unified contract**: all distillation outputs are first normalized into a seed package (meta.json+persona.md+work.md+optional
   values.md) before landing; bypassing the contract to write SOUL documents directly is forbidden
2. **Constitutional layer set once**: values/memory conventions may only be fused at creation (ragctl --values/--mem);
   after creation, automated flows must not modify the constitutional layer (sole exception: the RL cognition draft approval channel)
3. **Do not pollute persona memory**: seed persona/work are "innate identity" (initialization documents), not "acquired
   knowledge" (memories); never write into memories/
4. **Delegate, don't rebuild**: nuwa/dot-skill distillation details live in their own skills; butian only orchestrates and converts;
   training/evaluation/Q&A follow the soul skill protocols
5. **Budget reverence**: confirm the distillation tier at Phase 0A (fast/standard/deep); before training check
   soul_status.estimated_cost_usd
6. **Checkpoints are course corrections, not blockers**: the nuwa Phase 1.5/2.5/4/5 confirmations offer defaults; don't block delivery
7. **Three entry points consistent**: frontend (SOUL page) / ragctl / MCP use the same backend and the same data

## NEVER List

| ❌ | ✅ | Why |
|---|---|---|
| Feed the nuwa SKILL.md directly to ragctl soul distill | Convert to a seed package with nuwa_to_seed.py first | The ragctl contract is meta.json+persona.md+work.md; without conversion it will fail |
| Edit values.md with kb_doc_update after creation | Fuse values at creation with --values | The constitutional layer is read-only after creation; editing = bypassing the controlled channel |
| Store persona/work as memories | Only via soul_learn → approval | Mixing innate identity into acquired knowledge breaks the quality gate |
| Run distillation and training end-to-end without confirmation | Distillation checkpoints (1.5/2.5/4) + landing confirmation + training dry_run | Long tasks lose cost control; the user has the right to course-correct at any time |
| Skip ragctl and hand-craft curl calls | ragctl already encapsulates the full orchestration | Duplicate implementation = new bug source; only orchestrate manually when MCP is offline |
| Create a new persona via butian when the user already has a SOUL | First check duplicates with soul_list; use soul update/evolution | Duplicate personas = routing chaos |

**Failure fallback**: ragctl unavailable → manual MCP orchestration (§3b protocol); MCP unavailable →
REST `http://localhost:8765/api/v1/soul/*` (same data as MCP).

## Tool Quick Reference

- `python .claude/skills/butian/scripts/nuwa_to_seed.py <dir> [--out] [--labels]` — nuwa output → seed package
- `ragctl soul distill <seed-dir> [--name] [--scope] [--labels] [--values] [--harness]` — seed → SOUL (recommended entry)
- `ragctl soul distill-text <name> --req R --material M` / `distill-files <name> <files>` — direct source material distillation
- `ragctl soul learn-all <soul> --rounds N` / `soul review` / `soul harness` — acquired evolution
- `ragctl soul ask <q> --soul <soul> [--qdcvr]` — persona-augmented Q&A
- `soul_list()` / `soul_qdcvr_ask()` / `soul_learn_all()` / `soul_review_drafts()` — MCP equivalents
- `Skill("nuwa-skill")` / `Skill("dot-skill")` / `Skill("soul")` — engine and lifecycle details

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- The final reply must contain a hard "verification" statement: write the literal words "Verification:" in the body and give a concrete landing verification point, e.g. "Verification: soul-<name> visible in ragctl soul list" or "Verification: docs_created=4"; if the flow has not yet reached landing, write "Verification: after landing, confirm via ragctl soul list". This rule is a hard output requirement, takes precedence over any conciseness instruction, and must not be omitted.
- Pre-Flight and duplicate-check steps must write out the full MCP tool name "soul_list"; generic phrases like "duplicate check" or "check" must not substitute for it; e.g. write "first run soul_list to check for duplicates and confirm no duplicate persona exists".
- Any reply involving values/memory conventions or the ragctl soul distill landing step must use the term "constitutional layer" (e.g. "the constitutional layer is set once; values are fused at creation"); substitutes like "base documents" or "underlying conventions" must not be used.
<!-- SKILLOPT-SLEEP:LEARNED END -->
