#!/usr/bin/env python3
"""Print a pandoc-friendly flattened LaTeX source for the Word conversions.

Read-only: the script only reads the manuscript sources, the compiled .aux
label map and the .bbl bibliography, then prints the patched single-file
LaTeX to stdout. The caller redirects stdout to a literal path, e.g.
    python -X utf8 -I _make_docx_src.py main > _docx_build/main_docx.tex
Modes: main | supp
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

MAIN_FILES = [
    "n1_intro.tex", "n2_related.tex", "n3_overview.tex", "n4_acquisition.tex",
    "n5_organization.tex", "n6_retrieval.tex", "n7_implementation.tex",
    "n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex", "n9_discussion.tex",
    "n10_threats.tex", "n11_conclusion.tex", "n_back.tex",
]

PREAMBLE = """\\documentclass[11pt]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath,amssymb}
\\usepackage{booktabs}
\\usepackage{graphicx}
\\usepackage{longtable}
\\usepackage{array}
\\usepackage[hidelinks]{hyperref}
"""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_aux_labels() -> dict[str, str]:
    """label -> rendered number, from the compiled main_20p.aux."""
    labels: dict[str, str] = {}
    text = read(HERE / "main_20p.aux")
    for m in re.finditer(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", text):
        labels[m.group(1)] = m.group(2)
    return labels


def parse_bbl_numbers() -> dict[str, str]:
    """bib key -> printed reference number, in .bbl order."""
    text = read(HERE / "main_20p.bbl")
    keys = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", text)
    return {k: str(i + 1) for i, k in enumerate(keys)}


def compress(nums: list[str]) -> str:
    ints = sorted({int(n) for n in nums})
    parts: list[str] = []
    i = 0
    while i < len(ints):
        j = i
        while j + 1 < len(ints) and ints[j + 1] == ints[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append(f"{ints[i]}--{ints[j]}")
        else:
            parts.extend(str(ints[k]) for k in range(i, j + 1))
        i = j + 1
    return ",".join(parts)


def patch_body(text: str, refs: dict[str, str], labels: dict[str, str]) -> str:
    # citations -> printed numbers
    def cite_repl(m: re.Match) -> str:
        keys = [k.strip() for k in m.group(1).split(",")]
        nums = [refs[k] for k in keys if k in refs]
        if not nums:
            return "[citation:" + m.group(1) + "]"
        return "[" + compress(nums) + "]"

    text = re.sub(r"\\citep?\{([^}]+)\}", cite_repl, text)
    text = re.sub(r"\\cite\{([^}]+)\}", cite_repl, text)

    # cross references -> rendered numbers
    text = re.sub(r"\\ref\{([^}]+)\}",
                  lambda m: labels.get(m.group(1), "??"), text)
    text = re.sub(r"\\(?:eqref|autoref|pageref)\{([^}]+)\}",
                  lambda m: labels.get(m.group(1), "??"), text)

    # labels carry no meaning in Word
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    # figure*/table* -> figure/table so pandoc keeps them as floats
    text = text.replace("\\begin{figure*}", "\\begin{figure}")
    text = text.replace("\\end{figure*}", "\\end{figure}")
    text = text.replace("\\begin{table*}", "\\begin{table}")
    text = text.replace("\\end{table*}", "\\end{table}")
    # column decorations pandoc cannot parse
    text = text.replace(">{\\raggedright\\arraybackslash}", "")
    text = re.sub(r"p\{[\d.]+\\textwidth\}", "p{4cm}", text)
    text = re.sub(r"p\{[\d.]+\\columnwidth\}", "p{3cm}", text)
    # macros
    text = text.replace("\\protect", "")
    text = re.sub(r"(?<!\\)\\yes\b", "✓", text)
    text = re.sub(r"(?<!\\)\\no\b", "–", text)
    # png figures
    text = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?)\{([^}]+)\}",
                  r"\1{figs/\2.png}", text)
    # drop float placement hints and size wrappers pandoc ignores anyway
    text = re.sub(r"\\begin\{(figure|table)\}\[!?[tbph]+\]",
                  r"\\begin{\1}", text)
    return text


def clean_bbl(bbl: str, refs: dict[str, str]) -> str:
    """Flatten the .bbl into numbered plain-text entries for Word."""
    bbl = re.sub(r"\\expandafter\\ifx.*?\\fi\n", "", bbl, flags=re.S)
    bbl = bbl.replace("\\begin{thebibliography}{10}", "")
    bbl = bbl.replace("\\end{thebibliography}", "")
    bbl = re.sub(r"\\path\{([^}]*)\}", r"\1", bbl)
    bbl = re.sub(r"\\href\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\2", bbl)
    bbl = re.sub(r"\\url\{([^{}]*)\}", r"\1", bbl)
    bbl = bbl.replace("\\urlprefix", "")
    bbl = bbl.replace("\\newblock", " ")

    def item_repl(m: re.Match) -> str:
        n = refs.get(m.group(1), "?")
        return f"\n\n[{n}] "

    return re.sub(r"\\bibitem\{([^}]+)\}", item_repl, bbl)


def build_main() -> str:
    src = read(HERE / "main_20p.tex")
    refs = parse_bbl_numbers()
    labels = parse_aux_labels()

    title_m = re.search(r"\\title\{(.*?)\}\s*\n\\author", src, re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)) if title_m else "HMRS"

    abs_m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", src, re.S)
    abstract = abs_m.group(1).strip() if abs_m else ""
    abstract = re.sub(r"%.*", "", abstract)

    kw_m = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", src, re.S)
    keywords = ""
    if kw_m:
        keywords = kw_m.group(1).replace("\\sep", "·").strip()
        keywords = re.sub(r"\s+", " ", re.sub(r"%.*", "", keywords))

    parts = [PREAMBLE]
    parts.append(f"\\title{{{title}}}\n")
    parts.append("\\author{Author Name\\and Co-author Name}\n")
    parts.append("\\begin{document}\n\\maketitle\n")
    parts.append("\\begin{abstract}\n" + abstract + "\n\\end{abstract}\n")
    if keywords:
        parts.append("\n\\noindent\\textbf{Keywords:} " + keywords + "\n")
    parts.append("\n\\vspace{1em}\n")

    for name in MAIN_FILES:
        body = read(HERE / name)
        parts.append("\n" + patch_body(body, refs, labels) + "\n")

    bbl = clean_bbl(read(HERE / "main_20p.bbl"), refs)
    parts.append("\n\\section*{References}\n" + bbl + "\n")
    parts.append("\\end{document}\n")
    return "".join(parts)


def build_supp() -> str:
    src = read(HERE / "supplementary.tex")
    refs: dict[str, str] = {}
    labels: dict[str, str] = {}

    body_m = re.search(r"\\begin\{document\}(.*?)\\end\{document\}",
                       src, re.S)
    body = body_m.group(1) if body_m else src
    body = body.replace("\\twocolumn[{%\n\\centering\n"
                        "\\section*{Supplementary Material}\n}]\n", "")
    body = body.replace("\\input{supplementary-arm-tables}",
                        read(HERE / "supplementary-arm-tables.tex"))
    body = patch_body(body, refs, labels)

    out = [PREAMBLE]
    out.append("\\title{Supplementary Material for the HMRS manuscript}\n")
    out.append("\\begin{document}\n\\maketitle\n")
    out.append(body)
    out.append("\\end{document}\n")
    return "".join(out)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "main"
    if mode == "main":
        out = build_main()
    elif mode == "supp":
        out = build_supp()
    else:
        raise SystemExit("mode must be main|supp")
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    main()
