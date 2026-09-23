# Cross-KB Synthesis — Cross-Knowledge-Base Experience Synthesis

> When one experience spans multiple KBs' domains (e.g. "RAG retrieval optimization" touching both AI-ML-Research
> and Materials-ML), you must decide ownership, dedup, and linkage strategy.

## Table of Contents
- [When does cross-KB synthesis happen](#when-does-cross-kb-synthesis-happen)
- [Ownership decision](#ownership-decision-which-kb-gets-the-experience)
- [Cross-KB dedup](#cross-kb-dedup)
- [Cross-KB retrieval verification](#cross-kb-retrieval-verification)
- [Link maintenance](#link-maintenance)

---

## When Does Cross-KB Synthesis Happen?

| Scenario | Example |
|------|------|
| A user question touches documents in multiple KBs | "RAG applied in materials science" (RAG 在材料科学的应用) → AI-ML-Research + Materials-Science |
| A meditation-found question cluster spans multiple domains | "vector index fragmentation" (向量索引碎片) → every KB with an index |
| Experiences need re-owning after a document move | Document moved from KB-A to KB-B; the experience follows |

---

## Ownership Decision: Which KB Gets the Experience?

```
Decision logic (priority from high to low):

1. The user's explicit assignment ("put it in AI-ML-Research") → use it directly
2. Majority ownership by related_docs → put the experience in the KB holding the most of its documents
3. Core-domain ownership → the KB matching the question's most core domain word
4. Nothing decisive → put it in the parent/general KB; mark the related domains in tags
```

### Decision Tree

```
Which KBs does the experience involve?
  ├── Only 1 KB → put it in that KB (simple)
  ├── 2-3 KBs with a clear primary → put it in the primary-domain KB; tags include the secondary domains
  ├── 2-3 KBs with no primary → put it in the KB holding the most related documents
  └── Library-wide (e.g. "ragctl usage") → put it in the general KB, or one copy per KB
```

> ⚠️ **Do not put a full copy in multiple KBs** — it creates a maintenance nightmare (updates get missed somewhere).
> Exception: the "library-wide and each KB searches independently" scenario.

---

## Cross-KB Dedup

Search across KBs before creating:

```
experience_search_global(query="<core keywords>", top_k=10)
  → check whether a cross-KB experience already covers it

Already covered:
  - Similar one in the same KB → experience_update (see crud-and-migration.md)
  - Similar one in another KB (different library) → evaluate whether this KB needs its own copy:
    * This KB has unique context/documents → creating anew is allowed; mark the linkage in tags
    * Pure duplicate → do not create; optionally add a "pointer experience" in this KB (lightweight, pointing at the other KB's exp_id)
```

### Pointer Experiences (Cross-KB References)

When an experience already exists at high quality in another KB, this KB only needs the index entry, not a copy:

```yaml
title: "[Cross-KB reference] Vector index defragmentation (see AI-ML-Research)"   # 原文: "[跨库引用] 向量索引碎片整理（详见 AI-ML-Research）"
scenario: "cross-kb-ref-index-dedup"
category: tip
problem: "This KB may also hit vector index fragmentation; the full experience is at AI-ML-Research/exp-87993d41a050"   # 原文: "本库也可能遇到向量索引碎片化，完整经验见 AI-ML-Research/exp-87993d41a050"
solution: "See exp-87993d41a050 in AI-ML-Research; core step: kb_reindex(force=true)"   # 原文: "参见 AI-ML-Research 的 exp-87993d41a050，核心步骤：kb_reindex(force=true)"
key_lessons:
  - "For the general fix to vector index fragmentation, see AI-ML-Research/exp-87993d41a050"   # 原文: "向量索引碎片问题通用解法见 AI-ML-Research/exp-87993d41a050"
tags: ["跨库引用", "索引", "去重"]
related_docs: []
```

> Pointer experiences are lightweight and avoid content duplication, while guaranteeing this KB's retrieval can hit them and be directed to the full experience.

---

## Cross-KB Retrieval Verification

When inducing a cross-KB experience, verify the answer sources cover all relevant KBs:

```
For each relevant KB:
  kb_search_two_stage(query, kb_id=<KB>) → collect hits
  kb_doc_read(kb_id, top_doc) → extract key conclusions

Merge the hits across KBs → confirm the solution does not neglect any KB's perspective
```

---

## Link Maintenance

Cross-KB experiences need their tag linkage maintained, for cross-KB discovery:

```
Include all related domain words in tags:
  ["rag", "检索优化", "ai-ml", "materials-ml", "跨库"]

That way experience_search_global can recall across KBs via tags.
```

When documents of a cross-KB experience move (see [crud-and-migration.md](crud-and-migration.md)),
re-evaluate whether the ownership still makes sense.
