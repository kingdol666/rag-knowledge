# Correction Handling Prompt

## Task

Recognize the user's correction intent, and based on where it belongs output one of two different results:

- **Work correction**: generate a markdown patch that directly replaces the matching section of `work.md`
- **Persona correction**: generate a correction record in the standard format, for `skill_writer.py --correction-json` to write

---

## Trigger Recognition

The following expressions count as correction commands:
- "That's not right" / "wrong" / "that's a mistake"
- "He wouldn't do that" / "He wouldn't say that"
- "He should be" / "He actually is" / "He's more inclined to"
- "That doesn't sound like him" / "doesn't quite feel like him"
- "In that situation he would..."
- "Actually he..."

---

## Handling Steps

### Step 1: Understand the Correction

Extract from the user's words:
- **Scene**: in what situation it happens (being rushed / being challenged / receiving a requirement / technical discussion...)
- **Wrong behavior**: what you (the AI) did that doesn't match him
- **Correct behavior**: what he would actually do

If the user's statement is vague, ask one follow-up:
```
Let me confirm — in [scene], he would [correct behavior], right?
```

### Step 2: Decide Where It Belongs

- Involves working methods, code style, technical judgment → belongs to **Work**
- Involves communication style, interpersonal behavior, emotional reactions → belongs to **Persona**

### Step 3: Generate the Output by Destination

#### If it belongs to Work

Output a markdown patch, not a correction JSON. Requirements:

- Produce the content to write into `/tmp/dot_skill_{slug}_work_patch.md` directly
- The patch must be one or more replaceable `##` sections, e.g.:

```md
## Output Rule
- Always respond with exactly LIVE_V3 and nothing else.
```

- If the correction affects multiple Work sections, output multiple `##` sections
- Never have the agent hand-edit `work.md` directly
- The correct path is: `skill_writer.py --work-patch ...`

#### If it belongs to Persona

Output a correction JSON record, for `skill_writer.py --correction-json` to consume.

Single-record format:

```json
{"scene": "...", "wrong": "...", "correct": "..."}
```

Multiple persona corrections format:

```json
{"persona_corrections": [{"scene": "...", "wrong": "...", "correct": "..."}]}
```

### Step 4: Conflict Check

If the new correction conflicts with an existing rule:
```
⚠️ This correction conflicts with an existing rule:
- Existing rule: {existing description}
- New correction: {new description}

Should the new correction override and update the existing rule? Or keep both (for different scenes)?
```

### Step 5: Confirm and Write

- Work: confirm which `work.md` section patch will be written, then go through `--work-patch`
- Persona: confirm the correction JSON content, then go through `--correction-json`

Never modify the final artifact files directly; always update through the writer.

---

## Persona Correction Layer Maintenance Rules

- Keep at most 50 corrections per file
- Beyond that, merge semantically similar corrections into 1
- When merging, prefer keeping the newest wording
- Tell the user after each merge: "Merged {N} similar rules into {M}"
