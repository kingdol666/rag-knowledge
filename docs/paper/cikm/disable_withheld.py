"""Disable the three generator blocks that consume the withheld CIKM artefact.

Comments out the tab-cikm / tab-ablation / fig-fpr / fig-latency emitters so the
build no longer produces artefacts sourced from an untraceable benchmark.
Idempotent.
"""
import re

p = "make_assets.py"
s = open(p, encoding="utf-8").read()

MARKERS = [
    ("# ══════════════════════════════════════════════════════════════════════\n"
     "# TABLE 5 — CIKM 50-query benchmark", "TABLE 5"),
    ("# ══════════════════════════════════════════════════════════════════════\n"
     "# TABLE 6 — Ablation", "TABLE 6"),
    ("# ══════════════════════════════════════════════════════════════════════\n"
     "# FIGURE 2 — latency vs quality trade-off", "FIGURE 2"),
    ("# ══════════════════════════════════════════════════════════════════════\n"
     "# FIGURE 3 — FPR comparison", "FIGURE 3"),
]

if "WITHHELD-BLOCK-START" in s:
    print("already disabled")
    raise SystemExit(0)

out, i, done = [], 0, []
while True:
    best = None
    for m, name in MARKERS:
        j = s.find(m, i)
        if j >= 0 and (best is None or j < best[0]):
            best = (j, m, name)
    if best is None:
        out.append(s[i:])
        break
    j, m, name = best
    out.append(s[i:j])
    # the block runs to the next top-level section comment
    nxt = s.find("# ══════════════════════════════════════════════════════════════════════", j + len(m))
    end = nxt if nxt > 0 else len(s)
    block = s[j:end]
    commented = "\n".join(("# " + ln if ln.strip() else ln) for ln in block.split("\n"))
    out.append("\n# ---- WITHHELD-BLOCK-START (no producer; see PROVENANCE.md) ----\n")
    out.append(commented)
    out.append("\n# ---- WITHHELD-BLOCK-END ----\n")
    done.append(name)
    i = end

s2 = "".join(out)
open(p, "w", encoding="utf-8", newline="\n").write(s2)
print("disabled blocks:", ", ".join(done) if done else "none found")
