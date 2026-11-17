"""Verify every image referenced by FIGURE-GALLERY.html exists on disk."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KBS = ROOT / "paper-kbs" / "reference" / "kbs"
HTML = KBS / "FIGURE-GALLERY.html"
FIG = KBS / "figures"

h = HTML.read_text(encoding="utf-8")
pairs = re.findall(r'slug:"([^"]+)", p:"(\d+)"', h)
missing = []
for slug, pno in pairs:
    for suffix in ("_crop.png", ".png"):
        f = FIG / f"{slug}__p{pno}{suffix}"
        if not f.exists():
            missing.append(str(f.relative_to(ROOT)))

groups = Counter(re.findall(r'\{g:"(g\d)"', h))
sections = re.findall(r'id="(g\d)"', h)
checks = {
    "gallery HTML exists": HTML.exists(),
    "at least 20 figure cards": len(pairs) >= 20,
    "all card images exist": not missing,
    "every group has a target section": set(groups) <= set(sections),
    "every card has a group": len(pairs) == sum(groups.values()),
    "figure index exists": (ROOT / "paper-kbs/notes/kbs_all_figure_index.json").exists(),
    "selected-render report exists": (ROOT / "paper-kbs/notes/kbs_selected_figures.json").exists(),
}
print(f"cards={len(pairs)} groups={dict(groups)} png_total={len(list(FIG.glob('*.png')))}")
for m in missing[:20]:
    print("  MISSING", m)
for k, v in checks.items():
    print(("  PASS  " if v else "  FAIL  ") + k)
print(f"[summary] {sum(checks.values())}/{len(checks)} checks passed")
if missing or not all(checks.values()):
    raise SystemExit(1)

(ROOT / "paper-kbs/notes/figure_gallery_verify.json").write_text(
    json.dumps({"cards": len(pairs), "groups": dict(groups),
                "png_total": len(list(FIG.glob("*.png"))),
                "checks": checks}, ensure_ascii=False, indent=1),
    encoding="utf-8")
