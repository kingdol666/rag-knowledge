# Source Package

This is the LaTeX source and supporting material for the HMRS manuscript submitted to Knowledge-Based Systems. `main_20p.tex` is the double-column manuscript entry point, `main_20p_review.tex` is the double-spaced review copy, and `supplementary.tex` is the supplementary-material entry point.

## Build

With TeX Live (including `elsarticle`, `latexmk`, and BibTeX) or an Overleaf project using the included sources:

```text
latexmk -pdf main_20p.tex
latexmk -pdf main_20p_review.tex
latexmk -pdf supplementary.tex
latexmk -pdf external-baselines-qa.tex
```

The QA transcript source is regenerated from the shipped records with `python build_external_baselines_qa.py`; it embeds the verbatim prompt texts from `experiment_data/external_baselines_v3/protocol/`.

## Contents

- Both BibTeX databases, all referenced figure assets and the figure scripts.
- `experiment_data/baseline_quality_v2/` and `experiment_data/external_baselines_v3/`: the pinned answer-quality records (unified eight-arm answers, judgments, anonymisation maps, paired statistics, the earlier four-arm pass and the protocol texts).
- `experiment_data/routing_content_traces/`: the six trace CSVs behind Tables S12–S13 and Figures 6–7.
- `experiment_data/README.md`: a file-by-file guide and the recomputation scripts.
- `inventory-build/`: the Markdown source of the companion evidence inventory (Tables S1–S8).

The bundle excludes compiled PDFs, LaTeX auxiliary files, local agent session state, and the internal design notes and working reports (they remain in the repository under `review/`). Use `main_20p.tex` as the primary manuscript file.
