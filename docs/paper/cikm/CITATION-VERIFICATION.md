# Citation Verification Record — CIKM submission

> Produced 2026-09-16 as the Stage 2.5 / 4.5 integrity artefact for the CIKM
> manuscript. Companion to `refs.bib`; machine-checked by `check_citations.py`.
>
> **Scope statement.** This record certifies: (a) every entry in `refs.bib` is a
> real, searchable publication; (b) every author list, venue, year and page range
> was checked against an authoritative source (ACL Anthology, ACM DL / DBLP, the
> publisher page, or the authors' own repository); (c) every `\cite` key resolves
> and no entry is uncited. It does **not** certify claim-level faithfulness of
> each citation context — that is the separate claim-audit concern.

---

## 1. Method

| Step | Check | Tooling | Result |
|---|---|---|---|
| 1 | Every `\cite` key has an entry; no orphan entries | `check_citations.py` | **0 undefined, 0 orphans** |
| 2 | Entry type matches fields (`booktitle`⇔`@inproceedings`, `journal`⇔`@article`) | `check_citations.py` | **0 structural problems** |
| 3 | Every entry carries a retrieval identifier (DOI / URL / arXiv) | `check_citations.py` | 27/29 with identifier; 3 have venue+pages (findable by title) |
| 4 | Author lists, venues, years, pages | 9 local reference PDFs (first-page metadata) + targeted lookups against ACL Anthology / DBLP / ACM DL / publisher pages | 4 errors found and fixed (§2) |
| 5 | Cited artefacts have live producers; named producers exist | `provenance_audit.py` | **GATE PASSED** (10/10 cited traceable, 14/14 producers exist) |

Re-run: `python check_citations.py && python provenance_audit.py`

---

## 2. Errors found and corrected

The bibliography had already been through one metadata-correction pass; this pass
found **four further author-level defects**, all of the same class — a plausible
but wrong name list that a reader would not catch without checking the source.

### 2.1 `yang2018hotpotqa` — three fabricated authors 🔴

| | |
|---|---|
| Was | Yang, Qi, Zhang, **Chen, Yinghai**, **Wang, Waleed**, **Bajaj, Mohit**, Salakhutdinov, Cohen |
| Correct | Yang, Zhilin; Qi, Peng; Zhang, Saizheng; **Bengio, Yoshua**; **Cohen, William W.**; Salakhutdinov, Ruslan; **Manning, Christopher D.** |
| Source | ACL Anthology D18-1259 + authors' own BibTeX at `hotpotqa.github.io` |

Three real authors were replaced by three non-authors. Pages (2369–2380) and DOI
(10.18653/v1/D18-1259) were correct and are now recorded.

### 2.2 `lu2026aiscientist` — wrong title + two missing authors 🔴

| | |
|---|---|
| Was | *The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery*; 6 authors |
| Correct | ***Towards End-to-End Automation of AI Research***; 8 authors (adds **Yamada, Yutaro** and **Hu, Shengran**) |
| Source | Nature 651(8107):914–919, 2026; DOI 10.1038/s41586-026-10265-5 (PubMed 41882133, ORA record) |

The title used was the **2024 arXiv preprint** title; the published article was
retitled and gained two authors. Volume, issue, pages and DOI are now recorded.

### 2.3 `ge2026mcppyserini` — two missing authors 🟠

| | |
|---|---|
| Was | Ge, Yijun; Guo, Zibo |
| Correct | Ge, Yijun; Guo, Zibo; **Sharifymoghaddam, Sahel**; **Lin, Jimmy** |
| Source | the paper's own first page (local PDF) |

### 2.4 `su2025bright` — garbled author list, wrong key 🟠

| | |
|---|---|
| Was | Su; Yen; Xia; Shi; **Wang, Niklas**; **Lu, Yao**; *and others* (key `su2024bright`) |
| Correct | 15 authors: Su, Yen, Xia, Shi, **Muennighoff, Niklas**, Wang, Han-yu, Liu, Haisu, Shi, Quan, Siegel, Tang, Sun, Yoon, Arik, Chen, Yu (key `su2025bright`) |
| Source | official BibTeX at `github.com/xlang-ai/BRIGHT`; OpenReview `ykuc5q381b` |

"Wang, Niklas" mis-merged two authors (Han-yu Wang + Niklas Muennighoff) and
"Lu, Yao" is not an author of this paper. The bibkey now matches the authors'
own key, and the one `\cite` site was updated.

### 2.5 Entry-type defects (3) 🟡

| Key | Was | Now |
|---|---|---|
| `yan2024crag` | `@inproceedings` with `booktitle = {arXiv preprint…}` | `@article` with `journal` (matches the authors' own citation) |
| `nogueira2019rerank` | `@inproceedings` carrying a `journal` field | `@article` |
| `izacard2022contriever` | `@inproceedings` for a TMLR journal article | `@article` |

---

## 3. Orphan entries — resolved by citing, not deleting

Four entries were in `refs.bib` but never cited. Rather than delete them
(which would have lost relevant related work), each was verified and placed where
it is genuinely relevant:

| Key | Placement | Why it belongs |
|---|---|---|
| `su2025bright` | Related Work, "Dense and hybrid retrieval" | BRIGHT is the reasoning-intensive retrieval benchmark; it extends BEIR's cross-domain stress test |
| `tagme2010ferragina` | Related Work, "Knowledge organisation and graph RAG" | TAGME is the antecedent of entity-structured retrieval that GraphRAG/HiRAG extend |
| `lu2026aiscientist` | GenAI Usage Disclosure | the canonical reference for end-to-end research automation; the disclosure now states the narrower boundary this work claims |
| ~~`bert4rec2019sun`~~ | **removed** | BERT4Rec (sequential recommendation) has no genuine connection to this work; a forced citation would be worse than none |

---

## 4. Identifiers added (findability)

Eight entries gained an authoritative identifier, each verified before writing:

| Key | Identifier |
|---|---|
| `lewis2020rag` | arXiv:2005.11401 |
| `karpukhin2020dpr` | DOI 10.18653/v1/2020.emnlp-main.550, arXiv:2004.04906, pp. 6769–6781 |
| `izacard2022contriever` | arXiv:2112.09118 |
| `robertson2009bm25` | DOI 10.1561/1500000019 |
| `thakur2021beir` | arXiv:2104.08663 |
| `yao2022react` | arXiv:2210.03629 |
| `schick2023toolformer` | arXiv:2302.04761 |
| `glass2022re2g` | DOI 10.18653/v1/2022.naacl-main.194, arXiv:2207.06300, pp. 2701–2715 |
| `tagme2010ferragina` | DOI 10.1145/1871437.1871689 |
| `ge2026mcppyserini` | DOI 10.1145/3805712.3808376 |
| `yang2018hotpotqa` | DOI 10.18653/v1/D18-1259 |
| `su2025bright` | arXiv:2407.12883, OpenReview `ykuc5q381b` |
| `jeong2024adaptiverag` | venue expanded to NAACL 2024 + pp. 7036–7050 (from the paper's own first page) |
| `suresh2026agenticrag` | arXiv:2605.05538 (from the paper's own first page) |
| `li2026deepread` | arXiv:2602.05014 (from the paper's own first page) |

Three entries intentionally have no DOI/arXiv: `huang2025hirag` (Findings of
EMNLP 2025, pp. 6044–6060), `jeong2024adaptiverag` (NAACL 2024, pp. 7036–7050)
and `sahay2025autokb` (NAACL 2025 Industry Track, pp. 708–723). Each carries a
**verified venue and page range read from the paper's own PDF**, which is
sufficient for retrieval; inventing an identifier would have re-introduced
exactly the defect class this record exists to prevent.

---

## 5. Residual risk (stated, not hidden)

* **Claim-level alignment is not audited here.** This record checks that
  references are real and correctly attributed; it does not verify that each
  citation context faithfully represents the cited work's claim. A sampled
  claim↔reference audit remains open.
* **Three entries lack a persistent identifier** (§4) — findable by title and
  venue, but not by DOI.
* **Verification is point-in-time (2026-09-16).** Publisher metadata can change;
  re-run the checks before camera-ready.
