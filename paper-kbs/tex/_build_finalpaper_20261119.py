# -*- coding: utf-8 -*-
"""Build paper-kbs/finalpaper/: Overleaf-importable zip + compiled PDFs + supplementary sources."""
import shutil, zipfile
from pathlib import Path

SRC = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p")
VER = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p-verified-20261118")
DST = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\finalpaper")
OVW = DST / "overleaf-source"

TEX = ["main_20p.tex", "highlights.tex",
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
        "fig_tiered_singlecol_20261119", "fig_workflow_vector"]
PDFS = ["main_20p.pdf", "main_20p_review.pdf", "supplementary.pdf", "supplementary-inventory.pdf"]
SUPP_SRC = ["supplementary.tex", "supplementary-arm-tables.tex"]
# inventory 构建件（源码级，来自 verified 归档）
INV_SRC = ["supplementary-inventory-header.tex", "supplementary-inventory-paths.lua",
           "supplementary-inventory-source-map.md"]

copied, missing = [], []
def cp(src, rel):
    if not src.exists():
        missing.append(rel); return
    d = DST / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, d)
    copied.append(rel)

for f in TEX: cp(SRC / f, f"overleaf-source/{f}")
for f in FIGS: cp(SRC / "figs" / f"{f}.pdf", f"overleaf-source/figs/{f}.pdf")
for f in PDFS: cp(SRC / f, f"compiled/{f}")
for f in SUPP_SRC: cp(SRC / f, f"supplementary-source/{f}")
for f in INV_SRC: cp(VER / f, f"supplementary-source/inventory-build/{f}")
cp(VER / "supplementary-inventory.pdf", "compiled/supplementary-inventory.pdf")

print(f"copied={len(copied)} missing={missing}")

# Overleaf-importable zip（扁平结构，上传即编译 main_20p.tex）
zip_path = DST / "HMRS-KBS-overleaf-20261119.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OVW.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(OVW))
with zipfile.ZipFile(zip_path) as z:
    n = z.namelist()
    print("overleaf zip entries:", len(n),
          "| has main tex:", "main_20p.tex" in n,
          "| has figs:", any(x.startswith("figs/") for x in n),
          "| bad:", z.testzip())
print("zip:", zip_path)
