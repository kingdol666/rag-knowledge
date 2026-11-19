# -*- coding: utf-8 -*-
"""Package the 17-page (pre-recast) HMRS manuscript: source + PDFs + docs, then zip."""
import shutil
from pathlib import Path

SRC = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p")
DST = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\release-17p-20261119")

TEX = ["main_20p.tex", "main_20p_review.tex", "highlights.tex",
       "n1_intro.tex", "n2_related.tex", "n3_overview.tex", "n4_acquisition.tex",
       "n5_organization.tex", "n6_retrieval.tex", "n7_implementation.tex",
       "n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex", "n9_discussion.tex",
       "n10_threats.tex", "n11_conclusion.tex", "n_back.tex",
       "supplementary.tex", "supplementary-arm-tables.tex",
       "refs.bib", "refs_new_verified.bib"]

FIGS = ["fig1_architecture_native", "fig_exp_s3", "fig_exp_s5",
        "fig_library_analogy_vector", "fig_opt_answer", "fig_opt_case",
        "fig_opt_content", "fig_opt_route", "fig_opt_s_answer",
        "fig_opt_s_margin", "fig_opt_verifier", "fig_service_architecture_vector",
        "fig_tiered_drawio_20261116", "fig_workflow_vector"]

PDFS = ["main_20p.pdf", "main_20p_review.pdf", "supplementary.pdf"]

DOCS = ["README-OVERLEAF.txt", "SUBMISSION-FILL-IN.md", "cover_letter.txt",
        "suggested_reviewers.txt", "highlights.docx",
        "图文修订说明-20261113.md", "内容与证据复核-20261114.md",
        "排版与逻辑复核-20261113.md"]

copied, missing = [], []
def cp(rel, sub):
    s = SRC / rel
    if not s.exists():
        missing.append(rel); return
    d = DST / sub / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    copied.append(str(d.relative_to(DST)))

for f in TEX: cp(f, "source")
for f in FIGS: cp(f"figs/{f}.pdf", "source/figs")
for f in PDFS: cp(f, "pdf")
for f in DOCS: cp(f, "docs")

for pat in ("*.csv", "*.json", "SHA256SUMS"):
    for s in (SRC / "experiment_data").glob(pat):
        cp(f"experiment_data/{s.name}", "source/experiment_data")
if (SRC / "figure_scripts").is_dir():
    for s in (SRC / "figure_scripts").glob("*.py"):
        cp(f"figure_scripts/{s.name}", "source/figure_scripts")

print(f"copied={len(copied)} missing={missing}")

zip_path = shutil.make_archive(str(DST), "zip", root_dir=DST.parent, base_dir=DST.name)
print("zip:", zip_path)
import zipfile
with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
    print("zip entries:", len(names), "| bad:", z.testzip())
