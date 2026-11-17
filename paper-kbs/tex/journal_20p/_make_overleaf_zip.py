# -*- coding: utf-8
"""Build a clean, self-contained Overleaf package for the journal_20p manuscript.

Contents: main/supplementary tex sources, bibliography, the referenced
vector figure PDFs, the companion inventory PDF, packaged experiment data and
a README. Excludes logs, renders, backups, audit scripts and unused figures.
"""
import os
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "overleaf-journal20p-20261117.zip"

TEX = [
    "main_20p.tex",
    "n1_intro.tex", "n2_related.tex", "n3_overview.tex", "n4_acquisition.tex",
    "n5_organization.tex", "n6_retrieval.tex", "n7_implementation.tex",
    "n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex", "n9_discussion.tex",
    "n10_threats.tex", "n11_conclusion.tex", "n_back.tex",
    "supplementary.tex", "supplementary-arm-tables.tex",
    "highlights.tex", "refs.bib", "refs_new_verified.bib",
    "supplementary-inventory.pdf",
    "revision-20261112.sha256",
    "README-OVERLEAF.txt",
]

SOURCES = [
    "figure_scripts/build_fig_case_anatomy.py",
]

FIGS = [
    "fig1_architecture_native", "fig_library_analogy_vector",
    "fig_service_architecture_vector", "fig_workflow_vector",
    "fig_tiered_drawio_20261116", "fig_opt_route", "fig_opt_content",
    "fig_opt_case", "fig_opt_answer", "fig_opt_verifier", "fig_opt_s_answer", "fig_exp_s3",
    "fig_opt_s_margin", "fig_exp_s5",
]


def add_file(zf: zipfile.ZipFile, rel: str) -> None:
    src = HERE / rel
    if not src.is_file():
        raise FileNotFoundError(rel)
    zf.write(src, rel)


def main() -> None:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in TEX:
            add_file(zf, rel)
        for rel in SOURCES:
            add_file(zf, rel)
        for name in FIGS:
            add_file(zf, f"figs/{name}.pdf")
        data_dir = HERE / "experiment_data"
        for p in sorted(data_dir.rglob("*")):
            if p.is_file():
                zf.write(p, f"experiment_data/{p.name}")
    size = OUT.stat().st_size
    entries = len(zipfile.ZipFile(OUT).namelist())
    print(f"wrote {OUT} ({size/1024:.0f} KB, {entries} files)")


if __name__ == "__main__":
    main()
