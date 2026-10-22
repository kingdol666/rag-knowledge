# Reviewer verification — capability audit run (2026-10-21)

Reviewer: general-purpose agent (fresh context). Method: re-derived every
claim with fresh commands and its own read-only MCP probe; no files modified.

| # | Item | Result | Evidence observed |
|---|---|---|---|
| 1 | CAPABILITY.md vs result.json | PASS | 33 steps / 0 fails; every cited number matches (laya 0.8838, clean_immediately, new-path 2 / stale 0 hits, two_stage token found, kb_count 21) |
| 2 | Static mapping line numbers | PASS | all cited kb-mcp/server.py and vector_service.py / kb-instruction.ts lines exact (kb_create:446 parent_id, move:698 hygiene, laya:2863, budget 28000:211, groups 506-584, recursion 172-202, rewrite :44 / dedup :49) |
| 3 | Probe legitimacy | PASS | disposable timestamped tree; laya reference mode (JSON-string refs, no content); settle-window new-vs-stale classification; finally deletes exp→doc→child→parent + kb_list absence check; zero HTTP (stdio only) |
| 4 | Live-state re-check | PASS | own MCP probe: tools/list = 95; no `ZZ-Cap-*` KB remains; no merge/split tool in live list |
| 5 | Gap-list honesty | PASS | no merge tool; split only as ingestion-side script (`.claude/skills/knowledgebase-ingest/scripts/split_large_doc.py`); kb_doc_update_meta:644 has no hygiene block vs move:698 |

Reviewer note: matrix row 7 initially said "索引 2 chunks" where the first index
call returned 1 chunk (2 = post-move/force-reindex steady state); corrected in
CAPABILITY.md after the review.

## VERDICT: APPROVE

Post-review regression: dev_smoke 21/21 PASS; validate_skills PASS.
Deslop pass: simplified the finally-block state recovery in
run_capability_probe.py (now uses the tracked `exp_id`/`new_path` variables
directly); recorded results unaffected.
