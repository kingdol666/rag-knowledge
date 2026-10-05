# Query prep detail (knowledgebase-search Phase 0)

Read this when the query is ambiguous, incident/ops-flavored, or a multi-entity
comparison. The SKILL.md holds the rule; this file holds the tables and examples.

## Intent classification

| Type | Features | Retrieval emphasis |
|---|---|---|
| Factual | "what is", "definition" | Vector first; authoritative review documents |
| Method | "how to", "methods" | Vector first; tags as fallback path |
| Comparison | "A vs B", "difference" | Parallel multi-entity recall; keep the best chunk per entity |
| Incident/ops | "error", "failed", "how to fix" | **Experience library first** (`experience_search_global`), then documents |
| Experience/case | "similar cases", "how was it handled" | `experience_search_global` first, documents as supplement |
| Navigational | "where is", "is there" | `kb_list(lightweight=true)` + `kb_get_documents(lightweight=true)` description matching |

## Core entity extraction

Extract **subject** (PET / RAG / lithium battery) + **attribute** (crystallinity /
hallucination / thermal management) + **constraints** (process parameters / 2024).

## Rewrite examples

- Raw: `"PET薄膜双向拉伸工艺参数对结晶度的影响"`
  → vector: `"拉伸比/温度/速度对 PET 涤纶薄膜结晶度和晶体结构的影响"`
- Raw colloquial question → **declarative sentence + keyword combination**;
  keep the corpus's language (English corpus → English query variants).
- Comparison: split into one sub-query per entity, run in parallel, keep the
  best chunk per entity in addition to the global filter.

## Criterion hints for the verify gate

- Lookup/factual question → `criterion="evidence"`
- Enumeration/completeness question ("which", "list all") → `criterion="instance"`
- Unsure → `criterion="auto"` (intent heuristic)
