# Ground truth (verified 2026-10-13 before the run)

Every injected question's gold document was verified to exist in BOTH corpora:
- corpus_md 100-paper set (bm25/rrf substrate): `ls data/corpus_md | grep <id>` = 1
- live platform library (mode A/B/C substrate): kb_search metadata hit with KB attribution

| qid | gold arXiv id | live KB | question source |
|---|---|---|---|
| qk_QK01 | 1706.03762 | 计算机与人工智能 | Quick10 QK01 provenance |
| qk_QK02 | 1602.01876 | 生命科学与医学 | Quick10 QK02 cross-KB genomics |
| qk_QK03 | 1606.00335 | 工程与能源 | Quick10 QK03 materials/mechanism |
| qk_QK04 | 2209.15032 | 计算机与人工智能 | Quick10 QK04 numeric (94%) |
| qk_QK05 | 2508.05896 | 生命科学与医学 | Quick10 QK05 numeric (7-10%) |
| qk_QK06 | 1503.07557 | 自然科学与地球科学 | Quick10 QK06 chunk-window |
| qk_QK07 | 2608.05850 | 计算机与人工智能 | Quick10 QK07 distractor (multiple LM papers) |
| qk_QK08 | 2409.13934 | 自然科学与地球科学 | Quick10 QK08 cross-KB GAN/climate |

QK09 (unanswerable) / QK10 (out-of-corpus) are excluded here: the retrieval-layer
gate is gold-recall; their honesty behavior is covered by the chatmodes refusal
battery (cm5-cm9) at the system layer.
