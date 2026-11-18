# -*- coding: utf-8
"""Package the journal_20p manuscript for Overleaf or Editorial Manager.

Build the main and supplementary PDFs before packaging. Editorial Manager
compiles a flat manuscript archive; upload the supplement and highlights
separately in the portal.
"""
import argparse
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

MANUSCRIPT = [
    "main_20p.tex",
    "n1_intro.tex", "n2_related.tex", "n3_overview.tex", "n4_acquisition.tex",
    "n5_organization.tex", "n6_retrieval.tex", "n7_implementation.tex",
    "n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex", "n9_discussion.tex",
    "n10_threats.tex", "n11_conclusion.tex", "n_back.tex",
    "main_20p.bbl", "refs.bib", "refs_new_verified.bib",
]

OVERLEAF = [
    "main_20p_review.tex",
    "supplementary.tex", "supplementary-arm-tables.tex",
    "highlights.tex", "highlights.docx",
    "supplementary-inventory.pdf",
    "revision-20261112.sha256",
    "README-OVERLEAF.txt",
    ".frozen-experiment-sha256.txt",
    "figure_scripts/build_fig_case_anatomy.py",
]


def figure_paths(files: list[str]) -> list[str]:
    source = "\n".join((HERE / name).read_text(encoding="utf-8") for name in files
                       if name.endswith(".tex"))
    figures = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", source)
    return [f"figs/{name}.pdf" for name in sorted(set(figures))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--editorial-manager", action="store_true")
    args = parser.parse_args()

    default_name = ("hmrs-kbs-editorial-manager-20261118.zip" if args.editorial_manager
                    else "overleaf-journal20p-20261118.zip")
    output = args.output or HERE.parent / default_name
    files = MANUSCRIPT if args.editorial_manager else MANUSCRIPT + OVERLEAF
    sources = files + figure_paths(files)
    if not args.editorial_manager:
        sources += [
            path.relative_to(HERE).as_posix()
            for path in sorted((HERE / "experiment_data").glob("*"))
            if path.is_file()
        ]

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sources:
            path = HERE / name
            if args.editorial_manager and name == "main_20p.tex":
                text = path.read_text(encoding="utf-8")
                zf.writestr(name, text.replace(r"\graphicspath{{figs/}}", ""))
            else:
                zf.write(path, path.name if args.editorial_manager else name)
        print(f"wrote {output} ({len(zf.namelist())} files)")


if __name__ == "__main__":
    main()
