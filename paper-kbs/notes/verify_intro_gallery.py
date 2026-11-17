"""Verify that every image referenced by INTRO-RELATED-FIGURE-GALLERY.html exists."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KBS = ROOT / "paper-kbs" / "reference" / "kbs"
HTML = KBS / "INTRO-RELATED-FIGURE-GALLERY.html"
FIG = KBS / "figures"

h = HTML.read_text(encoding="utf-8")
pairs = re.findall(r'slug:"([^"]+)",\s*p:"(\d+)"', h)
missing = []
for slug, pno in pairs:
    for suffix in ("_intro_crop.png", "_intro.png"):
        f = FIG / f"{slug}__p{pno}{suffix}"
        if not f.exists():
            missing.append(str(f.relative_to(ROOT)))

groups = Counter(re.findall(r'\{g:"(g\d)"', h))
sections = set(re.findall(r'id="(g\d)"', h))
loc = json.loads((ROOT / "paper-kbs/notes/kbs_intro_related_figures.json").read_text(encoding="utf-8"))

checks = {
    "gallery HTML exists": HTML.exists(),
    "at least 12 curated cards": len(pairs) >= 12,
    "all card images exist": not missing,
    "every group has a target section": set(groups) <= sections,
    "every card has a group": len(pairs) == sum(groups.values()),
    "section locator exists": bool(loc),
    "all 29 PDFs were scanned": len(loc) == 29,
    "42 candidates were found": sum(len(e["intro_related_figures"]) for e in loc) == 42,
}
print(f"cards={len(pairs)} groups={dict(groups)} "
      f"candidates={sum(len(e['intro_related_figures']) for e in loc)} "
      f"intro_png={len(list(FIG.glob('*_intro*.png')))}")
for m in missing[:20]:
    print("  MISSING", m)
for k, v in checks.items():
    print(("  PASS  " if v else "  FAIL  ") + k)
print(f"[summary] {sum(checks.values())}/{len(checks)} checks passed")
if missing or not all(checks.values()):
    raise SystemExit(1)

(ROOT / "paper-kbs/notes/intro_gallery_verify.json").write_text(
    json.dumps({"cards": len(pairs), "groups": dict(groups),
                "candidates": sum(len(e["intro_related_figures"]) for e in loc),
                "checks": checks}, ensure_ascii=False, indent=1),
    encoding="utf-8")
