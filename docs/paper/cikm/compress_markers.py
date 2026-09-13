"""Replace verbose \\needblock{...} bodies in main.tex with compact TODO pointers.

The long-form rationale lives in REVIEW-TODO.md. The PDF keeps only a short red
pointer so it does not inflate the page count (12 long markers ≈ 2 pages).

Run:  python compress_markers.py
"""
import re

MAIN = "main.tex"

# order matters: map each verbose block to its TODO id by a distinctive substring
MAPPING = [
    ("Reproduce this motivating case",              "TODO-1",
     "Motivating example is unreproducible --- replace with a case mined from the frozen retrieval artefact (see REVIEW-TODO.md)."),
    ("The 30-day threshold and the decay rules",    "TODO-3",
     "Decay threshold unvalidated --- supply precision/recall, a sensitivity sweep and the observation window (REVIEW-TODO.md)."),
    ("This subsection currently makes an architectural claim", "TODO-4",
     "Multi-path fusion is unevaluated --- supply a leave-one-out ablation and a single-path baseline (REVIEW-TODO.md)."),
    ("The evaluation currently reports a single run", "TODO-7",
     "One run per configuration --- supply $\\geq 5$ runs with SD, the named test, and per-metric CIs (REVIEW-TODO.md)."),
    ("The ablation's absolute P@5",                 "TODO-9",
     "Ablation and main results are on different scales (0.72--0.88 vs 0.12--0.20) --- re-run on the same query set or state the differing protocol (REVIEW-TODO.md)."),
    ("The numbers in Table~\\ref{tab:experience} come from the archived run", "TODO-5",
     "This module produced 10 judged entries, then 0 on re-execution --- make the benchmark reset state and report $\\geq 3$ runs (REVIEW-TODO.md)."),
    ("The experience module is currently evaluated", "TODO-6",
     "No baseline --- supply a no-synthesis baseline and an LLM-summary baseline scored by the same judge (REVIEW-TODO.md)."),
    ("The artefact-producing directories",          "TODO-10",
     "Benchmark artefacts are overwritten in place --- add immutable per-run dirs and an anonymous artefact link (REVIEW-TODO.md)."),
    ("The blind-spot rule is asserted",             "TODO-2",
     "Blind-spot rule unevaluated --- report both over- and under-suppression rates (REVIEW-TODO.md)."),
    ("Report the BGE-M3",                           "TODO-8",
     "Record the BGE-M3 revision and ChromaDB HNSW parameters (REVIEW-TODO.md)."),
]


def extract_cmd(src, cmd, start=0):
    """Return (start, end, body) of the next \\cmd{...} with balanced braces."""
    key = "\\" + cmd + "{"
    j = src.find(key, start)
    if j < 0:
        return None
    k, depth = j + len(key), 1
    while k < len(src) and depth:
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
        k += 1
    return j, k, src[j + len(key):k - 1]


src = open(MAIN, encoding="utf-8").read()
replaced = 0

for needle, todo, short in MAPPING:
    # find the marker (either kind) whose body contains the needle
    found = None
    for cmd in ("needblock", "need"):
        pos = 0
        while True:
            got = extract_cmd(src, cmd, pos)
            if got is None:
                break
            a, b, body = got
            if needle in body:
                found = (a, b, cmd, body)
                break
            pos = b
        if found:
            break
    if not found:
        print(f"  !! not found: {needle[:48]}")
        continue
    a, b, cmd, body = found
    new = "\\need{%s %s}" % (todo, short)
    src = src[:a] + new + src[b:]
    replaced += 1
    print(f"  compressed {todo:<8} ({cmd}, {len(body)} -> {len(new)} chars)")

open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print(f"\n{replaced} markers compressed. Long-form rationale lives in REVIEW-TODO.md.")
