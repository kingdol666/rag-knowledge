# CIKM Demo compliance & style audit — QDCVR

Audited build: `tex/main.pdf`, 5 pages = **body 4 pp** + pp. 5 (GenAI disclosure +
references, both excluded from the page limit).
Reference set: the six CIKM demo papers in `reference/` (PolyUQuest, AppAgent-Pro,
SAFE-Cascade, SearchLog, JustEva, PrismaDV); distilled rules in
[`FIGURE-STYLE-GUIDE.md`](FIGURE-STYLE-GUIDE.md).

## 1. Hard requirements (CIKM 2025 Call for Demo Papers)

| Requirement | Status | Evidence |
|---|---|---|
| ≤ 4 pages incl. appendices | ✅ | body ends p4, after Conclusion + Acknowledgments + Data Availability |
| Unlimited references | ✅ | p5 |
| GenAI disclosure **before** references, outside the page budget | ✅ | `sec4_backmatter.tex` order: GenAI → Competing Interests → References |
| ACM **sigconf**, two column | ✅ | `\documentclass[sigconf]{acmart}` |
| **Single-blind** — real names required | ⚠️ | `Author Name` / `Affiliation` are placeholders; **must be filled before submission** |
| 3-minute demo video, URL in the paper | ⚠️ | URL present in 3 places; **goes live once the commit is pushed** (see §5) |
| Funding + competing-interest disclosure | ⚠️ | Competing interests written; funding line is still a placeholder |
| Intended audience | ✅ | §1, last sentence of the contribution setup |
| Innovative aspects | ✅ | §2.5 "Design Choices and Innovation" — three named contracts |
| Contribution to SOTA | ✅ | §3 Performance highlights + Fig. 2 |
| What attendees will experience | ✅ | §3, first sentence of each scenario |
| Functionality & user scenarios | ✅ | §3 Scenarios 1–3 |
| Interface / interaction options | ⚠️ | covered in prose (§2.4, §3 demo setup) and in the video; the UI figure was retired for page budget (§4) |
| Comparison with existing systems | ✅ | §2.5 prose comparison + the three-track comparison in Fig. 2 |
| **R&D challenges** (review criterion) | ✅ | §2.6 "Engineering Challenges" |

## 2. Layout vs the six reference papers

| Dimension | Reference practice | This paper | Verdict |
|---|---|---|---|
| Section skeleton | Intro → System → Demonstration → Conclusion (+ GenAI, refs) | identical | ✅ matches |
| Figure 1 | full-width architecture at top of p.2, traced by one real query | full-width architecture at top of p.2, orange trace = the NISQ query | ✅ matches |
| Architecture figure content | clients → services → storage, real query printed in the figure | same, with the query string and the gate score printed in the figure | ✅ matches |
| Number of exhibits | 2–4 figures + 1–3 tables, ~1 exhibit per content page | 2 figures, 0 tables (aggregates folded into Fig. 2) | ✅ in range |
| Table row entity | compared method, proposed system last | Fig. 2 carries the same three-way comparison as three columns | ✅ equivalent |
| Cost / latency column | near-mandatory, ↓ arrows | latency in each column header and in the aggregate strip | ✅ present |
| Caption pattern | `Figure N: <3–7-word title>.` + 1–4 present-tense sentences; every callout explained | both captions follow this: short title then 5–6 sentences, every panel explained | ✅ matches |
| Figure caption placement | below figures | below figures | ✅ |
| "Fig." abbreviation | never used | never used | ✅ |
| Exhibit without in-text reference | never happens | both figures referenced in §2 and §3 | ✅ |
| Standalone results bar chart in the body | never used | none | ✅ |
| Colour-only encoding | never | every verdict carries a ✓/✗ glyph and a word, not just colour | ✅ |
| Full-desktop screenshots | cropped to panels/columns | the console appears only in the video, cropped to panels | ✅ |

## 3. Figure aesthetics

**Figure 1 (architecture).** Landscape 2:1, four labelled bands with one dominant
left-to-right arrow direction, terracotta trace on a near-monochrome grey base,
greyscale-safe, no shadows, no vertical rules. One real query string and its gate
score are printed inside the figure — the reference papers do exactly this
(AppAgent-Pro prints "How to keep a cat"; PolyUQuest prints a real course question).
The exhibit is small because the page budget forced it to 0.50`\textwidth`; the box
labels remain legible at 100 % zoom but it is the weakest exhibit in the paper.

**Figure 2 (three-track evidence).** This is the figure the paper is built around.
Three columns, one per track, each carrying: contract and latency in the header, a
✓/✗ verdict chip, the **verbatim** recorded answer, the citation, and — beneath all
three — a shared aggregate strip with the 10-question numbers. Design follows the
reference conventions directly: the real string is printed in the figure (the actual
question, the actual answers), the proposed system's column is outlined in the accent
colour while the baselines stay neutral, and the takeaway is stated in the footer
rather than left to the reader. It replaces a results table, which the reference
papers also do (PolyUQuest folds its ablation into Table 1; PrismaDV states the
takeaway in the caption).

**What is weaker than the references.** The reference papers all print a UI
screenshot with numbered callouts (PrismaDV 1–6, PolyUQuest (1)(2)(3)). This paper
has no such figure — it was cut to stay inside four pages. The interface is instead
demonstrated in the 3-minute video, which is the track's primary artefact.

## 4. The one editorial trade-off

Four pages cannot carry three full-width figures *and* the required prose. Measured
marginal costs at `\textwidth`: a full-width figure ≈ 2 columns of text, so three
figures ≈ 1.5 pages of a four-page budget. The UI composite (`fig2_ui_composite.png`)
was therefore retired from the paper and kept in the repository and the video.

**If you would rather keep the UI figure than the evidence figure**, the swap is one
line in `main.tex`: re-add the `figure*` block for `fig2_ui_composite.png` and remove
the one for `fig3_threeway.png`. Expect to cut a further ~250 words to stay at four
pages. Our recommendation is to keep the evidence figure — a demo paper is judged on
what the system does, and Fig. 2 is the only exhibit that shows a real answer, a real
citation and a real failure side by side.

## 5. Outstanding before submission

1. **Push the video commit** so the URL resolves:
   ```bash
   git push origin master
   ```
   then check the link opens:
   `https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4`
   (The repo URL in the paper was also wrong — it said `kingdol/rag-knowledge`, which
   is a 404; it is now `kingdol666/rag-knowledge`, verified public.)
2. **Author names and affiliations** — the demo track is single-blind.
3. **Acknowledgments / funding** — currently placeholder text.
4. **`\acmConference`** venue city and dates are placeholders for camera-ready.

## 6. Verdict

| Aspect | Verdict |
|---|---|
| Hard CIKM demo requirements | **passes**, modulo the two author-side placeholders (names, funding) |
| Page budget | **passes** — body 4 pp, disclosures and references on p5 |
| Layout vs the six reference papers | **passes** — same skeleton, same Fig.-1 convention, same caption discipline |
| Figure aesthetics | **passes**; Fig. 2 is the strongest exhibit and is built to the reference conventions. Fig. 1 is legible but small, and the paper carries no UI-callout figure — the two places where it sits below the reference set |
| Content completeness | system functions, architecture, execution flow, innovation, comparison with conventional RAG, and future retrieval direction are all present and sourced |
| Typesetting | 0 overfull boxes, 0 undefined references, 0 LaTeX errors, 0 garbled glyphs |
