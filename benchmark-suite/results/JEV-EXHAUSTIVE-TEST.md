# Exhaustive-Recall + Judgment-Gate vs. Vector Lane — Completeness Test

**Date:** 2026-09-24 · **KB:** `Novel-PridePrejudice` (`b4c48237-6937-440a-9696-cc1e66bed5c1`)
**Corpus:** *Pride and Prejudice* (Project Gutenberg), 748,167 chars → 26 logical parts
(`benchmark-suite/data/novels/pride_and_prejudice.txt`, 14,915 lines; parts in
`data/novels/parts/`).

**Question (fixed before any pipeline output was seen):**

> List every scene in the novel where Darcy and Elizabeth meet in person, in order, and say what changes in their relationship at each.

---

## 1. Setup — and the Jev caveat (read this first)

| Item | Value |
|---|---|
| Retrieval pipeline | `benchmark-suite/scripts/122_jev_exhaustive_pipeline.py` |
| Judgment layer | `benchmark-suite/experiments/jev_judge.py` |
| Answer channel | `benchmark-suite/experiments/chat_tracks.py` → `answer_closed_book()` (identical for both lanes) |
| Threshold | 0.5 |

**The judgment backend that actually ran was `llm` — the LLM substitute gate. It is NOT Jev.**

`python benchmark-suite/experiments/jev_judge.py` returns
`{"key_env": "", "endpoint": "", "sdk_installed": false, "real_jev_ready": false}` —
no `TYPESAFE_API_KEY` / `JEV_API_KEY` is configured, and `jev-reranker` is not installed.
`jev_judge.judge(..., backend="auto")` therefore falls back to `chosen = "llm"` and the run
reports `"backend": "llm"` (confirmed in the output JSON). Everywhere below, "the gate" means
**the LLM substitute gate**, never Jev.

What would change with a real key (`TYPESAFE_API_KEY` or `JEV_API_KEY`): `backend` would be
`http` (or `sdk` if `jev-reranker` were installed), each candidate would be scored by Jev's
`noul` calibrated yes/no rather than by one LLM round-trip, and the per-part scores/kept set
would be Jev's, not an LLM's. **I did not run real Jev and make no claim about its output.**

**KB structural note (verified via `kb_get_documents`):** the KB holds **28 documents**, not
26 — parts 1 and 22 are each split into two docs (`(part 1 of 2)` / `(part 2 of 2)`), while the
other 24 parts are single docs. The pipeline de-duplicates by part number, so its "L4 = 26
candidates" silently reads only 26 of 28 docs (it keeps the first half of parts 1 and 22).

---

## 2. Ground truth (established by reading the novel, BEFORE judging any output)

Read directly from `data/novels/pride_and_prejudice.txt` (chapter markers `^CHAPTER …`, scene
windows read in full) and cross-checked against the part files. **20 in-person Darcy–Elizabeth
scenes**, spanning **10 distinct parts**.

| # | Scene (chapter) | Part | What changes |
|---|---|---|---|
| G1 | Meryton assembly (Ch 3) | 2 | First meeting. Darcy refuses an introduction and calls her "tolerable; but not handsome enough to tempt me"; she overhears and forms her prejudice. |
| G2 | Lucas Lodge evening (Ch 6) | 3 | Darcy begins to notice her; Sir William pushes them to dance, she refuses; Darcy tells Miss Bingley Elizabeth has "fine eyes." |
| G3 | Elizabeth's 3-mile walk to Netherfield to nurse Jane + the first days there (Ch 7–8) | 3 | Darcy admires the glow of exercise; "bewitched" attention grows. |
| G4 | Netherfield drawing-room — Darcy asks her to dance a reel (Ch 10) | 5 | She parries him; he is "bewitched by no woman so much"; begins to feel danger. |
| G5 | Netherfield drawing-room — the character/pride conversation (Ch 11) | 5 | Verbal sparring; "your defect is a propensity to hate everybody" / "yours is wilfully to misunderstand them." |
| G6 | Netherfield ball (Ch 18) | 7 | Darcy asks her to dance; Wickham's absence poisons the evening; open friction. |
| G7 | Rosings: Darcy & Col. Fitzwilliam's first call at Hunsford parsonage (Ch 30) | 12 | Strained formality; Elizabeth coldly probes about Jane in town. |
| G8 | Rosings drawing-room — the pianoforte scene (Ch 31) | 12 | Darcy watches her play; banter; "we neither of us perform to strangers." |
| G9 | Darcy's solitary morning call at the parsonage (Ch 32) | 12 | First private tête-à-tête; he nearly confesses; "you cannot have been always at Longbourn." |
| G10 | The park/grove walks (Ch 33) | 13 | Darcy repeatedly seeks her company; odd disconnected questions. |
| G11 | First proposal at Hunsford (Ch 34) | 13 | He proposes and insults her family; she refuses angrily (Jane + Wickham). Lowest point. |
| G12 | Darcy hands her the letter in the grove (Ch 35) | 13 | Turning point; her prejudice begins to dissolve. |
| G13 | Pemberley — the unexpected meeting on the lawn (Ch 43) | 17 | His manners transformed; he asks to introduce his sister. |
| G14 | Pemberley — Darcy brings Georgiana to the Lambton inn (Ch 44) | 17 | Introduction of Georgiana; civility to the Gardiners. |
| G15 | Pemberley — the return visit (Ch 45) | 18 | Darcy defends her to Miss Bingley: "one of the handsomest women of my acquaintance." |
| G16 | Lambton inn — news of Lydia's elopement (Ch 46) | 18 | She realises she could have loved him; he silently resolves to help. |
| G17 | Longbourn — Darcy & Bingley's first call after the marriage (Ch 53) | 22 | He is silent and grave; she is confused. |
| G18 | Longbourn dinner party (Ch 54) | 22 | He keeps apart; she nearly gives him up. |
| G19 | The walk to Lucas Lodge — second proposal (Ch 58) | 24 | She thanks him for saving Lydia; he proposes again; she accepts. |
| G20 | Engagement at Longbourn (Ch 59–60) | 24 | Mutual understanding; "dearest, loveliest Elizabeth." |

Ground-truth part set: **{2, 3, 5, 7, 12, 13, 17, 18, 22, 24}** (10 parts).

---

## 3. Pipeline trace (exhaustive recall → gate → deep read → answer)

Command:
```
cd benchmark-suite && python scripts/122_jev_exhaustive_pipeline.py \
  --question "List every scene in the novel where Darcy and Elizabeth meet in person, in order, and say what changes in their relationship at each."
```
Raw output: `results/JEV-EXHAUSTIVE-PIPELINE.md` / `.json`.

- **L0** read KB descriptions: **10** KBs.
- **L2** read doc descriptions: **26** parts (dedup of 28 KB docs).
- **L4 exhaustive recall:** read the head (1,200 chars) of **all 26** parts — no similarity filter. → **26 candidates**.
- **L5.5 judgment gate:** backend **`llm`** (substitute; `model: n/a`, `key_env: ""`), 8.8 s → kept **3** parts: **{5, 13, 14}**.
- **L5 deep read:** 3 parts × 6,000 chars → 18,033 chars of evidence.
- **L7 answer:** 47.8 s, $0.195777.

**Per-part gate scores** (0–1; ✓ = kept). The JSON scores are in the pipeline's sorted-by-name
index order; remapped here to numeric part order:

| part | score | kept | part | score | kept | part | score | kept |
|---:|---:|:--:|---:|---:|:--:|---:|---:|:--:|
| 1 | 0.0 | ✗ | 10 | 0.0 | ✗ | 19 | 0.0 | ✗ |
| 2 | 0.0 | ✗ | 11 | 0.0 | ✗ | 20 | 0.0 | ✗ |
| 3 | 0.0 | ✗ | 12 | 0.1 | ✗ | 21 | 0.0 | ✗ |
| 4 | 0.2 | ✗ | **13** | **0.7** | **✓** | 22 | 0.3 | ✗ |
| **5** | **0.5** | **✓** | **14** | **0.6** | **✓** | 23 | 0.1 | ✗ |
| 6 | 0.0 | ✗ | 15 | 0.0 | ✗ | 24 | 0.1 | ✗ |
| 7 | 0.1 | ✗ | 16 | 0.1 | ✗ | 25 | 0.2 | ✗ |
| 8 | 0.1 | ✗ | 17 | 0.3 | ✗ | 26 | 0.0 | ✗ |
| 9 | 0.0 | ✗ | 18 | 0.2 | ✗ | | | |

**Kept set = {5, 13, 14}.** Content of each (verified against the source):
- part 5 = end of Ch X (the reel scene, G4) + Ch XI (the character conversation, G5) — genuine.
- part 13 = Ch XXXIII–XXXV (park walks G10, first proposal G11, letter handover G12) — genuine.
- part 14 = Ch XXXVI onward (Elizabeth **reads** the letter; her reflections; departure from
  Kent). **No in-person Darcy–Elizabeth meeting occurs in part 14** → a **false positive**
  for the question as posed.

**Answer (verbatim):**

> The evidence is insufficient to answer this question.
>
> The retrieved chunks are three non-contiguous excerpts (parts 5, 13, and 14 of 26) of *Pride and Prejudice*; they do not constitute the full novel's text. Part 5 shows Darcy and Elizabeth at Netherfield (the reel exchange and the shrubbery walk), part 13 shows Darcy's visits to the Parsonage at Hunsford and his walks with Elizabeth in the park, and part 14 is Darcy's letter at Rosings. Every other in-person meeting in the novel (including Meryton, the Lucas Lodge dance, the first proposal, Pemberley, and the engagement) falls in the 23 unretrieved parts, so no complete, ordered list can be derived from this evidence. I therefore cannot enumerate "every scene" or trace the relationship arc across them without falling back on prior knowledge, which the task forbids.

→ **REFUSED** (honest and internally correct given the evidence it was handed).

---

## 4. Vector baseline (`kb_search_vector`, question verbatim, top_k = 10)

Command (real MCP call): `kb_search_vector({"query": <question>, "kb_id": <Novel-PridePrejudice>, "top_k": 10, "score_threshold": 0.0})`.
Raw output: `results/_vector_baseline.json`.

**10 chunks returned, spanning 8 distinct parts** (part 22 returned twice — it is split into
two KB docs):

| rank | part | score | rank | part | score |
|---:|---:|---:|---:|---:|---:|
| 1 | 22 | 0.591 | 6 | 6 | 0.567 |
| 2 | 15 | 0.581 | 7 | 13 | 0.565 |
| 3 | 17 | 0.575 | 8 | 22 | 0.561 |
| 4 | 5 | 0.572 | 9 | 17 | 0.561 |
| 5 | 18 | 0.571 | 10 | 24 | 0.560 |

**Parts surfaced: {5, 6, 13, 15, 17, 18, 22, 24}.**
Evidence pack = the 10 retrieved chunk texts (5,451 chars) → same `answer_closed_book()` channel.

**Answer (verbatim):**

> The evidence is insufficient to answer this question.
>
> The retrieved chunks are isolated excerpts from *Pride and Prejudice* (parts 5, 6, 13, 15, 17, 18, 22, and 24 of 26). They show fragments of several Darcy–Elizabeth encounters, but they do not provide the full set of in-person meetings, and most excerpts are truncated mid-sentence or begin mid-scene, so no complete ordered list can be constructed.
>
> What the excerpts do gesture at, without being exhaustive or conclusive: a gathering where Miss Bingley prompts Elizabeth to walk about the room and Darcy looks up (part 5); the first meeting with Wickham present, where both men change colour (part 6); unexpected meetings during Elizabeth's rambles in the park (part 13); Elizabeth telling Jane of the scene with Darcy (part 15); the introduction to Darcy's sister at Pemberley (part 17); Darcy's remark about Elizabeth's beauty overheard by Miss Bingley (part 18); Darcy's arrival in Hertfordshire with Bingley and the family's reaction (part 22); and Mr. Bennet's teasing about Darcy being the man (part 24).
>
> Since the evidence omits the novel's other meetings and contains no coherent narrative of how the relationship changes at each, I cannot supply the ordered list requested.
>
> Sources used: `pride_and_prejudice (part 5 of 26).md`, `(part 6 of 26).md`, `(part 13 of 26).md`, `(part 15 of 26).md`, `(part 17 of 26).md`, `(part 18 of 26).md`, `(part 22 of 26) (part 1 of 2).md`, `(part 24 of 26).md`.

→ **REFUSED** (also honest).

**Supplementary probe (not the baseline):** 8 paraphrase queries × top-10 (80 chunks) surface
the union **{1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 24, 25}** — which
**covers all 10 ground-truth parts**. So the vector lane *can* reach everything with enough
query variants; the single-query baseline is what under-recalls.

---

## 5. Completeness table

A scene counts as **found** if its ground-truth part was surfaced by that lane.

| # | Scene (Ch) | part | (a) exhaustive + gate | (b) vector top-10 | (c) neither |
|---|---|:--:|:--:|:--:|:--:|
| G1 | Meryton assembly (3) | 2 | ✗ (0.0) | ✗ | **✗** |
| G2 | Lucas Lodge (6) | 3 | ✗ (0.0) | ✗ | **✗** |
| G3 | Netherfield walk/stay (7–8) | 3 | ✗ | ✗ | **✗** |
| G4 | Reel (10) | 5 | ✓ (0.5) | ✓ | |
| G5 | Character convo (11) | 5 | ✓ (0.5) | ✓ | |
| G6 | Netherfield ball (18) | 7 | ✗ (0.1) | ✗ | **✗** |
| G7 | Rosings call (30) | 12 | ✗ (0.1) | ✗ | **✗** |
| G8 | Pianoforte (31) | 12 | ✗ | ✗ | **✗** |
| G9 | Hunsford tête-à-tête (32) | 12 | ✗ | ✗ | **✗** |
| G10 | Park walks (33) | 13 | ✓ (0.7) | ✓ | |
| G11 | First proposal (34) | 13 | ✓ | ✓ | |
| G12 | Letter handover (35) | 13 | ✓ | ✓ | |
| G13 | Pemberley lawn (43) | 17 | ✗ (0.3) | ✓ | |
| G14 | Georgiana intro (44) | 17 | ✗ | ✓ | |
| G15 | Pemberley visit (45) | 18 | ✗ (0.2) | ✓ | |
| G16 | Lambton news (46) | 18 | ✗ | ✓ | |
| G17 | Longbourn call (53) | 22 | ✗ (0.3) | ✓ | |
| G18 | Longbourn dinner (54) | 22 | ✗ | ✓ | |
| G19 | Second proposal (58) | 24 | ✗ (0.1) | ✓ | |
| G20 | Engagement (59–60) | 24 | ✗ | ✓ | |
| | **TOTAL** | | **5 / 20 = 25%** | **14 / 20 = 70%** | **7 / 20 = 35%** |

**Part-level recall:** exhaustive + gate **2/10 = 20%**; vector top-10 **6/10 = 60%**.
(Neither lane produced a correct complete answer — both refused.)

---

## 6. Verdict

**Did exhaustive-recall + gate find everything? No — it found the least of the two.**
Exhaustive recall (L4) genuinely read all 26 parts, but the **gate is the bottleneck**: it kept
only 3 of 26 parts, of which only **2 are ground-truth parts** (5 and 13). Scene recall **25%**.

**What the gate wrongly dropped.** Every ground-truth part except 5 and 13 was dropped,
including:
- **part 12** (0.1) — holds *three* in-person scenes (G7, G8, G9);
- **part 17** (0.3) — the entire Pemberley reunion (G13, G14);
- **part 18** (0.2) — G15, G16; **part 22** (0.3) — G17, G18; **part 24** (0.1) — G19, G20;
- **parts 2 and 3** (0.0) — the assembly and Lucas Lodge, i.e. the first meetings.

Root cause: the gate judges only the **1,200-char head** of each part. The head of a part is
usually mid-scene or front-matter (part 2's head is the table of contents), so the head often
contains no Darcy+Elizabeth exchange even when the part does. The gate also produced a **false
positive** — it kept **part 14** (score 0.6), which contains no in-person meeting at all (it is
Elizabeth reading the letter and leaving Kent), because the *letter* mentions Darcy. So the gate
is both lossy (misses real scenes) and imprecise (keeps non-scenes).

**What the vector lane missed.** The single verbatim query (top-10) surfaced 6/10 ground-truth
parts and missed **parts 2, 3, 7, and 12** — i.e. the assembly, Lucas Lodge/Netherfield-walk,
the Netherfield ball, and the whole Rosings cluster (G1–G3, G6–G9). Its hits are weighted toward
the later, more "quote-worthy" encounters (Pemberley, engagement). Unlike the gate, though, the
vector lane's misses are **recoverable by paraphrase**: 8 variant queries recover **all 10**
ground-truth parts. The gate's misses are not recoverable without changing the gate's input
window.

**Bottom line.** Neither configuration answered the question; both honestly refused. On
completeness, the vector lane (70% scene recall) beat exhaustive-recall + gate (25%) — but the
comparison isolates a *substitute* gate fed only part-heads, not the recall step and not Jev.
The exhaustive step is fine; the head-window gate is what destroyed completeness.

---

## 7. Honest limitations

1. **The gate was the LLM substitute, not Jev.** `real_jev_ready: false`; no API key. All
   gate numbers above are an LLM's, and a real Jev `noul` gate could score differently. I make
   no claim about real-Jev behaviour.
2. **Single run.** Both answers are LLM generations; they vary run-to-run. The *retrieval*
   numbers (scores, kept set, vector parts) are deterministic given the fixed evidence, but the
   answer text is not.
3. **Part-level, not chunk-level, completeness.** A scene is counted as "found" if its part was
   surfaced. The vector lane returns *chunks*; a surfaced part does not guarantee the exact
   scene chunk was retrieved. This can only **overstate** vector recall, so 70% is an upper
   bound for the vector lane at scene granularity.
4. **Head-window gate is a design choice.** The gate sees 1,200 chars/part; a different window
   (or scoring the whole part, or Jev) would change the kept set. The 25% figure is specific to
   this window and this substitute gate.
5. **28 vs 26 docs.** The KB stores parts 1 and 22 as two docs each; the pipeline's part-number
   dedup reads only the first half of each. No ground-truth scene here lives in those halves, so
   it does not change the counts, but the L4 "26 candidates" is not literally all 28 KB docs.
6. **Ground-truth granularity is a judgment call.** I fixed 20 scenes by reading the text; a
   finer split (e.g. separating the Netherfield stay into more beats) or a coarser one would
   move the percentages, though the ordering and the exhaustive-vs-vector gap would remain.
7. **Not verified:** real-Jev output; whether a Jev gate would keep part 14 (false positive);
   whether re-running the substitute gate reproduces the same 3-part kept set.
