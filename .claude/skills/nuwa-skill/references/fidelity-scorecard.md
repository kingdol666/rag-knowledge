# Fidelity Scorecard

> The factory QC report for a person Skill. It answers one question: **when this skill runs, does it actually resemble the person, and is it honest?**
>
> Background: the SkillLens paper (arXiv 2605.23899) showed empirically that an LLM self-assessing skill quality is only 46.4% accurate (near random). So the iron rule of the scorecard is: **the answering agent and the scoring agent must be two independent agents — never self-assess and self-certify.**

## Five Dimensions (100 points total)

| # | Dimension | Points | What it measures | How it is measured |
|---|-----------|--------|------------------|--------------------|
| 1 | Stance consistency | 30 | On questions the person has publicly taken a stance on, does the skill's answer direction agree | 3 known-stance questions, 10 points each: direction and details both right = 10, direction right but details off = 6, stance deviates = 0 |
| 2 | Style recognizability | 20 | Without seeing the name, can you tell who it is from the expression alone | The scoring agent blind-reads the answers: do sentence patterns, word choice, and analogy style carry this person's fingerprint, or a generic-AI voice |
| 3 | Edge-case honesty | 20 | On questions the person never publicly discussed, does it flag inference or fabricate with total confidence | 1 out-of-scope question: explicitly declares "this is an inference from the framework" and preserves uncertainty = full marks; passes it off as the person's own asserted view = 0 |
| 4 | Source transparency | 15 | Is the research trail traceable | Static check of skill files: has a research-sources section, first-hand source ratio > 50%, key quotes carry attribution |
| 5 | Structural completeness | 15 | Does it have the full structure for anti-drift and honest operation | Static check: 3-7 mental models, honest boundaries ≥ 3 items, internal tensions ≥ 2 pairs, anti-pattern list, role-play rules containing anti-drift constraints |

## Grades

| Grade | Score | Meaning |
|-------|-------|---------|
| A | ≥85 | Excellent out of the box; safe to use as a thinking advisor |
| B | 70-84 | Qualified; individual dimensions have known, annotated weak spots |
| C | 55-69 | Usable with caution; read the honest boundaries first |
| D | <55 | Not recommended; needs to go back and be re-distilled |

## Execution Process

1. **Write the questions**: 3 known-stance questions (topics the person repeatedly and publicly took a stance on) + 1 out-of-scope question + 1 style-sample question
2. **Answering agent**: reads only files inside that skill directory, answers with the persona activated per the skill, and is forbidden from going online
3. **Scoring agent**: an independent agent; receives the answers + this rubric + the skill file paths, and scores each dimension against the person's real public stances
4. **Output**: generate `FIDELITY.md` in the skill directory, containing the score table, per-question verdict rationale, test date, and the models used for answering/scoring

## Result Format (FIDELITY.md template)

```markdown
# Fidelity Scorecard

**Total: NN/100 · Grade X** | Test date: YYYY-MM-DD | Answering/scoring: independent dual agents

| Dimension | Score | Verdict summary |
|-----------|-------|-----------------|
| Stance consistency | NN/30 | ... |
| Style recognizability | NN/20 | ... |
| Edge-case honesty | NN/20 | ... |
| Source transparency | NN/15 | ... |
| Structural completeness | NN/15 | ... |

## Test Records
[Per question: the question, answer summary, the real stance it was checked against, verdict]
```

## Relationship to the Nüwa Workflow

- The pass criterion for Nüwa Phase 4 is **internal QC** (a gate during generation)
- The scorecard is the **external report** (factory inspection after generation completes; anyone can re-run and verify)
- When a community-contributed person skill applies for inclusion in the [COMMUNITY.md](../COMMUNITY.md) index, a scorecard grade ≥ B is the admission threshold (see [CONTRIBUTING.md](../CONTRIBUTING.md))

## Anti-Cheating

- The answering agent does not know which dimensions it is being tested on
- The scoring agent does not participate in answering; it only checks against public facts
- Questions avoid example dialogues already present in the skill files (to prevent memorized answers)
- For important conclusions, running 2 independent scoring agents is recommended; if their scores differ by > 10 points, a human re-review is required
