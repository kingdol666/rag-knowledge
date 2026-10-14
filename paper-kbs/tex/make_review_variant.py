"""Generate the double-spaced 'review-copy' variant of the KBS submission.

The KBS Guide for Authors states the length cap in *double line spaced* manuscript
pages ("preferably no more than 20 double line spaced manuscript pages, including
tables and figures"). elsarticle's `preprint` option is single spaced and `review`
is 1.5 spaced, so this script emits an explicitly double-spaced copy under
paper-kbs/tex/review/ purely to measure that cap. Sources are never modified.

    python make_review_variant.py && cd review && pdflatex main2 && bibtex main2 ...
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

TEX = Path(__file__).resolve().parent
DST = TEX / "review"

CLASS_OLD = r"\documentclass[preprint,12pt]{elsarticle}"
CLASS_NEW = (
    "% review copy: double line spacing, to measure the journal's page cap\n"
    "\\documentclass[preprint,12pt]{elsarticle}\n"
    "\\usepackage{setspace}\n"
    "\\doublespacing"
)


def main() -> int:
    if not (TEX / "main2.tex").exists():
        print("main2.tex not found", file=sys.stderr)
        return 1
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)

    for src in sorted(TEX.glob("*.tex")):
        text = src.read_text(encoding="utf-8")
        if src.name == "main2.tex":
            if CLASS_OLD not in text:
                print("documentclass line not found in main2.tex", file=sys.stderr)
                return 1
            text = text.replace(CLASS_OLD, CLASS_NEW)
            # the dense float fractions are tuned for the compact build; a review
            # copy should keep floats where an editor expects them
            text = re.sub(
                r"\\renewcommand\{\\topfraction\}\{0\.92\}.*?\\setcounter\{dbltopnumber\}\{3\}",
                # a lambda keeps re.sub from interpreting \t, \b, \f, \r as escapes
                lambda _m: (
                    "\\renewcommand{\\topfraction}{0.85}\n"
                    "\\renewcommand{\\bottomfraction}{0.7}\n"
                    "\\renewcommand{\\textfraction}{0.12}\n"
                    "\\renewcommand{\\floatpagefraction}{0.8}"
                ),
                text,
                flags=re.S,
            )
        (DST / src.name).write_text(text, encoding="utf-8")

    for extra in ("refs.bib", "refs_new_verified.bib"):
        if (TEX / extra).exists():
            shutil.copy2(TEX / extra, DST / extra)
    if (TEX / "figs").exists():
        shutil.copytree(TEX / "figs", DST / "figs", dirs_exist_ok=True)

    print(f"generated {DST} (double-spaced review copy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
