# KBS review panel — working ledger (2026-10-12)

Paper under review: `paper-kbs/tex/main2.tex` (elsarticle `[preprint,12pt]`), 80 pp preprint /
37 pp journal variant / 115 pp review variant / 80 pp flat submission package.
Builds: 0 errors, 0 undefined refs, 1 overfull hbox (1.09 pt).
Panel provenance: **native delegated** — six read-only children (`subagent`), each read the
sources itself. Script layer (`paper-audit` `audit.py`, `verify_quotes.py`,
`consolidate_review_findings.py`) did NOT run: `pwsh`/`glob`/`grep` failed all session with
Windows job-runner `0xC0000142` / ripgrep provider failure. All findings below are `[LLM]`
(reading-based), not `[Script]`.

## Parent arbitration (checked by the parent, not delegated)

| # | Panel claim | Parent verdict | Evidence the parent read |
|---|---|---|---|
| A1 | Abstract "on nine of ten questions both arms received identical evidence" contradicts Table 9(a) (Docs packed 12.0 vs 11.2) | **REJECTED** | `n8c_eval.tex:379-381` — the only shortened cell is QK09 (12→4), which changed no grade; 9×12+4 = 112 → mean 11.2. Abstract, body and table agree. |
| A2 | `refs.bib` judge/reranker entries are wrong | **CONFIRMED (2 entries)** | `refs.bib:255-260` `sun-urara` title is "…Investigating Relevance Reasoning with LLM-as-a-Judge"; the published title is "Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents" (ACL Anthology EMNLP 2023). `refs.bib:248-253` `rankgpt` carries the ungrammatical "Are Large Language Models Good at Listwise Rerankers?" with an author list (Sun, Chen, Zhang) that does not match the known author list (Weiwei Sun, Chuan Meng, Qi Meng, Zhaochun Ren, Pengjie Ren, Zhumin Chen, Maarten de Rijke). |
| A3 | "Cross-lingual retrieval is claimed but never measured" | **PARTIALLY REJECTED** | `n_appendix_tables.tex:41-60` `tab:acq-crosslang` measures ingestion success / KB membership / storage completeness / **self-retrieval Hit@1** (40 queries per language), all same-language. The abstract's "a cross-lingual corpus" is accurate; no *cross-language query→document* number is claimed anywhere. Residual action: say once that cross-lingual **querying** is not measured. |
| A4 | "All grounded cells named the gold (12/12) contradicts the gate ablation's 4/8 zeros" | **REJECTED (category error)** | `n8c_eval.tex:13-25` is the *agentic grid* — industrial corpus, questions Q2/Q4/Q6/Q7, engine `omp`/GLM-5.3-Flash. `n8c_eval.tex:358-431` (E8) is the *second corpus*, QK01–QK10, closing channel `claude`. Different corpora, questions and engine. Residual action: state the contrast explicitly (same reading-layer failure appears with a different answering model on the second corpus). |
| A5 | "Tool count inconsistent: 95 in the text vs 94 in the supplementary" | **DISCLOSED, not hidden** | `supplementary-material.md:1104-1110` reports both counts on purpose ("tools 94 against 95, and this document reports both rather than choosing"). A live `tools/list` probe earlier in this session returned exactly **95** registered tools. Residual action: keep 95 in the paper, keep the supplementary disclosure. |

## Panel findings received (verbatim quotes carry over into the final report)

- **Theory / novelty** (14 findings) — contribution ledger C1–C6 (the paper has **six**
  contributions at `n1_intro.tex:66`, not four); five of six are infrastructure whose own
  measurements are null or coverage-only; the one research-grade claim is the
  filter-vs-ranker asymmetry (C5), which is post-hoc, n=16, and rests on a verifier cited to a
  HuggingFace model card (`refs.bib:194-201`); no formalization anywhere (`amsmath` loaded,
  zero equations); positioning table's marks mean "not addressed by the cited work".
- **Devil's advocate** (12 findings) — conclusion claims a reachability advantage its own
  tables refute (`n11_conclusion.tex:19` vs `n8b_eval.tex:85-91`, `:259`); gate-as-filter 0.94
  equals fusion-only and dense 0.94; all 191 judged candidates pass the 0.5 threshold (lowest
  0.589); circularity via gold = unique filename fragment (`n8a_eval.tex:11`) and the
  `{domain}__{arxiv_id}__{slug}` prefix on 322/322 parts; the exp11 report's stronger wording
  ("the dominant failure mode … is the closing model refusing … evidence that contains the
  gold document at rank 1") is not in the manuscript; no human adjudication or inter-annotator
  agreement on any answer-quality number.
- **Editor-in-Chief / KBS desk screen** — verdict **DESK-REJECT-RISK-HIGH**. Seven desk triggers
  named: conclusion contradicted by Table 2; both designed mechanisms null in the matched
  ablations; 16 author-written questions as the whole quantitative base (Wilson [0.23, 0.67]);
  the conclusion's own future-work list is the evaluation the journal would require;
  the 21-paper gap is a headline whose instrument does not exist; **placeholder title-page
  metadata** (`main2.tex:49-54` "Author Name"/"author@example.com", CRediT "Author 1/2",
  `refs.bib:185` AUTHOR ACTION); length ≈5× the soft cap (111 pp double-spaced) and 21 table
  environments; plus novelty risk over the authors' own CIKM 2026 demo whose bib entry says
  `note = {To appear}` while the text says "was published" (`refs.bib:186-192`).
- **Methodology** (15 findings, design scorecard) — scores: baseline adequacy 2/5, statistical
  power 1/5, metric validity 2/5, controls 2/5, reproducibility 3/5, honesty 3/5. Named
  defects: **(i)** no negative control anywhere in E1–E3/E7, so a gate that always passes is
  indistinguishable from one that works; **(ii)** the gate ablation is zero-power by
  construction (gold packed at rank 1 in all arms, identical documents on 9/10 questions) and
  its segment arm got a different evidence budget (2,806 vs 4,000 chars, QK09); **(iii)** the
  second corpus moves domain, language, size and confuser density at once, so the
  "confuser density" mechanism is unidentified; **(iv)** the `p = 0.008` sign test is post-hoc,
  selected from nine configurations, uncorrected, and its guardrail sits 250 lines below the
  abstract; **(v)** baselines are untuned production defaults on a 42-document corpus and the
  Dense baseline is the platform's own embedding model; **(vi)** Graph lane scored 0.56/0.20 in
  a configuration whose relation tagging was bypassed; **(vii)** one local grader carries every
  answer-quality number with no human adjudication; **(viii)** Q6's "judge mishandled 31.35"
  example sits in an artifact whose `gold_ranks` shows Q16 gold absent from the pool.
- **Presentation / clarity** (15 findings + coverage matrix + figure-by-figure table) — the
  retrieval chapter is the strongest part ("a RAG-literate reader can trace one query end to
  end after one reading"); the systemic defect is *missing arbitration*: three incompatible
  decompositions of one platform (four services / four layers / twelve tool groups vs **eight**
  drawn in Fig. 1), and **three-source consistency omits the vector store**, the one store the
  paper shows diverging (18 vs 9 chunks after a rename). Figure defects: Fig. 1's caption
  describes a left/right layout that does not exist; Fig. 3's caption carries the filter claim
  that is plotted in Fig. 6(b); Fig. 6's caption calls its panel (b) "paraphrase collapse" when
  it is the three-verdict-role bars; five of nine figures are composites against KBS guidance;
  Fig. 9 is a 2×2 at 0.80\textheight. Also: `fig:ood` reintroduces a "0.5 refusal threshold"
  the gate chapter argues does not exist; the gate chapter never names the filter role as a
  mode; the nine configurations are not reproducible from any single passage; the `P1–P6`
  principles collide with Lane C's `P1–P5` phases and the P0/P1/P2 credibility tiers.

## Still to arrive

Results-verification (number ledger vs the JSON artifacts).
