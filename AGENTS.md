# AGENTS.md — cross-harness entry point

> **Canonical agent instructions live in [`CLAUDE.md`](./CLAUDE.md) — read it first.**
> This file exists so that harnesses which discover `AGENTS.md` (pi, codex, cursor,
> opencode, qwen, crush, dsh, hermes, …) also reach this project's skills.

## Where the skills live

- **Canonical**: `.claude/skills/<name>/SKILL.md`
- **Mirrored (symlink → canonical)**: .agents/skills, .claude/skills, .github/skills, .omp/skills
- Regenerate with `python scripts/sync_skills.py`; verify with `python scripts/validate_skills.cjs`.

## Skill index (generated — do not edit by hand)

| skill | what it does | path |
|---|---|---|
| `butian` | "Butian — SOUL persona initialization distillation dispatcher: orchestrates the dual nuwa-skill (deep research distillation of public figures/topics/t | `.claude/skills/butian/SKILL.md` |
| `dot-skill` | "Unified meta-skill engine for distilling colleague, relationship, or celebrity characters into reusable Skills. Triggered by: colleague persona, dist | `.claude/skills/dot-skill/SKILL.md` |
| `knowledgebase` | "Knowledge base management — primary entry point and dispatcher. Routes user requests to the correct sub-skill based on scenario matching (ingest, sea | `.claude/skills/knowledgebase/SKILL.md` |
| `knowledgebase-batch` | "High-volume batch operations. B1→B7: bulk tag migration, bulk description updates, directory mass ingestion (file-type routing), mass document move,  | `.claude/skills/knowledgebase-batch/SKILL.md` |
| `knowledgebase-experience` | "Experience full lifecycle management E0-E12. Structured practice cases (scenario/problem/solution/lessons). Auto-extract from KB docs (E0 prepare+LLM | `.claude/skills/knowledgebase-experience/SKILL.md` |
| `knowledgebase-experience-summarize` | "Experience authoring, meditation (auto-induction), cross-KB synthesis, and experience CRUD + migration. Full lifecycle: CREATE / UPDATE / DELETE / MI | `.claude/skills/knowledgebase-experience-summarize/SKILL.md` |
| `knowledgebase-graph` | "Knowledge graph build, query, and analysis for Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership). Build per | `.claude/skills/knowledgebase-graph/SKILL.md` |
| `knowledgebase-ingest` | "Document ingestion pipeline with quality gates A0→A9. Content-first workflow: dedup (content fingerprint), survey, parse with quality check, SCRIPTED | `.claude/skills/knowledgebase-ingest/SKILL.md` |
| `knowledgebase-init` | "Smart incremental installation wizard for the RAG Knowledge Platform. Audits the existing environment FIRST and only installs/configures/downloads wh | `.claude/skills/knowledgebase-init/SKILL.md` |
| `knowledgebase-librarian` | "Librarian retrieval — hierarchical COARSE→FINE whole-library search, VECTOR-FREE (no embedding / BM25 / hybrid ranking). Walks the stacks: read EVERY | `.claude/skills/knowledgebase-librarian/SKILL.md` |
| `knowledgebase-list` | "Knowledge base listing and discovery. L1→L3 read-only workflow: full inventory (KB names + descriptions + doc counts + tag vocabulary), KB drill-down | `.claude/skills/knowledgebase-list/SKILL.md` |
| `knowledgebase-manage` | "Document and KB administration. M1→M6 workflow: survey, confirm destructive ops, execute (move/rename/delete/merge/update), post-change reindex+exper | `.claude/skills/knowledgebase-manage/SKILL.md` |
| `knowledgebase-organize` | "Full collection restructuring engine. O1→O8 workflow (plus O5b three-way consistency): hierarchical discovery (sub-KB split detection + cross-KB merg | `.claude/skills/knowledgebase-organize/SKILL.md` |
| `knowledgebase-search` | "QDCVR v2 — Vector-First, Content-Gated, Librarian-Fallback Retrieval. Phase 0 query prep → Phase 1 vector search FIRST (kb_search_vector, balance_kbs | `.claude/skills/knowledgebase-search/SKILL.md` |
| `knowledgebase-update` | "Check the installed RAG Knowledge Platform version against the latest GitHub release / default-branch VERSION, and pull updates when available. Safe  | `.claude/skills/knowledgebase-update/SKILL.md` |
| `knowledgebase-verify` | "Knowledge base integrity and quality validation. V1→V9: three-way metadata consistency (disk↔.tree-fs.json↔.knowledge-base.yml), document integrity,  | `.claude/skills/knowledgebase-verify/SKILL.md` |
| `musk-perspective` | "Elon Musk's thinking framework. Based on 6-dimension deep research (writings/conversations/ expression/external views/decisions/timeline), it distill | `.claude/skills/musk-perspective/SKILL.md` |
| `nuwa-skill` | "Nüwa persona-making: input a person's name, a topic, or even just a vague need, and it automatically runs deep research → thinking-framework extracti | `.claude/skills/nuwa-skill/SKILL.md` |
| `soul` | "SOUL persona system — full persona lifecycle management (create/delete/configure/list), Butian (nuwa-skill × dot-skill dual-engine) distillation of i | `.claude/skills/soul/SKILL.md` |
| `soul-rag` | "SOUL retrieval-augmented adapter — combines \"knowledge base retrieval\" with \"SOUL persona processing\" into a unified Q&A strategy: first locate k | `.claude/skills/soul-rag/SKILL.md` |

*20 skills. Generated by `scripts/sync_skills.py`.*
