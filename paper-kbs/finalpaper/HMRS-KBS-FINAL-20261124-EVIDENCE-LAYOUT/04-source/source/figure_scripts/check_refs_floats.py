"""Reference/float audit for the main manuscript tree."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
files = ["main_20p.tex", "n1_intro.tex", "n2_related.tex", "n3_overview.tex",
         "n4_acquisition.tex", "n5_organization.tex", "n6_retrieval.tex",
         "n7_implementation.tex", "n8a_eval.tex", "n8b_eval.tex",
         "n8c_eval.tex", "n8d_eval.tex", "n9_discussion.tex",
         "n10_threats.tex", "n11_conclusion.tex", "n_back.tex"]
labels, refs, floats = set(), set(), set()
for f in files:
    t = (HERE / f).read_text(encoding="utf-8")
    labels |= set(re.findall(r"\\label\{([^}]+)\}", t))
    refs |= set(re.findall(r"\\ref\{([^}]+)\}", t))
    floats |= set(re.findall(r"\\label\{((?:fig|tab):[^}]+)\}", t))
print("undefined refs:", sorted(refs - labels))
print("uncited floats:", sorted(x for x in floats if x not in refs))
supp = (HERE / "supplementary.tex").read_text(encoding="utf-8")
for inc in ["supplementary-arm-tables.tex", "supplementary-baseline-quality.tex",
            "supplementary-external-baselines.tex"]:
    supp += (HERE / inc).read_text(encoding="utf-8")
slabels = set(re.findall(r"\\label\{([^}]+)\}", supp))
srefs = set(re.findall(r"\\ref\{([^}]+)\}", supp))
print("supp undefined refs:", sorted(srefs - slabels - labels))