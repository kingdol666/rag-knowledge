"""Generate an Elsevier 'final,5p,times,twocolumn' journal-style build from the
single-column preprint sources, without touching the submission sources.

Transformations applied to the copies in paper-kbs/tex/journal/:
  * documentclass  -> [final,5p,times,twocolumn]  (+ stfloats)
  * \\begin{table}  -> table*  when the table is wider than one column
  * \\begin{figure} -> figure* when the figure is included at \\textwidth
  * float fractions retuned for two-column output
Read-only with respect to the source tree.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

TEX = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex")
DST = TEX / "journal"

COL_WIDTH_CM = 8.4  # ~elsarticle 5p single column

ENV_RE = re.compile(r"\\begin\{(table|figure)\}(\[[^\]]*\])?(.*?)\\end\{\1\}", re.S)
PCOL_RE = re.compile(r"p\{([0-9.]+)\\columnwidth\}|p\{([0-9.]+)cm\}")


def env_width_cm(body: str) -> float:
    total = 0.0
    for m in PCOL_RE.finditer(body):
        if m.group(1):
            total += float(m.group(1)) * COL_WIDTH_CM
        else:
            total += float(m.group(2))
    return total


def convert(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    def repl(m: re.Match[str]) -> str:
        kind, opt, body = m.group(1), m.group(2) or "", m.group(3)
        if kind == "table":
            if env_width_cm(body) > COL_WIDTH_CM or "\\textwidth" in body:
                notes.append(f"table* ({env_width_cm(body):.1f}cm)")
                return f"\\begin{{table*}}[t]{body}\\end{{table*}}"
            return m.group(0)
        # figure
        if "width=\\textwidth" in body:
            notes.append("figure* (full width)")
            return f"\\begin{{figure*}}[t]{body}\\end{{figure*}}"
        return m.group(0)

    return ENV_RE.sub(repl, text), notes


CLASS_OLD = r"\documentclass[preprint,12pt]{elsarticle}"
CLASS_NEW = (
    "% journal-style camera-ready preview (generated from the submission sources)\n"
    "\\documentclass[final,5p,times,twocolumn]{elsarticle}\n"
    "\\usepackage{stfloats}"
)

FLOAT_BLOCK_OLD = re.compile(
    r"\\renewcommand\{\\topfraction\}\{0\.92\}.*?\\setcounter\{dbltopnumber\}\{3\}",
    re.S,
)
FLOAT_BLOCK_NEW = (
    "\\renewcommand{\\topfraction}{0.90}\n"
    "\\renewcommand{\\bottomfraction}{0.85}\n"
    "\\renewcommand{\\textfraction}{0.08}\n"
    "\\renewcommand{\\floatpagefraction}{0.75}\n"
    "\\renewcommand{\\dbltopfraction}{0.90}\n"
    "\\renewcommand{\\dblfloatpagefraction}{0.75}\n"
    "\\setcounter{topnumber}{3}\n"
    "\\setcounter{bottomnumber}{2}\n"
    "\\setcounter{totalnumber}{4}\n"
    "\\setcounter{dbltopnumber}{3}"
)


def main() -> int:
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)

    total_notes: dict[str, list[str]] = {}
    for src in sorted(TEX.glob("*.tex")):
        text = src.read_text(encoding="utf-8")
        if src.name == "main2.tex":
            text = text.replace(CLASS_OLD, CLASS_NEW)
            text = FLOAT_BLOCK_OLD.sub(lambda _m: FLOAT_BLOCK_NEW, text)
            text = text.replace(
                "\\bibliographystyle{unsrtnat}", "\\bibliographystyle{elsarticle-num}"
            )
            text = text.replace(
                "\\input{n", "\\input{n"
            )  # unchanged; kept for clarity
        new_text, notes = convert(text)
        if notes:
            total_notes[src.name] = notes
        (DST / src.name).write_text(new_text, encoding="utf-8")

    for extra in ("refs.bib", "refs_new_verified.bib"):
        s = TEX / extra
        if s.exists():
            shutil.copy2(s, DST / extra)
    for figs in ("figs",):
        s = TEX / figs
        if s.exists():
            shutil.copytree(s, DST / figs, dirs_exist_ok=True)

    print(f"generated {DST}")
    for name, notes in total_notes.items():
        print(f"  {name}: {len(notes)} float(s) widened -> " + ", ".join(sorted(set(notes))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
