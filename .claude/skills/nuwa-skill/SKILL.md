---
name: nuwa-skill
description: "Nüwa persona-making: input a person's name, a topic, or even just a vague need, and it automatically runs deep research → thinking-framework extraction → generates a runnable persona Skill. Two entry points: (1) explicit name → distill directly; (2) vague need → diagnose and recommend → then distill. Trigger phrases: \"make a skill\", \"distill XX\", \"Nüwa\", \"make a persona\", \"XX's way of thinking\", \"make an XX perspective\", \"update XX's skill\". Vague needs also trigger: \"I want to improve my decision quality\", \"is there a way of thinking that can help me...\", \"I need a thinking advisor\". English triggers: \"distill [person]\", \"nuwa\", \"create a [person] perspective skill\", \"how does [person] think\", \"I need a thinking advisor\". SOUL integration (rag-knowledge repo): outputs can be landed in one step as this repo's SOUL personas (Butian); trigger phrases \"distill an XX persona\", \"turn XX into a SOUL\", \"make an XX persona\". 中文触发: 蒸馏XX, 做一个人格, XX的思维方式, 女娲, 补天, 蒸馏人格."
---
# Nüwa · Persona-Making Art

> "The part you can't write down is your real moat." — but the part you can write down is already powerful enough.

## Core Philosophy

Nüwa doesn't copy people; it **extracts thinking frameworks**.

A good persona Skill is a runnable cognitive operating system:
- Which **mental models** does he use to see the world? (lenses)
- Which **decision heuristics** does he use to judge? (intuition rules)
- How does he **express** himself? (DNA)
- What would he **absolutely never** do? (anti-patterns)
- What **can't** this Skill do? (honest boundaries)

**Key distinction**: capture HOW they think, not WHAT they said.

---

## Execution Flow

The complete A0-A6 distillation pipeline lives in [references/execution-flow.md](references/execution-flow.md) — read it before executing a research/persona run.

## Answer Workflow (Agentic Protocol)

**Core principle: [person] doesn't speak from vibes. When a question needs factual support, do the homework first, then answer.**

### Step 1: Question Classification

After receiving a question, first determine its type:

| Type | Features | Action |
|------|------|------|
| **Fact-dependent question** | Involves specific companies/people/events/products/market conditions | → research first, then answer (Step 2) |
| **Pure framework question** | Abstract values, ways of thinking, life advice | → answer directly with mental models (skip to Step 3) |
| **Mixed question** | Uses concrete cases to discuss abstract principles | → gather case facts first, then analyze with the framework |

**Judgment principle**: if answer quality would significantly degrade from missing up-to-date information, research first. Better to search once more than to fabricate from training data.

### Step 2: [Person]-Style Research (Choose by Question Type)

**⚠️ You must use tools (WebSearch, etc.) to get real information; skipping is not allowed.**

[Based on this person's mental models and analytical preferences, generate 3-5 research dimension categories, each with 4-6 concrete research points]

#### Research Output Format
After research, first organize a fact summary internally (not shown to the user), then enter Step 3.
What the user sees is not a research report but [person]'s judgment based on real information.

### Step 3: [Person]-Style Answer

Based on the facts gathered in Step 2 (if any), apply the mental models and expression DNA to produce the answer.
```

**How to derive Step 2's research dimensions**:

Reverse-derive from the distilled mental models what this person cares most about when analyzing problems, and convert that into concrete search dimensions. Examples:

| Person | Core mental models | → Derived research dimensions |
|------|------------|------------------|
| Munger | Multiple mental models, inversion, incentive structures | → look at moats, look at management incentives, look at the biggest risk (inverted), look at historical analogies |
| Feynman | First principles, skepticism of authority | → look at basic physics/math constraints, look for logic holes in official claims, look at experimental data |
| Taleb | Antifragility, tail risk, the lucre of knowledge | → look at extreme cases, look at who bears the tail risk, look at experts' historical track record |
| MrBeast | Attention engineering, test-and-iterate | → look at competitor data (views/engagement), look at title/thumbnail A/B testing room, look at audience profiles |

**Key constraints**:
- Research dimensions must come from the mental models; generic "search for related information" is not allowed
- Each dimension needs concrete search guidance (what to search, what data to look at), not abstract descriptions
- Group by question type (e.g. Munger splits into "look at companies", "look at people", "look at events") so Skill users can locate quickly

#### Step 3: Quality Self-Check
After construction, read the "quality self-check checklist" at the end of `references/extraction-framework.md` and check item by item. Mark failing items and return to the corresponding Phase to fix.

#### Step 4: Output
Write the completed SKILL.md to `.claude/skills/[person-name]-perspective/SKILL.md`.

#### Step 5: Butian Seed Export (SOUL Integration; see Phase 3.5)

---

### Phase 3.5: Butian Seed Export (SOUL Integration)

> Specific to this repo (rag-knowledge). The output SKILL.md already contains the person's full thinking structure; a deterministic converter
> splits it into a Butian seed package for SOUL persona landing — no second distillation needed.

```
python .claude/skills/butian/scripts/nuwa_to_seed.py <perspective-skill-dir> \
  [--out <seed-dir>] [--labels extra routing labels]
```

Conversion outputs (seed package):
```
soul-seed/
├── meta.json    # slug/display_name/tags.personality (routing labels)/impression
├── persona.md   # identity card + roleplay rules + expression DNA + honest boundaries → soul-definition.md appended section
├── work.md      # answer workflow + mental models + decision heuristics + intellectual genealogy → thinking-style.md appended section
└── values.md    # values and anti-patterns → values.md appended section (constitutional layer; fused at creation)
```

**Checkpoint**: show the seed summary (persona name/routing labels) to the user for confirmation → Phase 6 landing.
Full mapping in `references/soul-seed-mapping.md`; dispatch in `../butian/SKILL.md`.

---

### Phase 4: Quality Validation

After generating the Skill, use sub-agents to run 3 tests (independent of the main agent, avoiding self-evaluation bias):

#### 4.1 Known-Answer Test (Sanity Check)
Pick 3 questions this person has publicly addressed, **spawn sub-agents answering with the new Skill**, and compare against actual positions.
- Direction matches → the model works
- Deviates → trace back and adjust mental model weights

#### 4.2 Edge Case Test
Pick 1 related question this person hasn't publicly discussed; infer with the Skill.
- Expected result: "Based on models X and Y, possibly... but uncertain"
- Should not be categorical

#### 4.3 Style Test (Voice Check)
Use the Skill to write a 100-character analysis and judge:
- Does it have this person's expression traits?
- Is it not generic AI-flavored chicken soup?
- Is it not stitched-together quotes?

#### 4.4 Pass Criteria

| Check item | Pass criteria | Failure signals |
|--------|---------|-----------|
| Mental model count | 3-7, each with source evidence | <3 or >10 |
| Each model's limitations | Failure conditions written explicitly | Only strengths listed |
| Expression DNA distinctiveness | Recognizable from 100 characters | Sounds like generic ChatGPT |
| Honest boundaries | At least 3 concrete limitations | Only "can't replace the person" |
| Internal tension | At least 2 contradiction pairs | Highly consistent views (too fake) |
| First-hand source ratio | >50% | Mostly secondhand summaries |

Validation passes → deliver. Fails → flag weak spots and return to Phase 2 to iterate.
**Iteration cap**: Phase 2→4 may loop at most 2 times. After 2 rounds, if items still fail, flag the weak dimensions in the honest boundaries and deliver the current best version instead of polishing forever.

**🔴 CHECKPOINT · the task counts as complete only after presenting the validation results to the user for confirmation.**

---

### Phase 5: Dual-Agent Refinement (Standard Post-Processing)

After Phase 4 validation passes, automatically launch dual-agent refinement to further improve the Skill's operability:

**Launch two agents in parallel:**

**Agent A (auto-skill-optimizer perspective)**:
- Run an 8-dimension structural evaluation of SKILL.md (workflow clarity, boundary conditions, checkpoint design, instruction specificity, etc.)
- Dry-run 3 typical test prompts, evaluating effectiveness dimensions
- Output: concrete improvement suggestions for the 2 weakest dimensions (with before/after text examples)

**Agent B (skill-creator perspective)**:
- Review whether the "activation trigger conditions" cover real usage scenarios
- Review the "roleplay rules" for operability (question routing, frequency constraints, failure prevention)
- Identify missing key information
- Output: 2-3 concrete text-change suggestions (with before/after text examples)

**🔴 CHECKPOINT · the main agent synthesizes both reports, applies non-conflicting improvements, and shows the change summary for user confirmation.**

Refinement standard: changes must make the skill "execute on activation" — not just adding content, but ensuring the AI knows what to do first and when to stop after receiving the skill.

---

### Phase 6: SOUL Landing and Acquired Evolution (Butian Integration; This Repo Only)

After the user confirms the seed, land and evolve per the butian dispatcher (this step is orchestrated by the butian skill;
Nüwa only guarantees seed quality):

```
# 1) Seed → SOUL persona (create KB + 4 constitutional documents + bootstrap + index)
ragctl soul distill <seed-dir> --name soul-<name> --scope kb1,kb2 \
  [--values <seed-dir>/values.md] [--harness omp]

# 2) Acquired curiosity training (innate genes → knowledge and experience)
ragctl soul learn-all soul-<name> --rounds 2
ragctl soul review soul-<name> --action approve --all   # approve memory drafts

# 3) Persona-augmented retrieval Q&A
ragctl soul ask "question" --soul soul-<name> --qdcvr
```

Evolution loop: training produces drafts → approval registers → profile refresh → better routing → scheduled training
keeps learning new documents → reflect guards against drift. Details in `../soul/SKILL.md` §B/§C and
`../soul/references/soul-distill-integration.md`.

---

## Updating an Existing Skill

When the user says "update XX's skill" or "XX has recent news":

1. Read the existing SKILL.md; find "Research date: [date]" in the "Honest Boundaries" section; note how long ago it was
2. Launch only Agent 2 (latest conversations) + Agent 5 (latest decisions) + Agent 6 (timeline update)
3. Compare new information against existing content:
   - New info reinforces existing models → add cases
   - New info contradicts existing models → flag the change; update the model
   - New thinking patterns appear → consider adding a new model
5. Update the "Latest Developments" section and research date in SKILL.md
6. Re-export the Butian seed (if already landed as SOUL): rerun nuwa_to_seed.py to overwrite the seed directory,
   then re-land/refresh via butian (see Phase 3.5/6)
7. Do not rewrite the whole Skill; only update incrementally

---

## Taste Rules (Quick Reference)

Look back here when judgment is hard. Concrete quantitative criteria are in the Phase 4 pass-criteria table.

| Principle | One sentence |
|------|--------|
| Long-form > soundbites | A 3000-word essay reveals thinking structure better than 50 tweets |
| Controversy > consensus | The most contested views reveal uniqueness best |
| Change > fixity | Where someone changed their mind carries more information than what they always held |

### ❌ Anti-Pattern Blacklist (Never Do These)

| # | Anti-pattern | Why / what to do instead |
|---|--------|------------------|
| 1 | Fabricate things this person never said | The web is full of fake celebrity quotes. Quotes must have sources; a great quote with no verifiable original is better left out |
| 2 | Package generic wisdom as this person's "unique insight" | Content failing the triple validation (exclusivity) doesn't enter mental models |
| 3 | Ignore negative reviews and controversies | Agent 4's critical material is the key defense against fan-goggles; insufficient negative share = failed research |
| 4 | Force generation when information is insufficient | Better an honest 60-point Skill with labeled limitations than a seemingly perfect 90-point Skill built on fabrication |
| 5 | Use Zhihu/WeChat official accounts/Baidu Baike as sources | Plagiarism, distortion, unverifiable. No dimension is an exception |
| 6 | Hard-run the whole flow in one session on a small-context model | Context will explode between Phases 1-2. Resume in segments per the failure downgrade table |
| 7 | Start running without reporting cost magnitude | Full distillation is a heavy task; the user has the right to pick a tier before spending |
| 8 | Distill a living non-public figure without flagging boundaries | Privacy and the person's own will are involved. The user must provide material and be reminded to obtain the person's consent |
| 9 | Generate a Skill without anti-drift mechanisms | In long conversations, persona Skills tend to lose character and fall back to generic assistant tone. The template's roleplay rules + expression DNA constraints must be fully preserved |
| 10 | Turn confirmation checkpoints into delivery blockers | Checkpoints let users course-correct, not withhold output. Give defaults wherever possible |

---

## Special Scenarios

### Living Person vs Historical Figure
- **Living person**: watch timeliness; flag the cutoff date; recommend periodic updates
- **Historical figure**: material is more stable but may carry biographical bias; cross-validate across multiple sources

### Topic Skill vs Persona Skill

When the input is a topic rather than a person's name (e.g. "value investing", "product restraint", "antifragile decisions"), the Phase variants:

| Phase | Persona Skill | Topic Skill variant |
|-------|----------|--------------|
| 0A | Confirm name + focus direction | Confirm topic boundaries + target audience (is "value investing" Graham-style or all schools?) |
| 0.5 | `[person]-perspective/` | `[topic]-framework/`, same directory structure |
| 1 | 6 agents around one person | First search the topic's 3-5 core figures/schools, then assign agents per figure (1-2 agents each instead of 6) |
| 2.1 | Extract one person's mental models | Extract the **domain-consensus framework** (all schools agree) + **inter-school disputes** (A says X, B says Y) |
| 2.3 | Simulate one person's expression | Don't simulate a specific voice; use neutral but professional expression |
| 2.4 | One person's internal contradictions | Fundamental inter-school disputes (e.g. value investing vs growth investing philosophical differences) |
| 3 | Use skill-template.md | Adjust the template: remove roleplay rules and identity card; use "Framework Overview" + "School Comparison" |
| 4 | Compare against this person's known positions | Compare against the domain's recognized classic cases |

### Chinese Figure vs Western Figure
- **Chinese figure**: Bilibili original videos/talks, Xiaoyuzhou podcasts, authoritative media interviews (36Kr/LatePost/Caixin/GeekPark), the person's own books/Weibo. Zhihu and WeChat official accounts are always excluded
- **Western figure**: Twitter, YouTube, Podcasts, Amazon book reviews

### Obscure Figures (Very Little Public Information)
When Phase 0.5's evaluation finds <10 usable sources:
1. Inform the user in Phase 0.5: "this person has little public information; the generated Skill's quality will be limited"
2. Reduce mental models to 2-3, each flagged "inferred from limited information"
3. Expand the honest boundaries section, explicitly listing "which dimensions lack information"
4. If the user can provide first-hand material (books, internal recordings, private messages), use it preferentially

### Distilling the User Themselves
When the user says "distill myself" or "make a skill of me":
1. Nüwa cannot find the user's thinking framework in public channels; the user must provide material
2. Guide the user to provide: personal articles/blogs, recorded videos/podcasts, decision memos they've written, self-descriptions
3. Phase 1's 6 agents analyze user-provided material instead of web searching
4. Pay special attention to "self-perception bias" — users may overestimate certain traits and ignore blind spots; follow up by asking about evaluations from people around them

---

## Finally

What Nüwa creates is not a person, but a mirror.

A good persona Skill lets you see your own problems through another person's eyes. Not to imitate them, but to expand the boundaries of your own thinking.
