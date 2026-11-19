#!/usr/bin/env python3
"""Prepare a Pandoc LaTeX input from an already compiled HMRS manuscript.

Run as _make_docx_src.py main or _make_docx_src.py supp. The converter reads the
matching aux file and, for main, the bibliography produced by BibTeX. Render
the included PDFs to same-named PNGs in figs/ before Pandoc reads the output.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORD_TEXT_WIDTH_CM = 16.5

BIBITEM = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}")
LABEL = re.compile(r"\\label\{([^}]+)\}")
CITE = re.compile(r"\\citep?\{([^}]+)\}")
FLOAT = re.compile(
    r"\\begin\{(figure|table)(\*?)\}(?:\[[^]]*\])?(.*?)\\end\{\1\2\}", re.S
)
ALGORITHM = re.compile(r"\\begin\{algorithm\}(?:\[[^]]*\])?(.*?)\\end\{algorithm\}", re.S)


def read(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*(?:\n|$)", "", text)


def aux_labels(aux: str) -> dict[str, str]:
    return dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", aux))


def source_section(text: str, environment: str) -> str:
    match = re.search(
        rf"\\begin\{{{environment}\}}(.*?)\\end\{{{environment}\}}", text, re.S
    )
    if not match:
        raise ValueError(f"No {environment} environment found")
    return match.group(1).strip()


def escape_tex(text: str) -> str:
    return re.sub(r"(?<!\\)([_#%&$])", r"\\\1", text)


def format_paths(text: str) -> str:
    return re.sub(
        r"\\path\{([^{}]+)\}", lambda m: r"\texttt{" + escape_tex(m[1]) + "}", text
    )


def format_bibliography(bbl: str, aux: str) -> tuple[str, dict[str, str]]:
    numbers = dict(re.findall(r"\\bibcite\{([^}]+)\}\{\{([0-9]+)\}", aux))
    matches = list(BIBITEM.finditer(bbl))
    if len(matches) != len(numbers) or not matches:
        raise ValueError("The compiled bibliography and aux citation counts differ")
    entries = []
    for index, match in enumerate(matches, 1):
        key = match[1]
        if numbers.get(key) != str(index):
            raise ValueError(f"Reference order differs between bibliography and aux for {key}")
        next_start = matches[index].start() if index < len(matches) else len(bbl)
        body = bbl[match.end():next_start].replace(r"\end{thebibliography}", "").strip()
        body = format_paths(body).replace(r"\newblock", " ").replace(r"\urlprefix", "URL ")
        body = body.replace(r"\newline", " ")
        entries.append(f"[{index}] " + " ".join(body.split()))
    return "\n\n".join(entries), numbers


def numbered_headings(text: str) -> str:
    counts = [0, 0]

    def number(match: re.Match[str]) -> str:
        command = match[1]
        if command == "section":
            counts[0] += 1
            counts[1] = 0
            ordinal = str(counts[0])
        else:
            counts[1] += 1
            ordinal = f"{counts[0]}.{counts[1]}"
        return "\\" + command + "{" + ordinal + ". "

    return re.sub(r"\\(section|subsection)\{", number, text)


def format_floats(text: str, labels: dict[str, str], *, supplement: bool) -> str:
    counters = Counter({"table": 8 if supplement else 0})

    def numbered_float(match: re.Match[str]) -> str:
        kind, body = match[1], match[3]
        counters[kind] += 1
        expected = ("S" if supplement else "") + str(counters[kind])
        label = LABEL.search(body)
        if label and labels.get(label[1]) != expected:
            raise ValueError(f"{label[1]} does not match compiled {kind} number {expected}")
        tag = r"\textbf{" + f"{kind.title()} {expected}." + "}"
        if r"\caption{" not in body:
            raise ValueError(f"No caption for {kind} {expected}")
        body = body.replace(r"\caption{", r"\caption{" + tag + " ", 1)
        return f"\\begin{{{kind}}}" + body + f"\\end{{{kind}}}"

    return FLOAT.sub(numbered_float, text)


def format_algorithm(match: re.Match[str], labels: dict[str, str]) -> str:
    source = match[1]
    label, caption = LABEL.search(source), re.search(r"\\caption\{([^}]+)\}", source)
    if not label or label[1] not in labels or not caption:
        raise ValueError("An algorithm has no compiled number or caption")
    body = re.search(r"\\begin\{algorithmic\}(?:\[[^]]+\])?(.*?)\\end\{algorithmic\}",
                     source, re.S)
    if not body:
        raise ValueError("Missing algorithmic block")

    rows = [r"\textbf{" + f"Algorithm {labels[label[1]]}. {caption[1]}" + "}"]
    step = 0
    for raw_line in body[1].strip().splitlines():
        line = raw_line.strip()
        line = re.sub(r"\\Comment\{([^}]+)\}", r" (\1)", line)
        line = line.replace(r"\textsc{", r"\mathrm{").replace(r"\Return ", r"\textbf{return} ")
        if line.startswith(r"\Require "):
            rows.append(line.replace(r"\Require ", r"\textbf{Require.} ", 1))
            continue
        condition = re.fullmatch(r"\\(If|ElsIf)\{(.*)\}", line)
        if condition:
            word = "if" if condition[1] == "If" else "else if"
            line = r"\textbf{" + word + "} " + condition[2] + r" \textbf{then}"
        elif line == r"\Else":
            line = r"\textbf{else}"
        elif line == r"\EndIf":
            line = r"\textbf{end if}"
        elif line.startswith(r"\State "):
            line = line.removeprefix(r"\State ")
        else:
            raise ValueError(f"Unsupported algorithm line {raw_line}")
        step += 1
        rows.append(f"{step}. {line}")
    return "\\begin{quote}\n" + "\n\n".join(rows) + "\n\\end{quote}"


def patch_body(text: str, refs: dict[str, str], labels: dict[str, str],
               *, supplement: bool = False) -> str:
    used: set[str] = set()

    def cite_replace(match: re.Match[str]) -> str:
        keys = [k.strip() for k in match[1].split(",")]
        missing = set(keys) - refs.keys()
        if missing:
            raise ValueError(f"Unresolved citation keys {sorted(missing)}")
        used.update(keys)
        return "[" + ", ".join(refs[k] for k in keys) + "]"

    text = CITE.sub(cite_replace, text)
    if set(refs) != used or re.search(r"\\cite[a-zA-Z]*\s*[\[{]", text):
        raise ValueError("The Word source and compiled bibliography do not have the same citations")
    text = format_floats(text, labels, supplement=supplement)
    text = ALGORITHM.sub(lambda m: format_algorithm(m, labels), text)

    def ref_replace(match: re.Match[str]) -> str:
        key = match[2]
        value = labels.get(key)
        if value is None:
            raise ValueError(f"Unresolved cross-reference {key}")
        return f"({value})" if match[1] == "eqref" else value

    text = re.sub(r"\\(ref|eqref)\{([^}]+)\}", ref_replace, text)
    if re.search(r"\\(?:autoref|pageref)\{", text):
        raise ValueError("Use a section, figure or table number for the Word cross-reference")
    text = LABEL.sub("", text)
    text = text.replace(r">{\raggedright\arraybackslash}", "")
    # Pandoc incorrectly turns booktabs' optional cmidrule arguments into cell text.
    text = re.sub(r"\\cmidrule(?:\([^)]*\))?\{[^}]*\}", "", text)
    text = re.sub(
        r"p\{([\d.]+)\\(?:textwidth|columnwidth)\}",
        lambda m: f"p{{{float(m[1]) * WORD_TEXT_WIDTH_CM:.3f}cm}}",
        text,
    )
    text = format_paths(text.replace(r"\protect", ""))
    text = re.sub(r"(?<!\\)\\yes\b", "✓", text)
    text = re.sub(r"(?<!\\)\\no\b", "–", text)
    text = re.sub(
        r"\\includegraphics(?:\[width=\\(textwidth|columnwidth)\])?\{([^}]+)\}",
        lambda m: r"\includegraphics[width=" + ("4.1in" if m[1] == "columnwidth" else "6.45in")
        + "]{figs/" + m[2] + ".png}",
        text,
    )
    return numbered_headings(text) if not supplement else text


def build_main() -> str:
    src = strip_comments(read("main_20p.tex"))
    aux = read("main_20p.aux")
    bibliography, refs = format_bibliography(read("main_20p.bbl"), aux)
    title = re.search(r"\\title\{([^}]+)\}", src)
    if not title:
        raise ValueError("No manuscript title found")
    authors = re.findall(
        r"\\author(?:\[[^\]]+\])?\{((?:[^{}]|\\corref\{[^{}]*\})+)\}", src
    )
    authors = [re.sub(r"\\corref\{[^{}]*\}", "", a).strip() for a in authors]
    if not authors:
        raise ValueError("No manuscript authors found")
    affiliations = re.findall(r"organization=\{([^{}]+)\}", src)
    emails = re.findall(r"\\ead\{([^}]+)\}", src)
    frontmatter = "\\author{" + r"\and ".join(authors) + "}\n"
    title_lines = [rf"\title{{{title[1]}}}", frontmatter, r"\begin{document}", r"\maketitle"]
    title_lines.extend(f"\\begin{{center}}{item}\\end{{center}}" for item in affiliations)
    title_lines.extend(
        f"\\begin{{center}}Correspondence: \\href{{mailto:{email}}}{{{escape_tex(email)}}}\\end{{center}}"
        for email in emails
    )
    abstract = source_section(src, "abstract")
    keywords = " ".join(source_section(src, "keyword").replace(r"\sep", "·").split())
    body = "\n\n".join(
        strip_comments(read(name + ".tex")) for name in re.findall(r"\\input\{([^}]+)\}", src)
    )
    header = "\n".join(title_lines) + "\n\n"
    return (
        header + "\\section*{Abstract}\n\n" + abstract + "\n\n"
        + r"\noindent\textbf{Keywords:} " + keywords + "\n\n"
        + patch_body(body, refs, aux_labels(aux))
        + "\n\\section*{References}\n\n" + bibliography + "\n\\end{document}\n"
    )


def build_supp() -> str:
    body = source_section(strip_comments(read("supplementary.tex")), "document")
    body = re.sub(r"\\setcounter[^\n]*\n", "", body, count=1)
    body = re.sub(
        r"\\twocolumn\[\{\s*\\begin\{minipage\}\{\\textwidth\}\s*"
        r"\{\\centering\s*\\section\*\{Supplementary Material\}\s*\}", "", body, count=1
    )
    body = re.sub(
        r"\\medskip\s*\{\\centering\s*(\\includegraphics[^\n]+)\s*\\par\}\s*"
        r"\\captionof\{figure\}((?:.|\n)*?)\\end\{minipage\}\s*\\vspace\{12pt\}\s*\}\]",
        r"\\begin{figure}\n\1\n\\caption\2\\end{figure}", body, count=1
    )
    if r"\captionof" in body or r"\twocolumn" in body:
        raise ValueError("The supplementary title and figure layout could not be flattened")
    body = re.sub(
        r"\\input\{([^}]+)\}", lambda m: strip_comments(read(m[1] + ".tex")), body
    )
    return (
        "\\title{Supplementary Material for the HMRS manuscript}\n"
        "\\begin{document}\n\\maketitle\n"
        + patch_body(body, {}, aux_labels(read("supplementary.aux")), supplement=True)
        + "\n\\end{document}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("main", "supp"), nargs="?", default="main")
    mode = parser.parse_args().mode
    document = build_main() if mode == "main" else build_supp()
    sys.stdout.buffer.write(document.encode("utf-8"))


if __name__ == "__main__":
    main()
