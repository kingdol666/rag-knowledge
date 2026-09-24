# Two-Lane Retrieval Test on a Long Novel — *Pride and Prejudice*

**Run date:** 2026-09-24 · **Test:** Lane A (`knowledgebase-search`, vector+content) vs Lane B (`knowledgebase-librarian`, vector-free) on 5 plot questions over a 26-part novel.

---

## 1. Setup

- **KB:** `Novel-PridePrejudice` (`b4c48237-6937-440a-9696-cc1e66bed5c1`) — *Pride and Prejudice*, Jane Austen, Project Gutenberg #1342, English, split into 26 `(part k of 26)` windows of ≈30 000 chars.
- **KB documents:** 28 (26 parts; parts 1 and 22 were further split into 2 for size). Local reference text: `benchmark-suite/data/novels/pride_and_prejudice.txt`.
- **Retrieval transport:** the project's own MCP stdio client (`benchmark-suite/scripts/lib.py:McpClient`) → `uv run --directory kb-mcp python server.py`. **Read-only**; no KB was created, modified or deleted.
- **Answer channel (identical for both lanes):** `benchmark-suite/experiments/chat_tracks.py` → `answer_closed_book(question, evidence)` → the platform's external chat API (`POST http://127.0.0.1:6789/api/claude/chat`, engine `claude`, `maxTurns=1`, no tools).
- **Evidence budget:** **20 000 characters per lane per question** (a hard cap; Lane A used ≈18 600, Lane B ≈20 000 — see §7 for the window-sampling caveat).
- **Known defect accounted for:** 24 of the 28 KB document descriptions read *"Gutenberg front/back matter"* although the parts hold novel chapters. Lane B's L3 trust check is designed to catch this.

### The 5 questions

- **Q1.** At the Mertyon assembly where the Netherfield party first appears, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth respond to it?
- **Q2.** What happens at Hunsford when Mr. Darcy proposes to Elizabeth, why does she refuse him, and what does his letter the next morning reveal about Wickham?
- **Q3.** How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did Darcy do and pay?
- **Q4.** How did Charlotte Lucas come to marry Mr. Collins, and how did Elizabeth react to the engagement?
- **Q5.** In the novel, Mr. Wickham is linked to two young women in connection with an elopement. Who are the two young women, roughly how old was each, and how did each affair end?

---

## 2. Ground truth (written BEFORE grading)

Full reference answers and required-fact lists are in `benchmark-suite/results/two-lane-test/GROUND_TRUTH.md`. Summary of the **required facts** (a *correct* answer must contain all; a *partial* answer misses ≥1):

| Q | Required facts (abridged) |
|---|---|
| Q1 | (1) Meryton assembly; (2) Darcy refuses to dance, *"She is tolerable: but not handsome enough to tempt me"*; (3) Elizabeth **overhears**; (4) no cordial feelings; (5) she **tells it with great spirit** |
| Q2 | (1) Hunsford proposal, *"In vain have I struggled…"*; (2) proposal dwells on her **inferiority/degradation**; (3) refusal on **two grounds** (Jane/Bingley; Wickham); (4) Darcy **admits** separating Bingley; (5) letter reveals Wickham **£3 000** + **Ramsgate/Georgiana (15)/£30 000/Mrs. Younge** |
| Q3 | (1) source = **Mrs. Gardiner's letter**; (2) **Darcy**, not Gardiner, did it; (3) found them via **Mrs. Younge**; (4) **debts >£1 000 + £1 000 settled on Lydia + commission purchased**; (5) credit given to Gardiner; (6) Darcy's partiality implied |
| Q4 | (1) follows Elizabeth's refusal; (2) Charlotte **deliberately encouraged** him; (3) *"desire of an establishment"*, **27**, never handsome; (4) *"I am not romantic… I ask only a comfortable home"*; (5) *"Engaged to Mr. Collins! impossible!"* + disillusionment |
| Q5 | (1) **Georgiana Darcy**; (2) **Ramsgate, fifteen, prevented**, £30 000; (3) **Lydia Bennet**, **sixteen**; (4) her affair **carried out → married** |

Part → chapter map (measured by grepping the parts): part 2 = Ch II–IV, part 3 = Ch V–VII, part 6 = Ch XV–XVI, part 9 = Ch XXI–XXIII, part 10 = Ch XXIV–XXVI, part 13 = Ch XXXIII–XXXV, part 14 = Ch XXXVI–XXXVII, part 19 = Ch XLVII–XLVIII, part 20 = Ch XLIX–L, part 21 = Ch LI–LII.

---

## 3. Per-question results

### Q1

> **Question.** At the Mertyon assembly where the Netherfield party first appears, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth respond to it?

#### Lane A — vector + content

Phase 0 rewrite: *"Mr. Darcy at the Meryton assembly refuses to dance with Elizabeth Bennet, saying she is tolerable but not handsome enough to tempt him, and Elizabeth overhears and laughs it off"*.

Phase 1 `kb_search_vector` (kb_id="", top_k=10, score_threshold=0.35, balance_kbs=True) → 10 hits. After the 0.35 hard threshold + per-doc dedup, the ONLY novel part in the top-10 is:
- **part 2 @ 0.7499** (chunk = the insult-scene lead-in: *"…his having slighted one of her daughters. Elizabeth Bennet had been obliged, by the scarcity of gentlemen, to sit down for two dances; and during part of that time, Mr. Darcy had been standing near enough for her to overhear a conversation between him and Mr. Bingley…"*). Hits 2-10 are cross-domain papers (0.49 down to 0.11).

Content gate (`kb_doc_read` part 2, max_chars=3000): topic 3 / scenario 3 / evidence 2 = **8/8** → **≥6, fast exit (Phase 1 only; Phase 2 never fires)**. Continuation read at offset 564 supplies the exact quotation.

Phases fired: Phase 0 → Phase 1 (fast exit).

**Lane A answer (verbatim):**

```text
The evidence answers this: when Bingley urges Darcy to dance and points out Elizabeth sitting behind him, Darcy looks at her briefly, then coldly says, "She is tolerable: but not handsome enough to tempt _me_; and I am in no humour at present to give consequence to young ladies who are slighted by other men," and tells Bingley to return to his partner. Bingley follows his advice and Darcy walks off, while Elizabeth "remained wi[th]" — the passage is cut off mid-sentence, so her immediate reaction is not fully shown. The later conversation with her sister Jane (Chapter IV) and her reported remark "Not handsome enough to dance with! ... I quite detest the man" indicate her resentment toward Darcy, though that reflection is attributed to her mother's account to her husband rather than stated directly as Elizabeth's own on-the-spot response. So the evidence fully covers what Darcy said, but Elizabeth's direct response at the assembly is truncated and only inferable from surrounding passages.

Sources used: retrieved chunk (Pride and Prejudice, Chapter III — "She is tolerable" passage, window 5/6 @line564); head/window 2/6 (Chapter I–II front matter).
```

**Lane A verdict: partially correct** — present: the exact quote (*"She is tolerable: but not handsome enough to tempt me…"*), the assembly scene, Darcy's refusal to be introduced. missing: that **Elizabeth overheard** it (the answer says the passage is truncated and infers resentment); the **"no very cordial feelings"** reaction; and the fact she **"told the story with great spirit"**. It cites the real text (part 2) and does not drift into general knowledge. 2.5/6 required facts.

#### Lane B — vector-free librarian

L0 `kb_list(lightweight=True)` → 10 KBs; shelf judged = **Novel-PridePrejudice** (description matches "《Pride and Prejudice》(Jane Austen, PG#1342) … 26 个 part").
L2 `kb_get_documents(lightweight=True)` → 28 docs, every description read.
L3 trust check: **24 of 28** descriptions are the boilerplate *"【Part k/26 · Gutenberg front/back matter】…front/back matter 的情节正文…"*; the other 4 are also unreliable — part 1 says *"Chapter I–XIV"* (over-claims; part 1 holds Ch I only), part 2 says *"Chapter XV–I"* (**degenerate/inverted range**), part 18 says *"Chapter XLVI–XLVI"* (**single-point range**). → **all 28 descriptions distrusted**; read the head (600 chars) of every part.
L4 shortlist from heads + story position: the question is the **opening assembly (Ch III)**; head of part 3 = *"Mrs. Hurst and her sister… Miss Bennet was therefore established as a sweet girl"* (Ch V, just after the assembly) → shortlist **[2, 3]**.
L5 targeted reads: 6 evenly-spaced windows per part (per-part budget 10 000 ch, window 1 666 ch).

**Lane B answer (verbatim):**

```text
The evidence is insufficient to answer this question as posed.

The retrieved chunks contain the Netherfield ball scene, where Mr. Darcy dances only with Mrs. Hurst and Miss Bingley, declines to be introduced to other ladies, and is overheard by Elizabeth in conversation with Bingley — but the overheard line is truncated: "I certainly shall not. You know how I detest it, unless I" (p2:4/6@line451). The continuation, which would contain any remark about Elizabeth, is cut off.

The later passage (p2:5/6@line564) gives Elizabeth's retrospective account — he was "all worth pleasing. So high and so conceited... Not handsome enough to dance with!" — and her statement "I quite detest the man," but this is her own reported reaction, not a quoted exchange with Bingley present.

Sources used:
- p2:4/6@line451 (pride_and_prejudice, part 2/26) — truncated overheard dialogue
- p2:5/6@line564 (pride_and_prejudice, part 2/26) — Elizabeth's later remarks to her friend
```

**Lane B verdict: refused (honest)** — Lane B's part-2 windows caught the ball scene (Darcy declines to be introduced; Elizabeth overhears) but **not the quoted insult line** — its only 'tolerable' hit was *"Sir William Lucas… had made a tolerable fortune"*. It therefore declared the evidence insufficient, correctly refusing rather than inventing the line. It does partially identify the scene and Elizabeth's later *"I quite detest the man"* (actually Mrs. Bennet's line — a small misattribution). 0/6 required facts stated.

---

### Q2

> **Question.** What happens at Hunsford when Mr. Darcy proposes to Elizabeth, why does she refuse him, and what does his letter the next morning reveal about Wickham?

#### Lane A — vector + content

Phase 0 rewrite: *"Mr. Darcy's first marriage proposal to Elizabeth Bennet at Hunsford Parsonage, her refusal, and the letter he gives her next morning revealing Wickham's attempted elopement with Georgiana Darcy"*.

Phase 1 vector → the only novel part in the top-10 is **part 6 @ 0.6581** — but part 6 is Ch XV–XVI: **Collins's** proposal and **Wickham's** narrative, *not* Darcy's Hunsford proposal. Content gate on part 6: topic 1 / scenario 1 / evidence 1 = **3/8 → ❌ discard**.

Phase 2 fired (gate ≤5): refined `kb_search_vector` (*"…'In vain have I struggled'… about Wickham and Georgiana Darcy"*) → **still part 6 @ 0.6373** (the vector lane consistently confuses Darcy's proposal with Collins's). Gate again 3/8. **No better candidate.**

Phases fired: Phase 0 → Phase 1 (gate fail) → Phase 2 (gate fail).

**Lane A answer (verbatim):**

```text
The evidence is insufficient to answer this question.

The retrieved chunks cover Elizabeth's first meeting with Wickham in Meryton and his account of the living and the Darcy family, but nothing about a proposal at Hunsford, Elizabeth's refusal, or Darcy's letter the following morning appears anywhere in them. The chunks end mid-conversation with Wickham describing Miss Darcy, and the head/window sections cover Mr. Collins's visit and the Philips's evening party. No source in the evidence describes the Hunsford proposal scene, Elizabeth's reasons for refusing, or the contents of Darcy's letter regarding Wickham. I therefore cannot answer from the provided evidence without relying on prior knowledge of the novel.

Sources used: retrieved chunk (`pride_and_prejudice`, 第 6/26 部分) and window sections 1–5 (`@line92`, `@line185`, `@line278`, `@line371`, `@line464`).
```

**Lane A verdict: refused (honest)** — The lane's only retrieved novel part (part 6) contains no Hunsford proposal, no refusal, and no letter. The answer explicitly says so and refuses — correct behaviour on bad retrieval, but it **failed to answer**. 0/5 required facts.

#### Lane B — vector-free librarian

L4 shortlist from heads: head of **part 13** = *"But why Mr. Darcy came so often to the Parsonage…"* (Ch XXXIII, the run-up at Hunsford); head of **part 14** = *"'Two offences of a very different nature… I had detached Mr. Bingley from your sister'"* (the letter, Ch XXXV) → shortlist **[13, 14]** (no vector signal used).
L5: 6 windows/part (per-part 10 000 ch).

**Lane B answer (verbatim):**

```text
**Answer:** At Hunsford, Mr. Darcy calls on Elizabeth at the Parsonage and, after agitated pacing and silence, declares "In vain have I struggled... You must allow me to tell you how ardently I admire and love you" [p13:3/6@line261].

Elizabeth refuses him on two grounds: his role in separating Bingley from Jane, which she calls the principal means of dividing them and exposing both to misery [p13:4/6@line348], and, more broadly, his character as unfolded in Wickham's recital — she tells him he was "the last man in the world whom I could ever be prevailed on to marry" [p13:5/6@line435]. Darcy replies that he comprehends her feelings and is ashamed of his own, then leaves abruptly; Elizabeth sits down and cries for half an hour [p13:5/6@line435].

His letter the next morning addresses "two offences of a very different nature" — detaching Bingley from Jane and ruining Wickham [p14:head], and on Wickham it reveals that he is the son of the late Mr. Darcy's estate manager at Pemberley, that the living was resigned in exchange for three thousand pounds, and that Wickham attempted an elopement with Darcy's fifteen-year-old sister Georgiana at Ramsgate, chiefly for her thirty-thousand-pound fortune, the plot aided by Mrs. Younge [p14:1/6@line80, p14:2/6@line160]. Elizabeth weighs the letter's account against Wickham's own words, finding each recital confirming the other until the matter of the will, where "the difference was great" and she feels "gross duplicity on one side or the other" [p14:3/6@line240].

**Sources used:** p13:head, p13:3/6@line261, p13:4/6@line348, p13:5/6@line435, p14:head, p14:1/6@line80, p14:2/6@line160, p14:3/6@line240 (all from *pride_and_prejudice*, parts 13/26 and 14/26).
```

**Lane B verdict: partially correct (strong)** — present: the Hunsford proposal and the opening quote (*"In vain have I struggled… ardently I admire and love you"*); the **two refusal grounds** (separating Bingley from Jane; Wickham's recital); the letter's contents — Wickham resigned the living for **£3,000**, the **Ramsgate** attempted elopement with **Georgiana (then fifteen)** for her **£30,000** fortune, aided by **Mrs. Younge**. missing: that Darcy's proposal **dwells on her inferiority/degradation**, and Darcy's explicit admission that he separated Bingley and rejoiced. Real parts cited (13, 14). 3/5 required facts.

---

### Q3

> **Question.** How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did Darcy do and pay?

#### Lane A — vector + content

Phase 0 rewrite: *"Mrs. Gardiner's letter revealing that Mr. Darcy secretly found Lydia and Wickham in London, paid Wickham's debts, settled money on Lydia, and bought his commission"*.

Phase 1 vector → only novel part = **part 21 @ 0.6621**; the retrieved chunk is literally the start of Mrs. Gardiner's letter (*"…he had found out where your sister and Mr. Wickham were… he left Derbyshire only one day after ourselves, and came to town with the resolution of hunting for them"*). Content gate: topic 3 / scenario 3 / evidence 2 = **8/8 → fast exit (Phase 1 only)**.

Phases fired: Phase 0 → Phase 1 (fast exit).

**Lane A answer (verbatim):**

```text
The evidence does not answer this question. The retrieved chunks show Elizabeth writing to her aunt for an explanation, and Mrs. Gardiner's reply recounting that Mr. Darcy called on Mr. Gardiner, told him where Lydia and Wickham were, met and negotiated with Wickham repeatedly, and persuaded Lydia, but the text cuts off at the point where details would follow. The passages also reveal Elizabeth's realization that Darcy "had followed them purposely to town" and had "finally bribed" Wickham, but no explicit statement of what Darcy paid or the full settlement terms appears in this evidence. Sources: pride_and_prejudice (part 21/26), retrieved chunk and windows 1–6.
```

**Lane A verdict: refused (honest)** — present: Darcy (not Mr. Gardiner) called on Mr. Gardiner, found the pair, met Wickham repeatedly, and "finally bribed" him. missing: the **exact sums** — Wickham's debts (>£1,000), the **£1,000 settled on Lydia**, and the **purchased commission** — which sat outside the read windows. It explicitly says the passage is cut off and declines to state what Darcy paid. 3/6 required facts.

#### Lane B — vector-free librarian

L4 shortlist from heads: head of **part 21** = *"Mr. Gardiner soon wrote again to his brother… Mr. Wickham had resolved on quitting the militia"* (Ch LI, immediately before Mrs. Gardiner's letter); head of **part 20** = *"…a letter arrived for their father… from Mr. Collins"* (Ch XLIX) → shortlist **[21, 20]**.
L5: 6 windows/part (per-part 10 000 ch).

**Lane B answer (verbatim):**

```text
The evidence is insufficient to answer this question fully. The retrieved chunks establish that Elizabeth learns of Darcy's involvement through a letter from her aunt, Mrs. Gardiner (p21:5/6@line450), which reveals that "He had followed them purposely to town, he had taken on himself all the trouble and mortification attendant on such a research" — and that her prior suspicions "were proved beyond their greatest extent to be true." However, the crucial portion of that letter explaining what Darcy actually did and paid is cut off mid-sentence ("where he was reduced to meet, frequently meet, reason with, persu—"), and the letter's opening paragraphs containing the account are not included. The other chunks (p20 and p21) discuss speculation about money — Mr. Bennet's guess of "ten thousand pounds," Wickham's debts, and the settlement of Lydia's equal share of five thousand pounds — but these are the family's conjectures before knowing Darcy's role, not a statement of what Darcy paid. Scattered hints appear (p21:4/6@line360 recounts Darcy's conversation with Wickham about marrying Lydia; p21:head describes Wickham quitting the militia), but the passages that would name Darcy's exact actions and sum are missing. I therefore cannot state what Darcy did and paid.

Sources used: p21:head, p21:4/6@line360, p21:5/6@line450, p20:2/6@line195, p20:3/6@line293 (pride_and_prejudice, parts 20 and 21).
```

**Lane B verdict: refused (honest)** — present: Mrs. Gardiner's letter is the source; Darcy "followed them purposely to town". missing: the same **exact sums** — Lane B's windows caught only the family's *conjectures* (*"ten thousand pounds"* guess, the *£5,000* equal-share settlement) and Wickham *"received his commission"* (not that Darcy **purchased** it). It correctly refused to state what Darcy paid. 3/6 required facts.

---

### Q4

> **Question.** How did Charlotte Lucas come to marry Mr. Collins, and how did Elizabeth react to the engagement?

#### Lane A — vector + content

Phase 0 rewrite: *"Charlotte Lucas's marriage to Mr. Collins and Elizabeth Bennet's reaction to the engagement"*.

Phase 1 vector → only novel part = **part 10 @ 0.6759** (Ch XXIV–XXVI: the *aftermath* — Mrs. Bennet's resentment, *"The sight of Miss Lucas was odious to her. As her successor in that house…"*). Content gate: topic 2 / scenario 1 / evidence 1 = **4/8 → ❌ discard** (the engagement scene and Elizabeth's reaction are in part 9).

Phase 2 fired: refined `kb_search_vector` (*"…'Engaged to Mr. Collins impossible'… I ask only a comfortable home"*) → **part 9 @ 0.7368** (Ch XXI–XXIII, the engagement) → gate 8/8.

Phases fired: Phase 0 → Phase 1 (gate fail) → Phase 2 (recovered part 9).

**Lane A answer (verbatim):**

```text
Charlotte Lucas secured Mr. Collins's proposal by deliberately encouraging his attentions — listening to him with civility while Elizabeth avoided him — and she accepted him "solely from the pure and disinterested desire of an establishment," reasoning that marriage was "the only honourable provision for well-educated young women of small fortune." Her parents, Sir William and Lady Lucas, consented "with a most joyful alacrity," and Charlotte, at twenty-seven, "felt all the good luck of it." She resolved to tell Elizabeth herself and swore Mr. Collins to secrecy beforehand. Elizabeth, who had thought it "almost as far from possibility" that Charlotte could encourage him as that she would do so herself, cried out, "Engaged to Mr. Collins! my dear Charlotte, impossible!" Charlotte calmly replied, "Why should you be surprised, my dear Eliza? Do you think it incredible that Mr. Collins should be able to procure any woman's good opinion, because he was not so happy as to succeed with you?" Elizabeth then recollected herself and assured her of her wish for her happiness, but "it was a long time before she became at all reconciled to the idea of so unsuitable a match," and she felt "no real confidence could ever subsist between them again."

Sources used: `pride_and_prejudice（第 9/26 部分）`, Chapters XXI–XXII (chunks: retrieved chunk; window 3/6 @line269; window 4/6 @line358; window 5/6 @line448).
```

**Lane A verdict: correct** — present: Charlotte deliberately encouraged Collins; *"accepted him solely from the pure and disinterested desire of an establishment"*; *"the only honourable provision for well-educated young women of small fortune"*; parents' joyful consent; **twenty-seven**; *"Engaged to Mr. Collins! my dear Charlotte, impossible!"*; Charlotte's reply; Elizabeth's long reconciliation and loss of confidence. **5/5 required facts.** Real part cited (9).

#### Lane B — vector-free librarian

L4 shortlist from heads: head of **part 9** = *"'My dear madam,' replied he, 'let us be for ever silent on this point…' Resignation"* (Collins's post-refusal speech, Ch XX — the engagement follows); head of **part 10** = *"Mr. Collins returned most punctually… the business of love-making"* → shortlist **[9, 10]**.
L5: 6 windows/part (per-part 10 000 ch).

**Lane B answer (verbatim):**

```text
Charlotte Lucas married Mr. Collins after Elizabeth Bennet refused his proposal, and Charlotte "accepted him solely from the pure and disinterested desire of an establishment" — she "had gained her point" and her "reflections were in general satisfactory" [p9:3/6@line269]. When Miss Lucas privately told Elizabeth of the engagement, Elizabeth was so astonished that she "could not help crying out, -- 'Engaged to Mr. Collins! my dear Charlotte, impossible!'" [p9:4/6@line358]. Charlotte calmly replied, "Why should you be surprised, my dear Eliza? Do you think it incredible that Mr. Collins should be able to procure any woman's good opinion, because he was not so happy as to succeed with you?" [p9:4/6@line358]. Elizabeth then recollected herself and "made a strong effort" to congratulate the couple, joining Jane in remarks on the happiness expected from the match [p9:5/6@line448]. Elizabeth's disbelief was grounded in her view that Charlotte's encouragement of him "seemed almost as far from possibility as that she could encourage him herself" [p9:4/6@line358]. Mr. Bennet's reaction was more tranquil, saying it gratified him to find Charlotte, whom he had thought sensible, "was as foolish as his wife" [p9:5/6@line448].

Sources: pride_and_prejudice part 9/26 — chunks [p9:3/6@line269], [p9:4/6@line358], [p9:5/6@line448].
```

**Lane B verdict: partially correct** — present: the engagement follows Elizabeth's refusal; *"accepted him solely from the pure and disinterested desire of an establishment"*; *"Engaged to Mr. Collins! my dear Charlotte, impossible!"*; Charlotte's reply; Elizabeth's effort to congratulate. missing: Charlotte's age **27 / "never been handsome"** and her direct words *"I am not romantic… I ask only a comfortable home"*. Real part cited (9). 3.5/5 required facts.

---

### Q5

> **Question.** In the novel, Mr. Wickham is linked to two young women in connection with an elopement. Who are the two young women, roughly how old was each, and how did each affair end?

#### Lane A — vector + content

Phase 0 rewrite: *"Wickham's attempted elopement with Georgiana Darcy at Ramsgate and his actual elopement with Lydia Bennet"*.

Phase 1 vector → only novel part = **part 19 @ 0.6053** (Ch XLVII–XLVIII: Lydia's flight; chunk = *"…dishonourable elopement with… Wickham will never marry a woman without some money… what claims has Lydia…"*). Content gate: topic 2 / scenario 1 / evidence 1 = **4/8 → ❌ discard** (only one of the two women; no ages).

Phase 2 fired: refined `kb_search_vector` → **still part 19 @ 0.6093** (never reaches part 14, where the Georgiana affair is revealed). Gate 4/8.

Phases fired: Phase 0 → Phase 1 (gate fail) → Phase 2 (gate fail).

**Lane A answer (verbatim):**

```text
The evidence does not contain the answer to this question.

What the retrieved chunks *do* establish is only one half of the alleged pairing: Wickham's elopement with **Lydia Bennet** — she is described as "very young," never taught to think on serious subjects, given over for "the last half year, nay, for a twelvemonth" to nothing but amusement and vanity (so roughly fifteen/sixteen, though no exact age is stated), and her note announces she is "going to Gretna Green" to sign herself "Lydia Wickham." The outcome of that affair is **not** given in these chunks: the last evidence is Jane reporting no news, with only "sanguine hope" that it would "end well" and perhaps "announce the marriage."

No second young woman, no second elopement, and no ages beyond the vague description above appear anywhere in the supplied text. The chunks come from *Pride and Prejudice* (part 19/26), windows 1–6, including Chapters XLVII and XLVIII. Because the evidence covers only one woman and no completed outcome for even that one affair, I cannot answer the question as posed.
```

**Lane A verdict: refused (honest)** — Lane A's only part (19) covers **Lydia** (elopement to Gretna Green, Wickham's mercenary motive) but no second woman and no ages. The answer says exactly that and refuses. 1/4 required facts.

#### Lane B — vector-free librarian

L4 shortlist from heads: head of **part 14** = the letter (Georgiana/Ramsgate reveal); head of **part 19** = *"She was wild to be at home… nothing could be done for Lydia"* (Lydia's flight); head of **part 20** = *"…a letter arrived… from Mr. Collins"* (Ch XLIX, the pair discovered) → shortlist **[14, 19, 20]**.
L5: 6 windows/part (per-part 6 666 ch).

**Lane B answer (verbatim):**

```text
The evidence is insufficient to answer this question fully.

From the retrieved chunks I can only partially address it. One chunk ([p14:2/6@line160], *pride_and_prejudice* part 14) describes Wickham's attempted elopement with Georgiana Darcy, who "was then but fifteen," an affair that ended when Darcy "joined them unexpectedly a day or two before the intended elopement," thwarting it. Another ([p19:4/6@line374], part 19) contains Lydia Bennet's note saying she is "going to Gretna Green" with the one man she loves, and [p20:2/6@line195] reports that Lydia and Wickham "are discovered" and apparently married. However, none of the retrieved chunks states Lydia's age, so I cannot supply ages for both women as the question requires.

Sources used: [p14:2/6@line160], [p19:4/6@line374], [p20:2/6@line195] (pride_and_prejudice, parts 14, 19, 20).

Because the evidence omits Lydia's age and the confirmation of the second affair's outcome, I cannot give a complete answer and will not draw on prior knowledge.
```

**Lane B verdict: partially correct** — present: **Georgiana Darcy**, *"then but fifteen"*, at **Ramsgate**, the elopement thwarted when Darcy arrived "a day or two before"; **Lydia Bennet**'s elopement and the eventual marriage. missing: Lydia's age (**sixteen** — the phrase *"she was only sixteen last June"* WAS inside Lane B's evidence but it did not connect it to Lydia) and Georgiana's **£30,000** fortune. Real parts cited (14, 19, 20). 3/4 required facts.

---

## 4. Score table

| Question | Lane A | Lane B | Required-fact coverage A | Required-fact coverage B |
|---|---|---|---|---|
| Q1 | partial (2.5/6) | refused | 2.5 / 6 | 0 / 6 (refused) |
| Q2 | refused | partial (3/5) | 0 / 5 (refused) | 3 / 5 |
| Q3 | refused | refused | 3 / 6 (refused) | 3 / 6 (refused) |
| Q4 | correct (5/5) | partial (3.5/5) | 5 / 5 | 3.5 / 5 |
| Q5 | refused | partial (3/4) | 1 / 4 (refused) | 3 / 4 |

**Totals (strict rule: missing any required fact ⇒ partial):**

| Lane | correct | partial | wrong | refused |
|---|---|---|---|---|
| **A** (vector + content) | 1 (Q4) | 1 (Q1) | 0 | 3 (Q2, Q3, Q5) |
| **B** (vector-free librarian) | 0 | 3 (Q2, Q4, Q5) | 0 | 2 (Q1, Q3) |

Neither lane produced a *wrong* (fabricated) answer — both refused honestly whenever the evidence was insufficient.

---

## 5. Lane comparison

**Which lane answered better?** A genuine 2–2–1 split, not a clean win:

- **Lane A wins Q1 and Q4** — exactly the questions where its vector top-1 landed on the right part (part 2; part 9 after a Phase-2 re-query). On Q4 it produced the only fully-correct answer in the whole test.
- **Lane B wins Q2 and Q5** — exactly the questions where the vector lane *missed* the right part (Q2: vector stuck on part 6, Collins's proposal; Q5: vector stuck on part 19, never reaching the Georgiana/Ramsgate reveal in part 14). Lane B's head-read shelf navigation recovered parts 13/14 and 14/19/20.
- **Q3 is a draw** — both lanes found the right part (part 21) and both refused, because the decisive settlement paragraph sat outside both lanes' read windows.

**By question type:**

- *Single-scene / self-contained* (Q1, Q4): vector-first is strong — the chunk is at the answer's location.
- *Multi-part / cross-chapter* (Q2, Q5): the vector lane collapsed one scene onto a **confusable sibling** (Darcy's proposal → Collins's proposal; Georgiana's elopement → Lydia's elopement) and never recovered, even after a Phase-2 re-query. The librarian's content-based part selection handled these better.
- *Exact numeric detail* (Q3): both lanes failed for the same reason — the money facts are ~2/3 into part 21, past the window budget.

**Cost / latency (measured):**

| | Lane A | Lane B |
|---|---|---|
| Retrieval tool calls | 36 (5 `kb_search_vector` + 28 `kb_doc_read` + 3 Phase-2 vector) | 30 (1 `kb_list` + 1 `kb_get_documents` + 28 `kb_doc_read`) |
| Evidence-assembly reads | 30 | 66 |
| **Total MCP calls** | **66** | **96** |
| Retrieval wall time | ≈ 9.5 s (+ Phase-2) | ≈ 10.2 s |
| Answer latency (sum of 5) | 44.2 s (mean 8.8 s) | 45.9 s (mean 9.2 s) |
| Answer input / output tokens | 33 350 / 1 158 | 24 488 / 1 655 |
| Answer cost | $0.2837 | $0.2572 |

Lane B is **~45 % more tool calls** and about the same wall-clock, but slightly cheaper on the answer model (its evidence happened to be more cache-friendly). The vector lane is the cheaper *retrieval* strategy per query; the librarian pays for the catalog + all-description + all-head sweep on every question.

---

## 6. L3 evidence — did the trust check fire?

**Yes.** The description defect was present exactly as warned:

- **24 of 28** KB document descriptions are the boilerplate *"【Part k/26 · Gutenberg front/back matter】Pride and Prejudice (Jane Austen, PG#1342) 英文全文分块——front/back matter 的情节正文…"*.
- The remaining 4 are also untrustworthy: part 1 says *"Chapter I–XIV"* (over-claims — part 1 holds Ch I only), part 2 says *"Chapter XV–I"* (**inverted/degenerate range**), part 18 says *"Chapter XLVI–XLVI"* (**single-point range**).
- Therefore **all 28 descriptions were distrusted** and Lane B fell back to reading the **head (600 chars) of every part** (the L3 fallback). The head text was enough to place each part approximately in the novel, and the L4 shortlists were built from those heads, **not** from the descriptions.
- **Did the vector-free lane still find the right parts?** Yes for Q2 (13, 14), Q3 (21, 20), Q4 (9, 10) and Q5 (14, 19, 20); for Q1 it shortlisted (2, 3) — part 2 *is* correct, but the head of part 2 is the table of contents, so the insult passage sat outside the sampled windows and the exact quote was missed.

This directly confirms the skill's design claim: the L3 trust check is what saves the librarian lane — a description-only librarian would have ranked parts 3–26 as 'front/back matter' and dropped the entire novel.

---

## 7. Honest limitations

1. **Single run per cell.** Each of the 10 answers is one generation from the platform's chat model (`answer_closed_book`, `maxTurns=1`). LLM answers vary run to run; these verdicts are for *this* run only. All 10 calls returned `is_error=false`.
2. **Lane B's extraction is window-placement-sensitive (the biggest caveat).** Both lanes got the same 20 000-char cap, but a ≈30 000-char part needs ≈50–70 % of its text to reach a mid/late passage. Lane B, having no locator, samples 6 evenly-spaced windows per part (≈33 % coverage). Its success on Q2/Q3/Q5 and its miss on Q1/Q4 therefore depend partly on where the windows fell. I used a **fixed** 6-window policy for all questions (not tuned per question), but a different window count or offset would change individual cells. The vector lane does not have this problem — it reads *at* the matching position — which is the core reason vector-first is the primary lane.
3. **Verdicts are strict and judgment-bearing.** I applied the rule 'missing any required fact ⇒ partial'. Lane B's Q2 and Q4 answers are substantively strong and a lenient grader might mark them correct; they are marked partial because they omit one listed characterisation (Q2: the 'inferiority/degradation' framing and Darcy's explicit admission; Q4: Charlotte's age 27 and her 'not romantic / comfortable home' words).
4. **Lane B stayed vector-free (audited).** Across all Lane-B tool calls the script recorded **0** invocations of `kb_search_vector` or `kb_search_two_stage`; Lane A recorded 8 `kb_search_vector` calls (5 Phase-1 + 3 Phase-2). The full per-call log is in `two-lane-test/retrieval_dump.json` (`call_log`) and `two-lane-test/lane_a_phase2.json` (`_log`).
5. **Environment repair was needed.** The backend on `:8771` was **down** at the start (only the web on `:6789` was listening), so the answer channel returned HTTP 401/502. I started the backend (`backend/.venv/Scripts/python.exe main.py`, with `HF_HUB_OFFLINE=1` to avoid a proxy-induced hang), refreshed the auth token, and the channel then worked. Retrieval itself never needed the HTTP backend — the MCP server reads the KB storage directly. This repair is disclosed because it touched the live stack; no knowledge base was modified.
6. **What I could not verify:** (a) whether the KB's 28-document split matches the 26 local part files line-for-line (the KB has extra splits of parts 1 and 22; line offsets used for windows come from the KB's own `totalLines`, not the local files); (b) the exact per-call MCP latency of the Phase-2 re-queries (recorded for Phase 1 and L0–L3 only).

---

## Artefacts

- `two-lane-test/GROUND_TRUTH.md` — reference answers written before grading.
- `two-lane-test/retrieval_dump.json` — Lane A vector hits + gate reads, Lane B L0/L2/L3, full call log.
- `two-lane-test/lane_a_phase2.json` — Lane A Phase-2 refined vector queries + gates.
- `two-lane-test/evidence_packs.json` — the two evidence packs per question (verbatim windows) + read log.
- `two-lane-test/answers.json` — all 10 verbatim answers with latency/tokens/cost.
