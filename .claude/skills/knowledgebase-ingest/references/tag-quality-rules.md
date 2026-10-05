# Tag Quality Rules — Tag Quality Gate

> **Core principle**: tags are retrieval's "signposts"; they must be **domain concept words** distilled from the content — not filename fragments, section titles, or test residue.
> Junk tags directly pollute `kb_doc_get_by_tag` recall and Path B of enterprise retrieval.

## Golden Rule

**Read the content first, then extract tags.** Tagging without reading the document body (≥2000 chars) is forbidden.
Every tag must satisfy: (1) it is a domain concept/technology/method/material/scenario word; (2) it genuinely appears in the body; (3) it is deduplicated and normalized against the existing vocabulary.

---

## T1 — Blocklist (any hit is discarded, never stored)

### T1a Section titles / paper-structure words
When parsing PDFs, headings are easily mis-extracted as tags. **All of the following patterns are rejected**:

| Pattern | Examples (field-observed junk) |
|---|---|
| Paper section numbers | `1 Introduction` `2 Tasks and Terminol` `3 Method` `3.1 Adapting GLIP` `4 Experiments` `5 Related Works` `6 Conclusions` `7 Limitations` `8 Ethics` |
| Appendix/acknowledgments/references | `Acknowledgments` `References` `A.1 GPT Prompts` `B.1 Narration Proces` `B.3 Hyperparameters` |
| Abstract/keywords | `Abstract` `Keywords` `摘要` `关键词` |
| Truncated residue | Any title ending in `...` or otherwise truncated (`Localizing Active Ob`) |
| Pure structural words | `完整版` `基线对比` `综述` (when used standalone without context) |

**Detection regexes**: `^\d+(\.\d+)*\s` (starts with a section number), `^(Abstract|References|Acknowledgments|摘要|关键词|附录)`.

### T1b Test / debug tags
| Pattern | Examples |
|---|---|
| Contains "test" | `test-tag-ingest` `test` `mcp-test-tag` `ingest-test` `test-ops` `metadata-test` `edge-test-tag` `integration-test` `skill-test` `test-batch-tag` `testing` |
| Contains the meta-word "tag" | `graph-test-tag` `web-api-test-tag` `tag with spaces & special!` |
| Process markers | `3-layer-sync` `verification` `e2e` |

### T1c Descriptive / meta tags
Tags that describe the "document state" rather than the "document content":
- `文件名内容不匹配` `待补` `未验证` `draft` `TODO` (filename-content mismatch / to-be-filled / unverified)
→ These belong in the description or an audit note, **never as tags**.

### T1d Invalid format
- Contains spaces (unless an established compound word like `deep learning`)
- Contains special characters `!@#$%^&*`, pure punctuation, pure digits, or is overlong (>30 chars)

---

## T2 — Normalization (normalize before finalizing tags)

### T2a Case normalization
Chemical formulas/abbreviations unified to uppercase: `pet`→`PET`、`pe`→`PE`、`pp`→`PP`、`pa6`→`PA6`、`pla`→`PLA`、`pvdf`→`PVDF`.
Generic technical words unified (except initialisms): `Transformer`/`transformer`→`Transformer` (proper architecture names keep capitals), `deep-learning`/`Deep-Learning`→`深度学习` (prefer the existing Chinese vocabulary word).

### T2b Chinese-English synonym merging (existing vocabulary words win; new words map to the established primary)

| Domain | Primary tag | Merged away |
|---|---|---|
| Polymers | `PET`/`聚酯` | `pet` `bopet` (unless emphasizing film processes) |
| | `PE`/`聚乙烯` | `pe` `uhmwpe` (UHMWPE is a special case, kept) |
| | `PP`/`聚丙烯` | `pp` `bopp` |
| | `PA6`/`聚酰胺` | `pa6` `pa56` `bopa6` (different grades kept separately) |
| | `PLA`/`聚乳酸` | `pla` |
| AI | `Transformer` | `transformer` `attention-mechanism` (the latter may be kept as a supplement) |
| | `强化学习` | `Reinforcement Learning` |
| | `机器学习` | `machine-learning` `ML` |
| Materials | `石墨烯` | `graphene` |
| | `MXene` | `mxene` |

**Rule**: query `kb_tags_list()`; if the Chinese primary word already exists, normalize new English tags to Chinese, and vice versa. **Keep only one of any synonym pair** to avoid vocabulary bloat.

### T2c Naming style unification
- Materials/chemistry: chemical formulas uppercase (`PET` `TiO₂`)
- Methods/algorithms: Chinese names preferred (`双向拉伸` `强化学习`), English proper names kept (`Transformer` `GraphRAG` `Self-RAG`)
- Equipment/processes: Chinese (`拉幅机` `挤出沉积`), unless the English term is industry-standard (`TDO`)

---

## T3 — Count and Content Criteria

| Dimension | Requirement |
|---|---|
| **Count** | **2-5 per document**. <2 is too scattered to recall; >5 is noisy |
| **Reuse rate** | **≥90%** reused from the existing `kb_tags_list()` vocabulary; add new words only when they represent a brand-new concept |
| **Granularity** | 1 material word + 1 method/process word + 1 scenario/application word + 0-2 fine attributes. E.g. `PET / 双向拉伸 / 结晶度 / 拉幅机` |
| **Body verification** | Every tag must **genuinely appear** in the ≥2000-char body sample, or be its direct hypernym |

---

## T4 — Execution Flow (at Ingest)

```
1. Read ≥2000 chars of the body
2. Candidate tags = distill 5-8 domain words from the content
3. T1 blocklist → discard hits
4. T2 normalization → unify casing, merge synonyms
5. T3 count trimming → keep the top 2-5 (material/method/scenario/attribute)
6. Compare against kb_tags_list() → ≥90% reuse; confirm new words are brand-new concepts
7. Body readback → confirm every tag appears in the content
8. kb_doc_update_tags(tags=cleaned_tags)
```

## T5 — During Cleanup (used by organize O8)

For an already-polluted vocabulary, scan `kb_tags_list()`:
- T1 blocklist hit → remove the tag from all documents
- T2 synonym duplicates → map uniformly to the primary word, replace via `kb_doc_update_tags`
- Orphan tags with 0 document references → auto-purged by the system, no manual action
- Unique to 1 document and not a new concept → consider merging into the primary word

**Field status**: the current vocabulary is 376 tags, of which ~40 are section titles, ~17 are test tags, and ~15 are synonym-duplicate groups → after cleanup, expect ~280 tags and a significant recall-precision improvement.
