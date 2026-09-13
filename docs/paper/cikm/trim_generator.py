"""Trim make_assets.py so it emits ONLY provenance-verified assets.

Everything after the in-house table emitter consumed the withheld CIKM artefact
(no producer — see PROVENANCE.md), so it is removed rather than commented. The
file keeps: system scale, ingestion, SciFact, in-house, experience.
Idempotent: does nothing if already trimmed.
"""
import re

p = "make_assets.py"
s = open(p, encoding="utf-8").read()

if "TRIMMED-TO-VERIFIED-ASSETS" in s:
    print("already trimmed")
    raise SystemExit(0)

# cut point: right after the in-house table is written
m = re.search(r'w\("tables/tab-inhouse\.tex".*?\n"""\)\n', s, re.S)
if not m:
    raise SystemExit("could not locate the in-house emitter; aborting rather than guessing")
cut = m.end()

head = s[:cut]
tail = '''
# ──────────────────────────────────────────────────────────────────────
# TRIMMED-TO-VERIFIED-ASSETS
#
# Everything below this point used to emit Table 5 (50-query benchmark),
# Table 6 (ablation), Figure 2 (latency) and Figure 3 (FPR) from
# `benchmark-web/backend/results/cikm/` and `.../v4/`.
#
# `provenance_audit.py` finds NO producing script for any artefact in those
# directories — an exhaustive search over 417 code files found no writer, and the
# one runner present in that tree is a standalone BM25 script over synthetic
# documents with no vector index, no adjudication and no LLM. The paper therefore
# no longer reports those results (see §7.4 of main.tex and PROVENANCE.md).
#
# They are removed rather than commented so the build cannot silently
# re-introduce untraceable numbers. To restore: write a committed script that
# reproduces the benchmark end to end, add it to the provenance map in
# provenance_audit.py, then re-emit the assets here.
# ──────────────────────────────────────────────────────────────────────

print("\\nAll LaTeX artefacts regenerated from the frozen, provenance-verified snapshot.")
print("Withheld (no producer): tab-cikm, tab-ablation, fig-fpr, fig-latency — see PROVENANCE.md")
'''

open(p, "w", encoding="utf-8", newline="\n").write(head + tail)
print(f"trimmed at char {cut} (kept {head.count(chr(10))} lines)")
