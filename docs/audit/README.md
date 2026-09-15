# Audit reports

Completed, self-contained diagnostics of this repository. Each report states what
was checked, what was found, and the evidence for every verdict. Reports are kept
here (and out of `.audit/` / `.ui-audit/`, which are gitignored scratch
workspaces) so the findings stay reviewable and citable.

| Report | Date | Scope | Outcome |
|---|---|---|---|
| [readme-fact-audit-2026-09-13.md](readme-fact-audit-2026-09-13.md) | 2026-09-13 | Every factual claim in `README.md` / `README-zh.md` — counts, performance numbers, architecture, install/CLI | 12 must-fix items identified; the security-relevant "auth is off" claim and the untraceable benchmark table were corrected in the READMEs |
| [api-harness-mechanism-audit-2026-09-13.md](api-harness-mechanism-audit-2026-09-13.md) | 2026-09-13 | Live HTTP E2E across the backend API (121 ops), the Nuxt gateway (124 routes), the 15-engine harness layer, KB management, retrieval, experience, SOUL, graph | Backend and KB management verified sound; gateway surface, SPA-fallback 404 behaviour, and 3 harness defects reported with evidence |

## Method

Both audits were **read-only**: no source file was edited by the auditor. Probe
scripts live in [`scripts/`](scripts/) and can be re-run against a live
deployment to reproduce the counts:

| Script | Purpose |
|---|---|
| `scripts/count_tools.py` | Counts `@mcp.tool()` decorators and per-category buckets in `kb-mcp/server.py` |
| `scripts/api_surface.py` | Enumerates the FastAPI operation surface from the live `/openapi.json` |
| `scripts/live_counts.py` | Probes live service state (KBs, collections, chunks, graph nodes/edges) |
| `scripts/trace_bench.py` | Traces each benchmark figure back to a producing script, or reports it untraceable |

## Standing rule these audits established

Any number quoted in a README, paper, or report must name the committed artefact
that produces it. Figures whose producing script is absent from the repository are
reported as **withheld**, not restated. `docs/paper/cikm/provenance_audit.py`
enforces the same rule for the CIKM paper's data snapshot.
