"""Assemble the KBS/Elsevier submission package for the 20-page build with NO
subfolders (Editorial Manager cannot process LaTeX submissions that contain
subdirectories).

Source of truth:  paper-kbs/tex/journal_20p/
Output:           paper-kbs/submission-20p/

The package contains
  * manuscript sources at one folder level (main_20p.tex + n*.tex + tab_*.tex)
  * refs.bib + refs_new_verified.bib + the generated qdcvr_kbs.bbl
    (.tex/.bbl/.bst/.sty/.cls/.bib/.nls/.ilg/.nlo are all 'Manuscript' items)
  * every figure the manuscript includes, as a separate vector PDF
  * highlights.docx + highlights.tex (Elsevier: 3-5 bullets, <=85 chars each)
  * README-submission.md with the file mapping and the author action items

Run after the manuscript build so that qdcvr_kbs.bbl is current:

    uv run python paper-kbs/submission-20p/make_submission_package.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
SRC = PKG.parent / "tex" / "journal_20p"

MAIN = "main_20p.tex"
SOURCE_TEX = [
    MAIN,
    "n1_intro.tex",
    "n2_related.tex",
    "n3_overview.tex",
    "n4_acquisition.tex",
    "n5_organization.tex",
    "n6_retrieval.tex",
    "n7_implementation.tex",
    "n8a_eval.tex",
    "n8b_eval.tex",
    "n8c_eval.tex",
    "n9_discussion.tex",
    "n10_threats.tex",
    "n11_conclusion.tex",
    "n_back.tex",
    "highlights.tex",
]
SOURCE_BIB = ["refs.bib", "refs_new_verified.bib"]
SOURCE_BBL = ["main_20p.bbl"]


def highlights() -> list[str]:
    text = (SRC / "highlights.tex").read_text(encoding="utf-8")
    body = re.search(r"\\begin\{highlights\}(.*?)\\end\{highlights\}", text, re.S)
    if not body:
        raise SystemExit("highlights.tex has no highlights environment")
    return [re.sub(r"\s+", " ", m.group(1)).strip()
            for m in re.finditer(r"\\item\s+(.*?)(?=\\item|$)", body.group(1), re.S)]


def write_docx(items: list[str], path: Path) -> None:
    from docx import Document  # type: ignore

    doc = Document()
    doc.add_heading("Highlights", level=1)
    for item in items:
        doc.add_paragraph(item, style="List Bullet")
    doc.save(path)


def figures_used(main_text: str, source_texts: list[str]) -> list[str]:
    """Only the graphics the manuscript actually includes, in citation order."""
    seen: list[str] = []
    for text in source_texts:
        for m in re.finditer(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", text):
            name = m.group(1).strip()
            if name not in seen:
                seen.append(name)
    return seen


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"source directory not found: {SRC}")

    items = highlights()
    longest = max(len(s) for s in items)
    print(f"highlights: {len(items)} item(s), longest {longest} chars")
    for i, s in enumerate(items, 1):
        print(f"  {i}. ({len(s)}) {s}")
    if not (3 <= len(items) <= 5) or longest > 85:
        print("FAIL: Elsevier requires 3-5 bullets of at most 85 characters",
              file=sys.stderr)
        return 1

    PKG.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    for group in (SOURCE_TEX, SOURCE_BIB, SOURCE_BBL):
        for name in group:
            src = SRC / name
            if not src.exists():
                missing.append(name)
                continue
            shutil.copy2(src, PKG / name)
            copied.append(name)

    texts = [(PKG / n).read_text(encoding="utf-8") for n in SOURCE_TEX
             if (PKG / n).exists()]
    names = figures_used(texts[0], texts)
    figs: list[Path] = []
    for name in names:
        for cand in (SRC / "figs" / f"{name}.pdf", SRC / f"{name}.pdf"):
            if cand.exists():
                shutil.copy2(cand, PKG / cand.name)
                figs.append(cand)
                break
        else:
            missing.append(f"{name}.pdf")

    # the submission copy must not rely on a graphics subfolder
    main_tex = PKG / MAIN
    text = main_tex.read_text(encoding="utf-8")
    stripped = re.sub(r"\\graphicspath\{\{[^}]*\}\}\n?", "", text)
    if stripped != text:
        main_tex.write_text(stripped, encoding="utf-8")
        print(f"  {MAIN}: removed \\graphicspath (figures sit at the same level)")

    write_docx(items, PKG / "highlights.docx")

    (PKG / "README-submission.md").write_text(
        "# KBS submission package\n\n"
        "Generated from the canonical source `paper-kbs/tex/journal_20p/`. This is a flattened LaTeX source package for Editorial Manager; the local 20-page PDF is a review/layout preview, not evidence that the journal's preferred double-spaced manuscript length is met.\n\n"
        f"- manuscript source: `{MAIN}` plus {len([n for n in copied if n.endswith('.tex')])-1} included TeX files\n"
        f"- bibliography: {', '.join(f'`{n}`' for n in SOURCE_BIB)} plus generated `{SOURCE_BBL[0]}`\n"
        f"- figures used by the manuscript: {', '.join(f'`{f.name}`' for f in figs)}\n"
        "- highlights: `highlights.docx` and `highlights.tex` (verify identical wording before upload)\n"
        "- supplementary material: upload `paper-kbs/supplementary/supplementary-material.pdf` as a separate supplementary item (Part D of that document carries Tables S1-S5, the five appendix tables the manuscript cites; they moved out of the manuscript on 2026-10-16)\n"
        "- Declaration of Interests: complete Elsevier's declarations tool and upload its generated Word document separately\n"
        "- evaluation freeze: the corrected annotations, the pre-correction question set and the grader are pinned in `paper-kbs/tex/journal_20p/.frozen-experiment-sha256.txt` (verify with `sha256sum -c` from the repository root)\n"
        "- page budget: measurements for both layouts (20-page camera-ready preview; 68-page double-spaced review format) and the compression plan are in `paper-kbs/notes/page-budget-2026-10-16.md`\n\n"
        "## Author confirmation required before submission\n\n"
        "1. Replace author names/order, corresponding-author email, affiliation and city/country in `main_20p.tex`.\n"
        "2. Replace Author 1/Author 2 in CRediT with accurate names and roles.\n"
        "3. Confirm the no-funding statement and acknowledgements.\n"
        "4. Confirm the generative-AI declaration: it now names the two agent CLIs used on this project (\"Anthropic Claude Code and ZCode command-line coding agents\"); add versions only if the editors ask.\n"
        "5. Supply the separate Declaration of Interests Word file from Elsevier's tool.\n"
        "6. Confirm the CIKM demo author metadata and publication details when available.\n"
        "7. Upload the supplementary PDF separately and verify it reflects the current manuscript.\n"
        "8. Choose the manuscript layout: the two-column preview (`main_20p.tex`, 20 pages) or the double-spaced review source (`main_20p_review.tex`, 68 pages); KBS permits double-column LaTeX but describes 20 double-spaced pages as preferred (see the page-budget note).\n",
        encoding="utf-8",
    )
    print(f"\npackage: {len(copied)} sources/bib/bbl + {len(figs)} figures")
    for f in figs:
        print(f"  fig: {f.name}")
    if missing:
        print("\nMISSING (fix before upload): " + ", ".join(missing), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
