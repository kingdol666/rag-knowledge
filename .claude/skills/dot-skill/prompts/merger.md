# Incremental Merge Prompt

## Task

You will receive:
1. The existing `work.md` content
2. The existing `persona.md` content
3. New raw material content (files or messages)

Your task is to decide which section the new content should update, and output the incremental update.

**Principle: append only the delta; never overwrite existing conclusions. On conflict, output a conflict notice and let the user decide.**

---

## Step 1: Classification

Classify every piece of information in the new content:

| Information type | Goes into |
|------------------|-----------|
| Technical standards, code style, API/interface design, workflow | → work.md |
| Domain knowledge, system responsibilities, technical conclusions | → work.md |
| Communication style, catchphrases, expression habits | → persona.md |
| Decision behavior, interpersonal relations, emotional patterns | → persona.md |
| Both | → split into each |

---

## Step 2: Conflict Check

Compare the new content against the existing content:

- If the new content **supplements** existing information (adds new detail) → append directly
- If the new content **confirms** existing information → ignore (do not write duplicates)
- If the new content **contradicts** existing information → output a conflict notice:

```
⚠️ Conflict detected:
- Existing: {existing description}
- New finding: {new content description}
- Source: {file name / time}

Suggestion: [keep existing / update to new content / keep both with timestamps]
Ask the user to decide.
```

---

## Step 3: Generate the Update Patch

For `work.md` updates, output in this format:
```
=== work.md update ===

[Append to the "Technical standards / Naming conventions" section]
- {new content}

[Append to the "Experience knowledge base" section]
- {new knowledge conclusion}

[No updates] or [sections above updated]
```

For `persona.md` updates, output in this format:
```
=== persona.md update ===

[Append to the "Layer 2 / Catchphrases and word choice" section]
- New catchphrase: "{xxx}"

[Append to the "Layer 4 / Toward peers" section]
- {new behavior description}

[No updates] or [sections above updated]
```

---

## Step 4: Generate the Update Summary

Show the user:
```
Update summary:
- work.md: appended {N} new items ({brief description})
- persona.md: appended {N} new items ({brief description})
- {N} conflicts found, awaiting your confirmation (see above)

Version will move from {vN} to {vN+1}.
Apply the update?
```
