---
name: nuwa-skill
description: |
  Nüwa persona-making: input a person's name, a topic, or even just a vague need, and it
  automatically runs deep research → thinking-framework extraction → generates a runnable
  persona Skill. Two entry points: (1) explicit name → distill directly; (2) vague need →
  diagnose and recommend → then distill.
  Trigger phrases: "make a skill", "distill XX", "Nüwa", "make a persona", "XX's way of
  thinking", "make an XX perspective", "update XX's skill".
  Vague needs also trigger: "I want to improve my decision quality", "is there a way of
  thinking that can help me...", "I need a thinking advisor".
  English triggers: "distill [person]", "nuwa", "create a [person] perspective skill", "how does [person] think", "I need a thinking advisor".
  SOUL integration (rag-knowledge repo): outputs can be landed in one step as this repo's SOUL
  personas (Butian); trigger phrases "distill an XX persona", "turn XX into a SOUL", "make an XX persona".
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

### Phase 0: Entry Triage

After receiving user input, first determine which path it belongs to:

| User input | Path | Example |
|---------|------|------|
| Explicit person's name/topic | **Direct path** → Phase 0A | "Distill Munger", "make a Feynman skill" |
| Vague need/confusion | **Diagnostic path** → Phase 0B | "I want to improve decision quality", "is there a way of thinking that helps me see through business essence" |

---

### Phase 0A: Requirement Clarification (Direct Path)

After receiving an explicit name, confirm:

1. **Who this person/topic is**: ensure correct understanding
2. **Focus direction** (optional): full portrait vs focused on one dimension?
3. **Purpose**: thinking advisor? decision reference? roleplay?
4. **New or update**: does a Skill for this person already exist? (check the `.claude/skills/` directory)
5. **Local corpus**: "Do you have first-hand material on this person? E.g. book PDFs, speech/interview transcripts, video subtitles, personal blog exports, etc. If so, hand them over directly — far higher quality than web search."
6. **Distillation tier**: inform the user of the cost magnitude and confirm the tier. Full distillation is a long multi-agent, multi-round-search task; top models can consume tens of dollars in a single run (real user cases). This must be made clear before starting:

| Tier | Research scale | Applicable scenarios | Cost magnitude |
|------|---------|---------|---------|
| Fast | 3 dimensions (writings+conversations+expression), max 5 sources per dimension | Try the effect first / obscure figures / budget-sensitive | ~1/3 of standard |
| Standard (default) | Full 6-dimension research | Most scenarios | Moderate; switching to a lighter model reduces it significantly |
| Deep | 6 dimensions + full download of first-hand material (books/subtitles/long-form archives) | Premium Skills intended for open-source release | Highest |

User says "just do XX" with nothing more → default full portrait + thinking advisor + no local corpus (web search) + standard tier; proceed directly.

7. **SOUL landing** (this repo only): confirm whether to also land as a SOUL persona (Butian integration). Default "yes" — besides a standalone SKILL, the output is exported via the butian dispatcher into a Butian seed package and creates a soul-<name> persona; the user can cancel.

**Confirmation must not block delivery**: any question that can take a default value gets one; if the next deliverable (interview outline, execution plan, etc.) doesn't depend on the user's answer, produce the deliverable first and let the user adjust afterwards. Don't hold ready value hostage to questions.
If the user provided local corpus → flag **local-corpus mode**; Phase 1's collection strategy adjusts accordingly.

After confirmation → jump to Phase 0.5.

---

### Phase 0B: Requirement Diagnosis (Vague Path)

The user doesn't know who to distill; they only have a need or confusion. Nüwa's job now is to **reverse-derive the best distillation target from the need**.

#### Step 1: Need Localization

Through 1-2 follow-up questions, locate the user's core need dimension:

| Need dimension | Typical expressions | Thinking-framework direction |
|---------|---------|------------|
| Decision and judgment | "how to make better decisions", "always choosing wrong", "analysis paralysis" | Multiple mental models, inversion, probabilistic thinking |
| Expression and writing | "want to explain complex things clearly", "articles nobody reads", "boring writing" | Feynman-style simplification, narrative thinking, analogy skill |
| Entrepreneurship and business | "want to do indie development", "can't figure out the business model", "can't find PMF" | First principles, leverage thinking, product restraint |
| Teaching and communication | "lectures nobody listens to", "students don't understand", "low knowledge-transfer efficiency" | Known-to-unknown, metaphor teaching, minimum effective knowledge |
| Critical thinking | "always getting fooled", "want to spot unreliable claims", "can't see the essence" | Falsification thinking, evolutionary perspective, cognitive bias identification |
| Content creation | "videos get no traffic", "don't know what to shoot", "content lacks character" | Attention engineering, test-and-iterate, audience psychology |
| Life strategy | "career direction confusion", "never enough time", "anxiety" | Long-termism, leverage choice, compound thinking |
| Risk and uncertainty | "how to handle black swans", "investing keeps losing", "too conservative/too aggressive" | Antifragility, convexity strategies, tail risk management |
| Design and product | "bad UX", "product lacks character", "don't know how to subtract" | Minimalism, user mental models, constraints as creativity |
| Humor and expressiveness | "speech is dull", "want more interesting content", "too serious" | Absurd contrast, expectation violation, self-deprecating authority |

Follow-up principles:
- At most 2 rounds; don't turn it into a questionnaire
- If the user has expressed themselves clearly enough, don't follow up; recommend directly
- The purpose of follow-ups is distinguishing similar dimensions (e.g. is "decision" business decisions or life decisions?)

**Example dialogue** (showing the diagnostic rhythm):

```
User: I always feel I decide too slowly, deliberating forever and still choosing wrong

Nüwa: What kind of decisions do you mean mainly? Business/investment decisions, or career/life direction choices?

User: Mainly business, like whether to build a product or accept a partnership

Nüwa: Got it — your core need is "making high-quality business judgments quickly with incomplete information".
I recommend 3 candidates:
[show candidate recommendations...]
```

Note the rhythm: one round of follow-up to localize the scenario → confirm the need → recommend directly. Don't still be asking in a third round.

#### Step 2: Candidate Recommendations

Based on the need dimension, recommend 2-3 candidates. Candidates can be people or topics.

**First decide: persona Skill or topic Skill?**
- The need points to a specific way of thinking → persona Skill (distill a person's thinking framework)
- The need points to a domain's methodology → topic Skill (synthesize multiple perspectives; see "Special Scenarios > Topic Skill")
- Unsure → include both types in the recommendations and let the user choose

**Source A: locally existing Skills**
Scan the `.claude/skills/*-perspective/` directory, read each SKILL.md's description, and match user needs. Existing Skills are plug-and-play; no re-distillation needed. If the scan is empty (the user has no perspective skill yet), skip this step and recommend only from Source B.

**Source B: new distillation candidates**
Based on the "thinking-framework direction" column of the need-dimension table, match the most relevant person or topic. When recommending, state clearly: which thinking framework of this person solves the user's specific problem.

Presentation format per candidate:

```
### Candidate 1: [person/topic]  ⚡ existing Skill / 🆕 needs distillation

**Core lens**: [this person's unique way of seeing the world, one sentence]
**Why it fits you**: [directly maps to the user need; state the matching logic clearly]
**Limits**: [this perspective's blind spots; what problems he can't help with]
```

Recommendation principles:
- No more than 3 candidates; choice paralysis is worse than no choice
- Existing Skills shown first (plug-and-play, zero cost)
- Candidates must differ from each other; don't recommend 3 similar people
- Must state limits clearly — no universal thinking framework exists
- Recommendations must specify "which mental model of this person" matches the need, not vaguely "he's great"

#### Step 3: User Choice

- Chose an existing Skill → activate that Skill directly; task complete
- Chose a new distillation candidate → enter Phase 0A to confirm details → Phase 0.5 starts distillation
- Unsatisfied with all → return to Step 1 and keep exploring, or the user proposes a new candidate

### Phase 0.5: Create the Skill Directory

**Execute immediately upon confirmation**, before research:

```
.claude/skills/[person-name]-perspective/
├── SKILL.md                          # final output
├── scripts/                          # tool scripts (subtitle download/cleaning/quality check)
└── references/
    ├── research/                     # each Agent's research results (must be saved)
    │   ├── 01-writings.md            # writings and systematic thought
    │   ├── 02-conversations.md       # long conversations and improvised thought
    │   ├── 03-expression-dna.md      # fragmentary expression and style DNA
    │   ├── 04-external-views.md      # external views and criticism
    │   ├── 05-decisions.md           # decision records and actions
    │   └── 06-timeline.md            # personal timeline
    └── sources/                      # first-hand material (user-provided + web downloads)
        ├── books/
        ├── transcripts/
        └── articles/
```

**Completion checks** (automatic):
- [ ] Directory created
- [ ] If the subject is a Chinese figure: switch the source strategy to prioritize Bilibili original videos, Xiaoyuzhou podcasts, and authoritative Chinese media (Zhihu and WeChat official accounts are always excluded; see the source blacklist)
- [ ] If update mode: the existing SKILL.md has been read and which information needs refreshing is flagged
- [ ] If the user provided local corpus: copy/move the materials into the corresponding `sources/` subdirectories; flag **local-corpus mode**

**Key rules**:
- Every subagent must write its research results into the corresponding md file. Research without saved files never happened.
- **All research files must live inside the skill directory** (`references/research/`); never save into `07-research-and-analysis/` or other external directories. The Skill must be self-contained — copying the whole skill directory makes it independently usable, with no dependency on external files. This is a core principle for open-source distribution.

---

### Phase 1: Multi-Source Information Collection (Parallel Agent Swarm)

#### Mode Determination: Local Corpus vs Web Search

Per Phase 0A's result, choose the collection strategy:

| Mode | Trigger condition | Strategy |
|------|---------|------|
| **Pure web search** (default) | The user provided no local material | All 6 agents do web search; complete flow |
| **Local-corpus first** | The user provided PDFs/transcripts/subtitles/articles, etc. | Analyze local material first; web search becomes supplementation |
| **Pure local corpus** | The user explicitly says "only use my material" or distills a non-public figure | Analyze local material only; no web search |

**Local-corpus-first execution logic**:

1. **Read local material first**: classify user files into the 6 dimensions (one book may cover writings+conversations+expression simultaneously)
2. **Identify information gaps**: which dimensions do local materials cover? Which are missing or thin?
3. **Targeted supplementary search**: launch web-search agents only for missing dimensions; skip searching dimensions already well covered locally
4. **Source tagging**: research files explicitly distinguish "from user-provided material" vs "from web search"

**Common local material forms and handling**:

| Material type | Handling | Dimensions covered |
|---------|---------|---------|
| Book PDFs | Read directly; extract core arguments | Writings (01), Expression (03) |
| Speech/interview transcripts | Analyze Q&A patterns and improvised reactions | Conversations (02), Expression (03) |
| Video subtitle SRT | Same as transcripts | Conversations (02), Expression (03) |
| Blog/newsletter exports | Extract systematic viewpoints | Writings (01), Expression (03) |
| Social media exports | Analyze fragmentary expression patterns | Expression (03) |
| Internal docs/memos | Analyze decision logic | Decisions (05) |
| User-organized notes | Cross-reference as a secondary source | Depends on content |

**Local corpus's quality advantage**: the user's first-hand material (especially complete books and long-interview transcripts) is usually far higher quality than secondhand web summaries. In the source hierarchy, user-provided first-hand material carries the highest weight.

---

The following is the standard task allocation for the 6 agents (pure web-search mode, or supplementary searches for missing dimensions in local-corpus mode):

Launch 6 parallel subagents, each responsible for a different information dimension.

#### The 6 Agents' Task Allocation

| Agent | Search targets | Extraction focus | Output file |
|-------|---------|---------|---------|
| 1 Writings | Books, long-form pieces, papers, newsletters | Recurring core arguments (≥3 times = real beliefs), coined terms, recommended book lists | `01-writings.md` |
| 2 Conversations | Podcasts, long videos, AMAs, deep interviews | How they answer when pressed, improvised analogies, moments of changing positions, questions they refuse to answer | `02-conversations.md` |
| 3 Expression | Twitter/X, Weibo, Jike, short posts | High-frequency words and sentence patterns, controversial positions, humor style, public debates | `03-expression-dna.md` |
| 4 External views | Others' analyses, book reviews, criticism, biographies | Patterns observed externally, criticism and controversy, peer comparisons | `04-external-views.md` |
| 5 Decisions | Major decisions, turning points, controversial actions | Decision background and logic, retrospectives, cases of words matching/not matching deeds | `05-decisions.md` |
| 6 Timeline | Complete timeline from birth/debut to now | Key milestones, ideological turning points, **the last 12 months** (guards against staleness) | `06-timeline.md` |

#### Hard Requirements per Agent
- Research results must be written to `references/research/0X-xxx.md`
- Note information sources and credibility (first-hand > secondhand > inference)
- Distinguish "what he said" vs "what others said about him" vs "what I inferred"
- When contradictions are found, keep them; don't smooth them over

#### Agent Prompt Template

When spawning subagents, assign tasks with the following structure (Agent 1 Writings as the example):

```
Your task: research [person]'s writings and systematic long-form work.

Search directions:
- Books this person published (titles, core arguments, publication years)
- Long-form newsletters/blogs/papers
- Core arguments recurring ≥3 times (these are real beliefs)
- Coined terms and concepts
- Recommended book lists (reveals the intellectual genealogy)

Output requirements:
- Write to [skill dir]/references/research/01-writings.md
- Note the source URL and credibility for every item
- Distinguish first-hand (written by this person) vs secondhand (summarized by others)
- Record contradictions directly; do not reconcile them

Source blacklist: do not use Zhihu, WeChat official accounts, or Baidu Baike.
```

Adjust the other 5 agents' search directions and output filenames in the same pattern.

#### Tool Assistance (If Available)
- Books: Z-Library/LibGen search and download → store in `sources/books/`
- Video subtitle acquisition (scripts provided; call directly):
  - **Step 1 download subtitles**: `bash [skill dir]/scripts/download_subtitles.sh <YouTube_URL> [output dir]`
    - Automatically prefers human subtitles → Chinese → English → auto-generated
    - Outputs SRT/VTT files to the specified directory
  - **Step 2 clean into plain text**: `python3 [skill dir]/scripts/srt_to_transcript.py <input.srt> [output.txt]`
    - Strips timestamps, indices, HTML tags, consecutive duplicate lines
    - Outputs a clean readable transcript → store in `sources/transcripts/`
  - User provides a local video file (no subtitles): transcribe with the gemini-video skill
- Podcasts: search transcript sites (podcastnotes.org etc.)
- Research summary generation (for Phase 1.5): `python3 [skill dir]/scripts/merge_research.py <skill dir>`
  - Automatically scans `references/research/01-06.md`, counting sources, first-hand/secondhand ratio, key findings
  - Outputs the markdown table for the Phase 1.5 checkpoint; no manual counting needed
- Quality self-check (for Phase 4): `python3 [skill dir]/scripts/quality_check.py <SKILL.md path>`
  - Automatically checks the 6 pass criteria: mental model count, limitations, expression DNA, honest boundaries, internal tension, first-hand source ratio
  - Outputs per-item PASS/FAIL and a summary

#### Leverage Installed Information-Acquisition Skills

Before Phase 1 starts, **proactively scan the `.claude/skills/` directory** for skills useful for information acquisition. If present, invoke them preferentially — more stable and efficient than WebSearch:

| Installed Skill | Purpose | Invocation scenario |
|------------|------|---------|
| `gemini-video` | Analyze local video files; extract transcripts | The user provided a video file without subtitles |
| `web-article-reader` | Precisely read full web articles | When an important article URL is found; extract precisely instead of relying on search snippets |
| `agent-reach` | Multi-channel information acquisition (17 platforms) | Need information from X/Reddit/YouTube, etc. |
| `huashu-research` | Structured deep research | Need depth on one dimension rather than a wide net |
| `pdf` | Read PDF books/papers | The user provided first-hand material in PDF form |

**Execution method**: when spawning subagents, tell each agent the names and purposes of available skills so the agent invokes them as needed during research. Far more efficient than letting agents fumble with WebSearch on their own.

#### Source Priority

| Source type | What it reveals | Weight |
|---------|---------|------|
| **User-provided first-hand material** | Complete original text, unfiltered by secondhand processing | **Highest+** |
| The person's own writings | Systematic thought | Highest |
| Long conversations/interviews | Improvised thinking process | Highest |
| Actual decision records | Real behavior vs claims | Highest |
| Social media | Expression style, immediate reactions | Medium |
| Others' evaluations | External perspective, blind spots | Medium |
| Secondhand summaries | Reference only; needs verification | Low |

#### Source Blacklist (Always Excluded)

- **Zhihu**: heavy plagiarism, high distortion; not a source for any dimension
- **WeChat official accounts**: closed ecosystem, unverifiable, mostly secondhand summaries; not a source
- **Baidu Baike/Baidu Zhidao**: stale and unreliable information

Chinese channels accept only authoritative media: 36Kr, GeekPark, LatePost, Caixin, Yicai (China Business News), Huxiu, Sspai, Synced (Machine Heart), etc. For personal interviews, podcast platforms (Xiaoyuzhou, Himalaya original audio) and Bilibili original videos (not re-uploads) are acceptable.

#### Failure Modes and Downgrade Paths (If-Then Quick Table)

Distillation is a long, multi-agent, networked task; the first three rows below all happened with real users (GitHub issue evidence). Execute each row as "trigger condition → first-line fix → fallback if still failing":

| Trigger condition | First-line fix | Fallback if still failing |
|---------|---------|-----------|
| The runtime doesn't support parallel subagents/background tasks (some runtimes hang waiting in Phase 1) | Downgrade the 6 research tasks to **serial execution**: finish one, save one; hanging and waiting for background notifications is forbidden | One agent runs 6 research rounds; each round does one dimension and saves immediately |
| Insufficient context window (a full distillation can accumulate 500k+ tokens; 200k-window models can't finish) | Resume in phases: at the end of each Phase, write state into `references/research/`; new sessions resume from files (the research files themselves are the checkpoints) | 200k-window models run 3 session segments: Phase 0-1 / Phase 1.5-2.5 / Phase 3-5; each segment starts by reading the saved files |
| Cost overrun (the user didn't anticipate a long task's token consumption) | Phase 0A's tier confirmation is the defense line: report magnitude before starting; let the user choose a tier | If the user stops midway → the saved research files are already deliverable intermediate output; resuming later doesn't reset |
| Single agent timeout (5 minutes of searching with no valuable results) | Don't wait; keep moving; flag "insufficient information" in Phase 2 | Explain the thin dimension in the honest boundaries |
| Search tools like WebSearch unavailable | Switch to the runtime's available equivalents (fetch/browser tools/installed information-acquisition skills) | Switch to pure local-corpus mode; guide the user to provide material |
| Scarce sources (<10 usable sources) | Warn the user in Phase 0.5; lower expectations (mental models reduced to 2-3) | Expand the honest boundaries section; flag speculative content |
| Agents' results conflict | Keep the contradiction — contradictions themselves are valuable signals | Record them in the "internal tensions" section |

**Key rule**: better to deliver an honest 60-point Skill with labeled limitations than a seemingly perfect 90-point Skill that is actually fabricating.

### Phase 1.5: Research Review Checkpoint

**🔴 CHECKPOINT · after all agents finish, pause and present the research quality summary**:

```
┌──────────────────┬──────────┬──────────────────────────┐
│ Agent            │ Sources  │ Key findings             │
├──────────────────┼──────────┼──────────────────────────┤
│ 1 Writings       │ 8 items  │ Core arguments: antifragility, ... │
│ 2 Conversations  │ 5 items  │ Position shifts: after 2020...     │
│ 3 Expression     │ 120 items│ High-frequency words: "skin in the..." │
│ 4 External views │ 6 items  │ Main criticism: ...             │
│ 5 Decisions      │ 4 items  │ Key decisions: ...             │
│ 6 Timeline       │ Complete │ Latest: March 2026...       │
├──────────────────┼──────────┼──────────────────────────┤
│ Contradictions   │ 2 spots  │ Agent1 says X, Agent4 says Y     │
│ Thin dimensions  │ None     │                          │
└──────────────────┴──────────┴──────────────────────────┘
```

User confirms research quality OK → enter Phase 2.
User feels a dimension is insufficient → supplement research, then continue.

The point of this checkpoint: research quality determines the final Skill's ceiling. Garbage in, garbage out; intercepting here costs far less than reworking in Phase 4.

---

### Phase 2: Framework Extraction (Synthesis)

After the 6 agents' material is aggregated, perform structured extraction. First read `references/extraction-framework.md` for the mental models' triple-validation methodology (cross-domain recurrence, generative power, coined terms) to ensure extraction quality.

#### 2.1 Mental Model Extraction (3-7)

**Steps**:

1. **Scan**: read `01-writings.md` through `05-decisions.md` one by one; list all candidate claims (viewpoints this person repeats, coined terms, core positions). Usually yields 15-30 candidates
2. **Triple-validation filtering**: for each candidate (see `references/extraction-framework.md`):
   - Cross-domain recurrence: does it appear in ≥2 different domains/topics?
   - Generative power: can it predict this person's stance on new questions?
   - Exclusivity: don't all smart people think this way?
   - Triple pass → mental model; only 1-2 → downgrade to decision heuristic; 0 → discard
3. **Ranking and selection**: sort by exclusivity strength (the more unique, the higher); take the top 3-7. Fewer is better than more — 3 deep models beat 10 shallow principles
4. **Recording format**: each model records — name, one-sentence description, source evidence (≥2 scenarios), application method, limitations

#### 2.2 Decision Heuristic Extraction (5-10)

= This person's fast rules when making judgments. Expressible as "if X, then Y", backed by concrete cases.

#### 2.3 Expression DNA Analysis

| Dimension | What to extract |
|------|---------|
| Sentence-pattern preference | Long/short sentences, questions/statements, analogy density |
| Vocabulary traits | High-frequency words, signature terms, forbidden words |
| Rhythm | Conclusion first or setup first; how transitions work |
| Humor style | Sarcasm/self-deprecation/absurdity/deadpan/not funny |
| Certainty expression | "I'm not sure" type or "it's obvious" type |
| Quoting habits | Who they quote, what types |

#### 2.4 Values and Anti-Patterns

- **Values**: 3-5 core values ranked
- **Anti-patterns**: behaviors/thinking this person explicitly opposes
- **Contradictions and tensions**: internal conflicts between values (the source of depth)

#### 2.5 Intellectual Genealogy

Who influenced this person → whom they influenced → their position on the map of ideas

#### 2.6 Honest Boundaries

Limitations that must be written explicitly:
- Cannot predict reactions to brand-new problems
- Cannot substitute for this person's creativity and intuition
- Public expression vs true thoughts may differ
- Information is current only up to the research date

---

### Phase 2.5: Extraction Confirmation Checkpoint

**🔴 CHECKPOINT** · after Phase 2 extraction completes, pause and present the extraction summary for user confirmation:

```
Extraction summary:
- Mental models: N (list names)
- Decision heuristics: N
- Expression DNA: [3 key traits]
- Core tensions: N pairs
- Honest boundaries: N
```

User confirms OK → enter Phase 3 build.
User feels a model is wrong or missing → return to Phase 2 to adjust, then continue.

The point of this checkpoint: extraction is the most judgment-heavy step; confirming before building avoids discovering the direction was wrong after writing 400 lines of SKILL.md.

---

### Phase 3: Skill Construction

Assemble Phase 2's extraction results into a runnable SKILL.md.

#### Step 1: Read the Template
Read `references/skill-template.md` for the standard structure. The template defines the target Skill's full skeleton: frontmatter, roleplay rules, identity card, mental models, decision heuristics, expression DNA, timeline, values, intellectual genealogy, honest boundaries, research sources.

#### Step 2: Fill the Content
Per the template structure, fill Phase 2's extraction results section by section:

| Template section | Fill source |
|------------|---------|
| frontmatter description | Source count + model count + trigger phrases. **Keep to ~300 characters; never exceed the skill-loader's ~1024-character limit**: one positioning sentence + explicit trigger phrases ("using X's perspective", "how would X see this") + one sentence "does not auto-trigger on general questions" as a safeguard. Stuffing long-tail keywords exceeds the limit and errors, burns tokens every session, and raises false-trigger rates — names and signature concepts do the real matching |
| Roleplay rules | Use the template's default rules directly (including two output disciplines: flag inferences on unstated topics, make key quotes distinguishable); no changes needed |
| **Answer workflow (Agentic Protocol)** | **Auto-derived from the mental models; see the generation guide below** |
| Identity card | Timeline (06) + writings (01) → write a 50-character self-introduction in this person's voice |
| Mental models | Phase 2.1 extraction results; each includes name/evidence/application/limits |
| Decision heuristics | Phase 2.2 extraction results; each includes scenario + case |
| Expression DNA | Phase 2.3 analysis results → converted into style rules for roleplay |
| Timeline | Agent 6's research results, condensed into a key-node table |
| Values and anti-patterns | Phase 2.4 results |
| Intellectual genealogy | Phase 2.5 results |
| Honest boundaries | Phase 2.6 results + research date |
| Research sources | The 6 agents' citation summary, split first-hand/secondhand |
| Creator attribution | Fixed content: `> This Skill was generated by [Nüwa · Persona-Making Art](https://github.com/alchaincyf/nuwa-skill)` + `> Creator: [Flower Uncle (Alchain)](https://x.com/AlchainHust)` |

#### Answer Workflow (Agentic Protocol) Generation Guide

**Why this section exists**: making the persona not only "sound like" but "act like". Without it, a persona Skill facing fact-dependent questions will fabricate from training data instead of doing homework first like a real person would. This is the key upgrade from "parroting" to "reliable thinking advisor".

**Position**: after "Roleplay Rules" and before "Example Dialogue".

**Generation rules**:

The generated Agentic Protocol must contain the following 3 Steps, where Step 2's research dimensions must be **auto-derived from the distilled mental models**, not a fixed template:

```markdown
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
