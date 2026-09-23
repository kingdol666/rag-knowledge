# Thinking-Framework Extraction Methodology

> The core methodology for going from raw information to runnable mental models.

## 1. Triple Validation for Mental-Model Identification

For a claim to be recognized as a "mental model" rather than an "offhand remark", it must pass triple validation:

### Validation 1: Cross-domain recurrence
The same thinking framework appears in at least 2 different domains this person discusses.

Example: Naval's "leverage" concept —
- Talks about leverage in wealth creation (code, media, capital, labor)
- Talks about leverage in personal growth (specific knowledge + leverage = compound interest)
- Talks about leverage in career choice (choose work with leverage effects)
→ Recurs across 3 domains → this is a genuine mental model

### Validation 2: Generative power
The model lets you infer this person's likely stance on new questions.

Example: if Munger's "inversion" is a mental model —
- Facing "how to succeed" → he first thinks "how to guarantee failure"
- Facing "how to invest" → he first thinks "how to lose all the money"
→ Generates new inferences → this is a genuine mental model

### Validation 3: Exclusivity
Not every smart person thinks this way — the model embodies this person's distinctive perspective.

Example: "antifragility" belongs to Taleb; not everyone sees the world this way
→ It differentiates → this is a mental model worth distilling

**If a claim passes only 1 of the 3 validations** → downgrade it to a "decision heuristic" rather than a "mental model"
**If a claim passes 0 validations** → it may just be something the person said in one specific context; do not include it

---

## 2. Quantifying Expression DNA

### 2.1 Sentence-pattern fingerprint

Randomly sample 20 passages from this person's long-form writing / talks, and measure:

| Dimension | How to measure |
|-----------|----------------|
| Average sentence length | characters / sentence count |
| Question ratio | questions / total sentences |
| Analogy density | analogies per 1,000 characters |
| First-person usage rate | frequency of "I" (「我」) |
| Certainty-language ratio | "definitely" (「一定」) "obviously" (「显然」) vs "maybe" (「也许」) "possibly" (「可能」) |
| Transition frequency | "but" (「但是」) "however" (「然而」) "though" (「不过」) per 1,000 characters |

### 2.2 Style tags

Tag along the following dimensions:

```
formal ←→ colloquial
abstract ←→ concrete
hedged ←→ assertive
academic ←→ popular
long sentences ←→ short sentences
buildup-first ←→ conclusion-first
data-driven ←→ narrative-driven
```

### 2.3 Forbidden words and verbal tics

- Words this person never uses → do not use them in the generated Skill either
- This person's verbal tics / high-frequency expressions → use sparingly (too many turns it into an impression act)

---

## 3. Contradiction-Handling Principles

Contradictions are a core feature of a persona, not a bug to be fixed.

### Three types of contradiction

1. **Temporal contradiction** (evolving views)
   - The person said A early on, later said B
   - Handling: record the evolution trajectory, tag with "early" and "recent"
   - In the Skill, present "recent views" as primary while mentioning the evolution

2. **Domain-specific contradiction** (different rules in different contexts)
   - The person advocates X at work and Y in life
   - Handling: record per domain; do not force unification
   - This is precisely where depth comes from

3. **Essential tension** (internal conflict of values)
   - Example: pursuing freedom while also valuing discipline
   - Handling: record explicitly as a "core tension"
   - This is usually the most interesting part of the person

### Wrong ways to handle it
- ❌ Pick one side and ignore the other
- ❌ Invent a reconciling explanation
- ❌ Pretend the contradiction does not exist

---

## 4. Handling Insufficient Information

| Situation | Handling |
|-----------|----------|
| Very little public information on a dimension | Mark in the Skill: "insufficient information; this dimension is speculative" |
| Only secondhand information | Lower confidence; mark as "reported by [source]" |
| Information contradicts itself and cannot be judged | Present both side by side and let the user judge |
| The person deliberately keeps something private | Respect the boundary; note in the Skill: "this person stays silent on this topic" |

---

## 5. Person Skill vs Topic Skill

| Dimension | Person Skill | Topic Skill |
|-----------|--------------|-------------|
| Core | One person's way of thinking | A domain's thinking toolbox |
| Source of mental models | Primarily one person | Synthesized from multiple perspectives |
| Expression style | Simulates this person's expression | Neutral but professional |
| Contradiction handling | Preserves the person's internal contradictions | Presents disagreements between schools of thought |
| Validation method | Compare against this person's known positions | Compare against domain consensus |

---

## 6. Quality Self-Check Checklist

After generating the Skill, self-check with these questions:

### Mental models
- [ ] Does every model have evidence from at least 2 different domains?
- [ ] Is the model count between 3-7? (too few = too shallow, too many = not distilled)
- [ ] Does every model have clear application scenarios and limitations?
- [ ] Do the models have tension between them without contradicting each other?

### Expression DNA
- [ ] Does it read as distinctive, not like a generic AI?
- [ ] Does it avoid over-imitation turning into a caricature?
- [ ] Does it capture core traits rather than surface mimicry?

### Decision heuristics
- [ ] Is every rule backed by a concrete case?
- [ ] Can each rule be triggered by new situations (not just the original case)?

### Honest boundaries
- [ ] Does it state clearly what it cannot do?
- [ ] Are information sources and research dates noted?
- [ ] Are information-insufficient dimensions acknowledged?

### Overall
- [ ] Looking at a new problem through this person's eyes, do you get a valuable perspective?
- [ ] Is it the framework running, not a collage of the person's quotes?
- [ ] With the name removed, could you still tell whose way of thinking this is?
