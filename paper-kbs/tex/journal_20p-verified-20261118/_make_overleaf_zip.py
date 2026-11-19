# -*- coding: utf-8
"""Package the journal_20p manuscript for Overleaf or Editorial Manager.

Build the main and supplementary PDFs before packaging. Editorial Manager
compiles a flat manuscript archive; upload the supplement and highlights
separately in the portal.
"""
import argparse
import hashlib
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
    "highlights.tex", "NOVEMBER-EVIDENCE-AUDIT.md", "experiment-source-map.md",
    "supplementary-inventory-source-map.md",
    "supplementary-inventory.pdf", "supplementary-inventory.md",
    "supplementary-inventory-header.tex", "supplementary-inventory-paths.lua",
    "README-OVERLEAF.txt", "SUBMISSION-FILL-IN.md", "_make_overleaf_zip.py",
    "figs/fig_tiered_algorithm.drawio", "figs/fig_tiered_drawio_20261116.drawio",
    "editable-figures/library-hmrs-single-column.drawio",
    "editable-figures/architecture_vector.drawio", "editable-figures/workflow_vector.drawio",
    "figure_scripts/build_fig_case_anatomy.py", "figure_scripts/build_fig_latest.py",
    "verify_archived_labels.py", "verify_november_sources.py", "verify_display_dates.py",
    "rescore_bq_answers_20261115.py", "README-archive-verification.md",
    "bq_supplement_20261115/bq_20261115_aggregate.csv",
    "bq_supplement_20261115/bq_20261115_per_case.csv",
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
    parser.add_argument("--manifest", type=Path,
                        help="write a SHA-256 manifest beside the package")
    parser.add_argument("--compiled-bbl", type=Path,
                        help="use the bibliography from a clean final build")
    parser.add_argument("--compiled-inventory", type=Path,
                        help="use the companion inventory PDF from a clean build")
    parser.add_argument("--word-builder", type=Path,
                        help="include the optional Word builder in the Overleaf archive")
    args = parser.parse_args()

    default_name = ("hmrs-kbs-editorial-manager-november-evidence.zip" if args.editorial_manager
                    else "hmrs-kbs-overleaf-november-evidence.zip")
    output = args.output or HERE.parent / default_name
    files = MANUSCRIPT if args.editorial_manager else MANUSCRIPT + OVERLEAF
    sources = {name: HERE / name for name in files + figure_paths(files)}
    if args.compiled_bbl:
        sources["main_20p.bbl"] = args.compiled_bbl
    if not args.editorial_manager:
        if args.compiled_inventory:
            sources["supplementary-inventory.pdf"] = args.compiled_inventory
        sources.update((path.relative_to(HERE).as_posix(), path)
                       for path in sorted((HERE / "experiment_data").glob("*"))
                       if path.is_file())
        if args.word_builder:
            sources["tools/build_word.py"] = args.word_builder
        elif (HERE / "tools/build_word.py").is_file():
            sources["tools/build_word.py"] = HERE / "tools/build_word.py"

    digests = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in sources.items():
            entry = Path(name).name if args.editorial_manager else name
            data = path.read_bytes()
            if args.editorial_manager and name == "main_20p.tex":
                data = data.replace(rb"\graphicspath{{figs/}}", b"")
            zf.writestr(entry, data)
            digests.append((entry, hashlib.sha256(data).hexdigest()))
        manifest = "".join(f"{digest}  {entry}\n" for entry, digest in sorted(digests))
        # Keep the flat Editorial Manager upload limited to manuscript inputs.
        if not args.editorial_manager:
            zf.writestr("SHA256SUMS", manifest)
        print(f"wrote {output} ({len(zf.namelist())} files)")
    if args.manifest:
        args.manifest.write_bytes(manifest.encode("ascii"))


if __name__ == "__main__":
    main()
