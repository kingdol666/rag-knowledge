"""What per-query evidence exists in the frozen snapshot? Drives TODO-15 (coverage)."""
import json
import os

SNAP = "docs/paper/cikm/data-snapshot"

MARKERS = ["n_returned", "returned", "num_returned", "empty", "n_hits",
           "k_returned", "results", "hits", "n_docs_returned", "returned_count"]

for fn in sorted(os.listdir(SNAP)):
    if not fn.endswith(".json") or fn == "MANIFEST.json":
        continue
    p = os.path.join(SNAP, fn)
    d = json.load(open(p, encoding="utf-8-sig"))
    blob = json.dumps(d)
    found = [m for m in MARKERS if ('"%s"' % m) in blob]
    print(f"\n=== {fn} ===")
    print(f"  top-level keys : {list(d)[:12]}")
    print(f"  per-query markers present: {found or 'NONE'}")

    rows = d.get("rows") or d.get("per_query") or d.get("details")
    if isinstance(rows, list) and rows:
        print(f"  rows           : {len(rows)}")
        print(f"  row keys       : {sorted(rows[0]) if isinstance(rows[0], dict) else type(rows[0])}")
    elif isinstance(rows, dict):
        print(f"  rows (dict)    : {list(rows)[:6]}")

    # how deep does the structure go before it stops being aggregates?
    def depth(o, d=0):
        if isinstance(o, dict) and d < 3:
            return 1 + max([depth(v, d + 1) for v in o.values()] or [0])
        if isinstance(o, list) and o and d < 3:
            return 1 + depth(o[0], d + 1)
        return 0
    print(f"  nesting depth  : {depth(d)}")
