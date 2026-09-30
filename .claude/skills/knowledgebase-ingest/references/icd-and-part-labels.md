# D9 ICD + A3c-P Part Labels — rationale and measured failures

Summarized in [SKILL.md](../SKILL.md) §A3c; this file keeps the evidence that motivates the gates.

## D9 — why the Identity-Card Description is the precision ceiling

The exact ICD template:

```
【门类】作品/主题名（原文或别名）· 第 k/N 部分 · 章节范围
事件: 1-3 个具体事实（检索钩子，正文实读所得）
实体: 3-8 个专名
可答: 问题类型; 不含: 易混淆的相邻主题（仅在确有混淆风险时写，须正文可证）
```

Measured 2026-09-26: with vague descriptions the librarian's L2 description matcher gets zero signal and must read a whole multi-novel KB; with ICDs it selects exactly the 3 relevant parts and filters the 3 other novels. Hence:

- **D2 identity anchor repeats in every part** (作品名双语并列) — any part independently addressable; this is the precondition for "filter a multi-work library by work".
- **D4 event fingerprints are precision hooks** — write what actually happens in the chapter ("达西二度求婚，伊丽莎白应允"), never "本章精彩纷呈".
- **The KB description carries the 收录清单** (e.g. "本库仅收《傲慢与偏见》全本 26 part；不含其他作品") — L1 can prune at work level instead of reading the whole "novel library".

Validation: `scripts/identity_card.py validate` 6/6 dimensions (grade `icd-ok`) before saving; `audit` scores the whole library after batch ingests. All subcommands run offline.

## A3c-P — measured part-label failures

- 2026-09-24: a 26-part novel was ingested with **24 of 26** labels reading `Gutenberg front/back matter` while the parts held novel chapters; a description-driven librarian selected 2 parts instead of 7 and lost 2 of 7 key scenes.
- 2026-09-25: **156 of 322** catalog docs shipped with a literal `【?/?·` template prefix; the librarian's L3 trust check flags it as `broken_part_prefix` and refuses to trust the description.

The four label checks (non-boilerplate / non-degenerate / non-placeholder / content-derived) exist because the librarian reads labels, not bodies, when picking parts — a wrong label silently breaks hierarchical retrieval.

## Audit / repair (post-hoc maintenance)

After bulk ingests or split campaigns, dump the catalog (`kb_list` + `kb_get_documents(lightweight)` saved as JSON) and run:

```bash
python .claude/skills/knowledgebase-ingest/scripts/audit_descriptions.py --input catalog.json
# flags: empty / short(<40ch) / broken_part_prefix 【?/?· / boilerplate(≥3 repeats) /
#        degenerate_range / part_anchor_missing

python .claude/skills/knowledgebase-ingest/scripts/repair_part_prefixes.py --input catalog.json            # dry-run plan
python .claude/skills/knowledgebase-ingest/scripts/repair_part_prefixes.py --input catalog.json --apply    # fill 【k/N· from the path, via kb_doc_update_meta
```

The repair is deterministic (no LLM): it only fills the missing `k/N` from the path's `(part k of N)` and skips rows whose live description changed since the dump. Any other defect (boilerplate, content-free, wrong range) requires a content-based A3c rewrite, not a patch.
