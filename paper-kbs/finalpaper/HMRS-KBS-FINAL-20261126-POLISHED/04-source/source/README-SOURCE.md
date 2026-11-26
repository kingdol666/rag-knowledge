# Source Package

This is the LaTeX source and supporting material for the HMRS submission to Knowledge-Based Systems. `main_20p.tex` is the double-column manuscript entry point, `main_20p_review.tex` is the double-spaced review copy, and `supplementary.tex` is the supplementary-material entry point.

## Build

With TeX Live (including `elsarticle`, `latexmk`, and BibTeX) or an Overleaf project using the included sources:

```text
latexmk -pdf main_20p.tex
latexmk -pdf main_20p_review.tex
latexmk -pdf supplementary.tex
latexmk -pdf external-baselines-qa.tex
```

The QA transcript source is regenerated from the shipped records with `python build_external_baselines_qa.py`; it embeds the verbatim prompt texts from `experiment_data/external_baselines_v3/protocol/` and shows the answers that were generated in Chinese (HMRS agent, native DeepRead) using the shipped English translations where available. Other non-ASCII fragments are transliterated for display, while the raw JSONL records keep the original text verbatim. The external-baseline configuration is archived in the experiment records; adapter source code is not included in this package. Regenerate Figure 5 with `python figure_scripts/build_fig5_tiered_case.py`; Figures 6–8 can be regenerated from their checked records with `build_fig_route_comparison.py`, `build_fig_content_comparison.py` and `build_fig_verifier_comparison.py`.

## Contents

- Both BibTeX databases, all referenced figure assets and the figure scripts.
- `experiment_data/baseline_quality_v2/` and `experiment_data/external_baselines_v3/`: the pinned answer-quality records (unified eight-arm answers, judgments, anonymisation maps, paired statistics, the earlier four-arm pass and the protocol texts).
- `experiment_data/tiered_case/`: the independently captured BQ07 trace used for Figure 5, not a scored result in E2 or E3.
- `experiment_data/external_baselines_v3/fig-hmrs-case-provenance.json`: the archived native E2 tool calls on BQ07, kept for the E2 discussion only.
- `experiment_data/routing_content_traces/`: the six trace CSVs behind Tables S12–S13 and Figures 6–7.
- `experiment_data/paired_diagnostics/`: the two verifier-replay tables behind Figure 8 (16 pools, 191 recorded scores).
- `experiment_data/README.md`: a file-by-file guide and the recomputation scripts.
- `inventory-build/`: the source of the companion evidence index. The supplementary PDF and the evidence index provide the crosswalk to `benchmark-suite/paper-results-kbs-20261125/` in the project repository.

The bundle includes compiled PDFs and excludes LaTeX auxiliary files, local agent session state, and internal design notes. Use `main_20p.tex` as the primary manuscript file. Rebuild the companion index from `inventory-build/` with `pandoc supplementary-inventory.md --standalone --lua-filter=supplementary-inventory-paths.lua --include-in-header=supplementary-inventory-header.tex --pdf-engine=pdflatex -o supplementary-inventory.pdf`.
