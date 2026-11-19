#!/usr/bin/env python3
"""Build the three editable HMRS Word files from a freshly LaTeX-compiled clone.

Requires Python 3.10+, python-docx 1.2+, Pandoc 3.1.8+, and Poppler pdftoppm
for PDF figures. In the clone, compile main_20p (or main_20p_review) through
BibTeX and the final LaTeX pass, and compile supplementary.tex. For example:
    latexmk -pdf main_20p_review.tex supplementary.tex

From outside the clone, run:
    python -IB /path/to/build_word.py --source-dir /path/to/clone --main-job main_20p_review --check-only
    python -IB /path/to/build_word.py --source-dir /path/to/clone --main-job main_20p_review --output-dir /path/to/new-word-dir

Only --output-dir writes files. It emits main.docx, supplementary.docx and
highlights.docx. No TeX compiler or Word renderer is invoked. Review figure
and table pagination in the publishing renderer before accepting its output.
The separate S1–S8 companion inventory is outside this helper's scope.
This adapter targets the HMRS LaTeX dialect, not arbitrary LaTeX projects.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterator

from docx import Document
from docx.document import Document as WordDocument
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, Twips
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import _Element, tostring

TOOLS = Path(__file__).resolve().parent
INPUT = re.compile(r"\\input\s*\{([^{}]+)\}")
LABEL = re.compile(r"\\label\s*\{([^{}]+)\}")
FLOAT = re.compile(r"\\begin\{(figure|table)(\*?)\}(?:\s*\[[^]]*\])?(.*?)\\end\{\1\2\}", re.S)
CAPTION = re.compile(r"\\caption\s*(?:\[[^]]*\]\s*)?\{")
GRAPHIC = re.compile(r"\\includegraphics\s*(?:\[([^]]*)\])?\s*\{([^{}]+)\}")
BIBITEM = re.compile(r"\\bibitem(?:\[[^]]*\])?\{([^{}]+)\}")
CEILING = re.compile(r"(?:\\left\s*)?\\lceil\s*3\s*n\s*/\s*5\s*(?:\\right\s*)?\\rceil")
# Fixed grid widths (twips) from dist/november-final, keyed by visible caption number.
TABLE_WIDTHS = {
    "1": (1100, 1700, 1800, 1700, 1620),
    "2": (1150, 1470, 1520, 1150, 1600, 1030),
    "3": (1200, 2300, 3200, 1220),
    "4": (1150, 1550, 1900, 1450, 1870),
    "S9": (1710, 2410, 4100, 850),
    "S10": (850, 1700, 2050, 1900, 1420),
    "S11": (1550, 2490, 2400, 2630),
    "S12": (1640, 910, 1820, 1190, 1380, 1210, 920),
    "S13": (1400, 2300, 1400, 1400, 1420),
    "S14": (630, 2000, 1050, *([470] * 9)),
    "S15": (1900, 900, 850, 850, 900, 1200, 1320),
    "S16": (1500, 3210, 3210),
    "S17": (1670, 2230, 2200, 2970),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)((?:\\\\)*)%[^\n]*(?:\n|$)", r"\1", text)


def environment(text: str, name: str) -> str:
    match = re.search(rf"\\begin\{{{name}\}}(.*?)\\end\{{{name}\}}", text, re.S)
    if not match:
        raise ValueError(f"Missing {name} environment")
    return match[1].strip()


def escape_tex(text: str) -> str:
    return re.sub(r"(?<!\\)([_#%&$])", r"\\\1", text)


def paths_to_code(text: str) -> str:
    return re.sub(r"\\path\{([^{}]+)\}", lambda m: r"\texttt{" + escape_tex(m[1]) + "}", text)


@dataclass(frozen=True)
class Asset:
    path: Path
    width: int  # twips


class Source:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tex_files: set[Path] = set()
        self.assets: dict[str, Asset] = {}

    def local(self, name: str) -> Path:
        path = (self.root / name).resolve()
        require(path.is_relative_to(self.root), f"Path leaves source clone: {name}")
        return path

    def read(self, name: str) -> str:
        path = self.local(name)
        require(path.is_file() and path.stat().st_size > 0, f"Missing or empty input: {path}")
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".tex":
            self.tex_files.add(path)
            return strip_comments(text)
        return text

    def expand(self, text: str, stack: tuple[Path, ...] = ()) -> str:
        def include(match: re.Match[str]) -> str:
            name = match[1].strip()
            if not name.endswith(".tex"):
                name += ".tex"
            path = self.local(name)
            require(path not in stack, f"Cyclic TeX input: {path}")
            return "\n\n" + self.expand(self.read(name), (*stack, path)) + "\n\n"

        return INPUT.sub(include, text)

    def graphic(self, match: re.Match[str]) -> str:
        options, source = match[1] or "", Path(match[2].strip())
        opts = re.fullmatch(r"\s*width\s*=\s*\\(textwidth|columnwidth)\s*", options)
        require(not options or opts is not None, f"Unsupported graphics options for {source}: {options}")
        require(not source.is_absolute() and not source.drive, f"Figure must be local: {source}")
        exts = (".pdf", ".png", ".jpg", ".jpeg")
        names = [source] if source.suffix else [source.with_suffix(ext) for ext in exts]
        candidates = [self.local(str(folder / name)) for folder in (Path(), Path("figs")) for name in names]
        asset = next((file for file in candidates if file.is_file()), None)
        if asset is None or asset.suffix.lower() not in exts:
            raise ValueError(f"Missing or unsupported figure {source}; expected a local PDF, PNG or JPEG")
        key = f"hmrs_asset_{len(self.assets) + 1}.png"
        width = 5904 if opts and opts[1] == "columnwidth" else 8400
        self.assets[key] = Asset(asset, width)
        return rf"\includegraphics[width={width / 1440:.5f}in]{{{key}}}"


def labels_from(aux: str) -> dict[str, str]:
    pairs = re.findall(r"\\newlabel\{([^{}]+)\}\{\{([^{}]*)\}", aux)
    labels = dict(pairs)
    require(len(labels) == len(pairs), "Duplicate labels in compiled aux")
    return labels


def bibliography(bbl: str, aux: str) -> tuple[str, dict[str, str]]:
    pairs = re.findall(r"\\bibcite\{([^{}]+)\}\{(?:\{)?(\d+)\}", aux)
    numbers = dict(pairs)
    items = list(BIBITEM.finditer(bbl))
    require(bool(items) and len(items) == len(numbers) == len(pairs), "AUX and BBL citation counts differ")
    entries = []
    for i, item in enumerate(items, 1):
        require(numbers.get(item[1]) == str(i), f"AUX and BBL citation order differs for {item[1]}")
        end = items[i].start() if i < len(items) else bbl.rindex(r"\end{thebibliography}")
        body = bbl[item.end():end].replace(r"\newblock", " ").replace(r"\newline", " ")
        body = body.replace(r"\urlprefix", "URL ")
        entries.append(f"[{i}] " + " ".join(paths_to_code(body).split()))
    return "\n\n".join(entries), numbers


def flatten_algorithm(match: re.Match[str], labels: dict[str, str]) -> str:
    text = match[1]
    label = LABEL.search(text)
    caption = re.search(r"\\caption\{([^{}]+)\}", text)
    if not label or not caption or label[1] not in labels:
        raise ValueError("Algorithm missing compiled label or caption")
    body = re.sub(r"^\s*\[\d+\]", "", environment(text, "algorithmic"))
    lines = [r"\textbf{" + f"Algorithm {labels[label[1]]}. {caption[1]}" + "}"]
    step = 0
    for raw in body.strip().splitlines():
        line = re.sub(r"\\Comment\{([^{}]+)\}", r" (\1)", raw.strip())
        line = line.replace(r"\textsc{", r"\mathrm{").replace(r"\Return ", r"\textbf{return} ")
        if line.startswith(r"\Require "):
            lines.append(line.replace(r"\Require ", r"\textbf{Require.} ", 1))
            continue
        condition = re.fullmatch(r"\\(If|ElsIf)\{(.*)\}", line)
        if condition:
            keyword = "if" if condition[1] == "If" else "else if"
            line = rf"\textbf{{{keyword}}} {condition[2]} \textbf{{then}}"
        elif line in (r"\Else", r"\EndIf"):
            line = r"\textbf{else}" if line == r"\Else" else r"\textbf{end if}"
        elif line.startswith(r"\State "):
            line = line.removeprefix(r"\State ")
        else:
            raise ValueError(f"Unsupported algorithm line: {raw}")
        step += 1
        lines.append(f"{step}. {line}")
    return "\\begin{quote}\n" + "\n\n".join(lines) + "\n\\end{quote}"


def number_headings(text: str) -> str:
    counts = [0, 0, 0]
    commands = ("section", "subsection", "subsubsection")

    def number(match: re.Match[str]) -> str:
        level = commands.index(match[1])
        counts[level] += 1
        counts[level + 1:] = [0] * (2 - level)
        return "\\" + match[1] + "{" + ".".join(map(str, counts[:level + 1])) + ". "

    return re.sub(r"\\(section|subsection|subsubsection)\s*\{", number, text)


def prep_body(source: Source, text: str, aux: str, refs: dict[str, str], *, supp: bool) -> str:
    labels = labels_from(aux)
    expected = {
        "figure": [("S" if supp else "") + str(i) for i in range(1, 8)],
        "table": [n for n in TABLE_WIDTHS if n.startswith("S") == supp],
    }
    used: set[str] = set()
    counters: Counter[str] = Counter()

    def cite(match: re.Match[str]) -> str:
        keys = [k.strip() for k in match[1].split(",")]
        missing = set(keys) - refs.keys()
        require(not missing, f"Unresolved citations: {sorted(missing)}")
        used.update(keys)
        return "[" + ", ".join(refs[k] for k in keys) + "]"

    def ref(match: re.Match[str]) -> str:
        label = match[2]
        require(label in labels and bool(labels[label]), f"Unresolved reference: {label}")
        return f"({labels[label]})" if match[1] == "eqref" else labels[label]

    def numbered_float(match: re.Match[str]) -> str:
        kind, body = match[1], match[3]
        index = counters[kind]
        require(index < len(expected[kind]), f"Unexpected extra {kind}")
        number = expected[kind][index]
        counters[kind] += 1
        for label in LABEL.findall(body):
            require(labels.get(label) == number, f"{label}: expected compiled {kind} number {number}")
        captions = list(CAPTION.finditer(body))
        require(len(captions) == 1, f"Expected one caption for {kind} {number}")
        cap = captions[0]
        body = body[:cap.start()] + rf"\caption{{\textbf{{{kind.title()} {number}.}} " + body[cap.end():]
        return rf"\begin{{{kind}}}{body}\end{{{kind}}}"

    text = re.sub(r"\\citep?\s*\{([^{}]+)\}", cite, text)
    require(used == set(refs) and not re.search(r"\\(?:cite[a-zA-Z]*|nocite)\b", text),
            "Source citations differ from BBL/AUX or use unsupported citation commands")
    text = FLOAT.sub(numbered_float, text)
    for kind, numbers in expected.items():
        # TeX may ship floats on different pages or in a different inter-kind order.
        # The compiled LoF/LoT also covers the unlabeled Table S11.
        listed = re.findall(rf"\\contentsline\s*\{{{kind}\}}\s*\{{\\numberline\s*\{{([^}}]+)\}}", aux)
        require(Counter(listed) == Counter(numbers) and counters[kind] == len(numbers),
                f"{'Supplement' if supp else 'Main'} {kind} count/numbering differs from the expected AUX inventory")
    text = re.sub(r"\\begin\{algorithm\}(?:\[[^]]*\])?(.*?)\\end\{algorithm\}",
                  lambda m: flatten_algorithm(m, labels), text, flags=re.S)
    text = re.sub(r"\\(ref|eqref)\s*\{([^{}]+)\}", ref, text)
    require(not re.search(r"\\(?:ref|eqref|autoref|pageref|cref|Cref|include|input)\b", text),
            "Unsupported cross-reference or unresolved input in Word source")
    text = LABEL.sub("", text).replace(r">{\raggedright\arraybackslash}", "")
    # Pandoc otherwise emits booktabs' (lr) arguments as cell text.
    text = re.sub(r"\\cmidrule(?:\([^)]*\))?\{[^{}]*\}", "", text)
    text = re.sub(r"p\{([\d.]+)\\(?:textwidth|columnwidth)\}",
                  lambda m: f"p{{{float(m[1]) * 16.5:.3f}cm}}", text)
    text = paths_to_code(text.replace(r"\protect", ""))
    text = re.sub(r"(?<!\\)\\yes\b", "✓", text)
    text = re.sub(r"(?<!\\)\\no\b", "–", text)
    text = GRAPHIC.sub(source.graphic, text)
    return text if supp else number_headings(text)


def fresh(source: Source, job: str, *, bbl: bool, allow_stale: bool) -> None:
    aux = source.local(job + ".aux")
    stamp = aux.stat().st_mtime_ns
    newer = sorted(p.relative_to(source.root).as_posix() for p in source.tex_files | {a.path for a in source.assets.values()}
                   if p.stat().st_mtime_ns > stamp)
    if bbl and source.local(job + ".bbl").stat().st_mtime_ns > stamp:
        newer.append(job + ".bbl")
    if newer:
        message = f"{aux.name} predates {', '.join(newer)}; recompile the clone through the final LaTeX pass"
        require(allow_stale, message)
        print(f"Warning (snapshot check only): {message}", file=sys.stderr)


def main_source(source: Source, job: str, allow_stale: bool) -> tuple[str, int]:
    src = source.read("main_20p.tex")
    wrapper = source.local(job + ".tex")
    if wrapper.is_file():
        source.tex_files.add(wrapper)
    aux = source.read(job + ".aux")
    bib, refs = bibliography(source.read(job + ".bbl"), aux)
    document = environment(src, "document")
    front = environment(document, "frontmatter")
    tail = document.split(r"\end{frontmatter}", 1)[1]
    bib_start = re.search(r"\{\s*\\ifdefined\\HMRSReviewLayout.*?\\bibliography\{[^{}]+\}\s*\}", tail, re.S)
    if not bib_start:
        bib_start = re.search(r"\\bibliographystyle\{[^{}]+\}\s*\\bibliography\{[^{}]+\}", tail)
    if not bib_start:
        raise ValueError("No supported bibliography block after main body")
    require(not tail[bib_start.end():].strip(), "Unexpected content after main bibliography")
    for names in re.findall(r"\\bibliography\{([^{}]+)\}", bib_start[0]):
        for name in names.split(","):
            path = source.local(name.strip() + ".bib")
            if path.is_file():
                source.tex_files.add(path)
    title = re.search(r"\\title\s*\{((?:[^{}]|\{[^{}]*\})+)\}", front)
    authors = re.findall(r"\\author(?:\[[^]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})+)\}", front)
    authors = [re.sub(r"\\corref\{[^{}]*\}", "", a).strip() for a in authors]
    if not title or not authors:
        raise ValueError("Missing manuscript title or authors")
    abstract = environment(front, "abstract")
    keywords = " ".join(environment(front, "keyword").replace(r"\sep", "·").split())
    lines = [r"\title{" + title[1] + "}", r"\author{" + r"\and ".join(authors) + "}",
             r"\begin{document}", r"\maketitle"]
    for aff in re.findall(r"\\affiliation(?:\[[^]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", front):
        fields = dict(re.findall(r"(organization|addressline|city|postcode|state|country)\s*=\s*\{([^{}]+)\}", aff))
        address: list[str] = []
        for key in ("organization", "addressline", "city", "postcode", "state", "country"):
            value = " ".join(fields.get(key, "").split())
            if value and not re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", ", ".join(address)):
                address.append(value)
        require(bool(address), "Unsupported empty affiliation")
        lines.append(r"\begin{center}" + ", ".join(address) + r"\end{center}")
    for email in re.findall(r"\\ead\s*\{([^{}]+)\}", front):
        lines.append(rf"\begin{{center}}Correspondence: \href{{mailto:{email}}}{{{escape_tex(email)}}}\end{{center}}")
    preamble_text = (r"\section*{Abstract}" + "\n\n" + abstract + "\n\n"
                     + r"\noindent\textbf{Keywords:} " + keywords + "\n\n")
    body = prep_body(source, preamble_text + source.expand(tail[:bib_start.start()]), aux, refs, supp=False)
    fresh(source, job, bbl=True, allow_stale=allow_stale)
    return ("\n".join(lines) + "\n\n" + body + "\n\n" + r"\section*{References}"
            + "\n\n" + bib + "\n" + r"\end{document}"), len(refs)


def supplement_source(source: Source, allow_stale: bool) -> str:
    body = environment(source.read("supplementary.tex"), "document")
    # The S1 caption is a captionof in a two-column front-page minipage.
    body = re.sub(r"^\\setcounter[^\n]*\n", "", body, count=1)
    body = re.sub(r"\\twocolumn\[\{\s*\\begin\{minipage\}\{\\textwidth\}\s*"
                  r"\{\\centering\s*\\section\*\{Supplementary Material\}\s*\}", "", body, count=1)
    body = re.sub(r"\\medskip\s*\{\\centering\s*(\\includegraphics[^\n]+)\s*\\par\}\s*"
                  r"\\captionof\{figure\}(.*?)\\end\{minipage\}\s*\\vspace\{12pt\}\s*\}\]",
                  r"\\begin{figure}\n\1\n\\caption\2\\end{figure}", body, count=1, flags=re.S)
    require(not re.search(r"\\(?:twocolumn|captionof)\b", body), "Unsupported supplementary front-page layout")
    aux = source.read("supplementary.aux")
    body = prep_body(source, source.expand(body), aux, {}, supp=True)
    fresh(source, "supplementary", bbl=False, allow_stale=allow_stale)
    return ("\\title{Supplementary Material for the HMRS manuscript}\n"
            "\\begin{document}\n\\maketitle\n" + body + "\n\\end{document}")


def run(command: list[str], data: bytes | None = None) -> bytes:
    result = subprocess.run(command, input=data, capture_output=True, cwd=TOOLS, timeout=120, check=False)
    if result.returncode:
        raise ValueError(f"{command[0]} exited {result.returncode}: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def nodes(value: Any, kind: str) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("t") == kind:
            yield value
        for child in value.values():
            yield from nodes(child, kind)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child, kind)


def image_data(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        # Like the source \includegraphics with no page option, use page 1.
        data = run(["pdftoppm", "-png", "-singlefile", "-cropbox", "-f", "1", "-l", "1", "-r", "300", str(path)])
        require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"No valid raster returned for {path}")
    else:
        data = path.read_bytes()
    mime = "image/png" if ext in (".pdf", ".png") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def convert(tex: str, assets: dict[str, Asset], ceil_text: bool) -> tuple[WordDocument, int, int]:
    args = ["pandoc", "--sandbox", "--fail-if-warnings"]
    ast = json.loads(run([*args, "-f", "latex", "-t", "json"], tex.encode("utf-8")))
    seen = []
    for node in nodes(ast, "Image"):
        target = node["c"][2]
        key = target[0]
        require(key in assets, f"Unexpected image in conversion: {key}")
        seen.append(key)
        target[0] = image_data(assets[key].path)
    require(seen == list(assets), "Pandoc dropped, duplicated or reordered figures")
    math = list(nodes(ast, "Math"))
    ceilings = 0
    for node in math:
        mode, formula = node["c"]
        if mode["t"] == "InlineMath" and CEILING.fullmatch(formula.strip()):
            ceilings += 1
            if ceil_text:
                node.update(t="Str", c="ceil(3n/5)")
            else:
                # Real stretchy OMML delimiters, not two separate ceiling glyph runs.
                node["c"][1] = r"\left\lceil 3n/5\right\rceil"
    data = run([*args, "-f", "json", "-t", "docx", "-o", "-"], json.dumps(ast).encode("utf-8"))
    doc = Document(BytesIO(data))
    expected = len(math) - (ceilings if ceil_text else 0)
    require(len(doc._element.xpath(".//m:oMath")) == expected, "Word equation count differs from Pandoc native math count")
    if ceilings:
        if ceil_text:
            require(sum(p.text.count("ceil(3n/5)") for p in doc.paragraphs) >= ceilings,
                    "The exact inline ceiling fallback was not emitted")
        else:
            require(len(doc._element.xpath('.//m:dPr[m:begChr/@m:val="⌈" and m:endChr/@m:val="⌉"]')) >= ceilings,
                    "The inline ceiling is missing native Word delimiters")
    return doc, expected, ceilings


def w_element(parent: _Element, name: str, *before: str, **attrs: str) -> _Element:
    node = parent.find(qn("w:" + name))
    if node is None:
        node = OxmlElement("w:" + name)
        successors = {qn("w:" + tag) for tag in before}
        for child in parent:
            if child.tag in successors:
                child.addprevious(node)
                break
        else:
            parent.append(node)
    for key, value in attrs.items():
        node.set(qn("w:" + key), value)
    return node


def style_table(table: Table, number: str, available: int) -> None:
    widths = TABLE_WIDTHS[number]
    rows = 2 if number in {"S12", "S14"} else 1
    require(len(table.columns) == len(widths) and len(table.rows) > rows and sum(widths) <= available,
            f"Table {number} changed shape or exceeds the text area; review its width profile")
    table.autofit = False
    pr = table._tbl.tblPr
    w_element(pr, "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
              "tblCellMar", "tblLook", w=str(sum(widths)), type="dxa")
    margins = w_element(pr, "tblCellMar", "tblLook", "tblCaption", "tblDescription")
    pad = 55 if number in {"S11", "S17"} else 26
    for side, size in [("top", pad), ("left", 45 if number == "S14" else 85),
                       ("bottom", pad), ("right", 45 if number == "S14" else 85)]:
        w_element(margins, side, w=str(size), type="dxa")
    borders = w_element(pr, "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook")
    rule = dict(val="single", sz="5", color="777777", space="0")
    for side in ("top", "bottom"):
        w_element(borders, side, **rule)
    if number in {"S11", "S17"}:
        w_element(borders, "insideH", val="single", sz="4", color="C0C0C0", space="0")
    for col, width in zip(table.columns, widths):
        col.width = Twips(width)
    for i, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        w_element(tr_pr, "cantSplit", "trHeight", "tblHeader", "tblCellSpacing", "jc", val="1")
        if i < rows:
            w_element(tr_pr, "tblHeader", "tblCellSpacing", "jc", val="1")
        elif (old_header := tr_pr.find(qn("w:tblHeader"))) is not None:
            tr_pr.remove(old_header)
        # Set physical cell widths, including cells spanning the grouped headers.
        column = row.grid_cols_before
        for cell in row._tr.tc_lst:
            end = column + cell.grid_span
            require(end <= len(widths), f"Table {number} row {i + 1} crosses its width profile")
            cell.width = Twips(sum(widths[column:end]))
            column = end
            if i == rows - 1:
                cell_borders = w_element(cell.get_or_add_tcPr(), "tcBorders", "shd", "noWrap", "tcMar",
                                         "textDirection", "tcFitText", "vAlign")
                w_element(cell_borders, "bottom", "right", "end", "insideH", "insideV", **rule)
            for element in cell.p_lst:
                paragraph = Paragraph(element, table)
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.keep_with_next = (
                    i < rows or number == "1" and i < len(table.rows) - 1
                )
                for run in paragraph.runs:
                    run.font.size = Pt(8 if number == "S14" else 9)
        require(column + row.grid_cols_after == len(widths), f"Table {number} row {i + 1} grid mismatch")


def caption(p: Paragraph, kind: str, number: str) -> None:
    expected_style = "Image Caption" if kind == "Figure" else "Table Caption"
    require(p.style.name == expected_style and p.text.startswith(f"{kind} {number}. "),
            f"Missing adjacent caption for {kind} {number}: {p.text[:75]!r}")
    p.paragraph_format.keep_together = True
    p.paragraph_format.keep_with_next = kind == "Table"


def content_signature(doc: WordDocument) -> list[tuple[str, str | bytes | None]]:
    # Verify that only presentation changed: all text nodes and all native equations stay intact.
    body = doc._element.body
    text = set(map(qn, ["w:t", "w:instrText"]))
    return [(e.tag, tostring(e) if e.tag == qn("m:oMath") else e.text) for e in body.iter()
            if e.tag in text or e.tag == qn("m:oMath")]


def format_word(doc: WordDocument, assets: dict[str, Asset], *, supp: bool) -> tuple[list[str], list[str]]:
    before = content_signature(doc)
    # November supplementary uses US Letter, one-inch margins; make those defaults explicit in both.
    for section in doc.sections:
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        section.left_margin = section.right_margin = section.top_margin = section.bottom_margin = Inches(1)
    if "Verbatim Char" in doc.styles:
        doc.styles["Verbatim Char"].font.name = "Courier New"  # distinguish l / 1 in identifiers
    table_ids = [n for n in TABLE_WIDTHS if n.startswith("S") == supp]
    figure_ids = [("S" if supp else "") + str(i) for i in range(1, 8)]
    shapes = list(doc.inline_shapes)
    counts = Counter(p.style.name for p in doc.paragraphs)
    require(len(shapes) == counts["Image Caption"] == len(figure_ids) == len(assets), "Unexpected figure/caption count")
    require(len(doc.tables) == counts["Table Caption"] == len(table_ids), "Unexpected table/caption count")
    for shape, number, asset in zip(shapes, figure_ids, assets.values()):
        element = shape._inline.getparent()
        while element is not None and element.tag != qn("w:p"):
            element = element.getparent()
        require(element is not None and element.getparent() is doc._element.body, f"Figure {number} is not inline in the body")
        following = element.getnext()
        require(following is not None and following.tag == qn("w:p"), f"No paragraph after Figure {number}")
        caption(Paragraph(following, doc), "Figure", number)
        picture = Paragraph(element, doc)
        picture.paragraph_format.keep_with_next = picture.paragraph_format.keep_together = True
        # Reserve caption space. S3 had a tighter November cap due to its long caption.
        height_limit = Inches(3.15 if number == "S3" else 4.4)
        width_limit = Twips(asset.width)
        require(shape.width > 0 and shape.height > 0, f"Invalid size for Figure {number}")
        factor = min(1.0, width_limit / shape.width, height_limit / shape.height)
        shape.width, shape.height = int(shape.width * factor), int(shape.height * factor)
    for table, number in zip(doc.tables, table_ids):
        previous = table._tbl.getprevious()
        require(previous is not None and previous.tag == qn("w:p"), f"No paragraph before Table {number}")
        caption(Paragraph(previous, doc), "Table", number)
        style_table(table, number, available=9360)
    require(content_signature(doc) == before, "Formatting changed text or native equations")
    return figure_ids, table_ids


def check_references(doc: WordDocument, count: int) -> None:
    paragraphs = doc.paragraphs
    sections = [i for i, p in enumerate(paragraphs) if p.text == "References" and p.style.name == "Heading 1"]
    require(len(sections) == 1, "Expected exactly one References heading in Word")
    numbers = [m[1] for p in paragraphs[sections[0] + 1:] if (m := re.match(r"^\[(\d+)\]\s", p.text))]
    require(numbers == [str(i) for i in range(1, count + 1)],
            "Word reference list differs from compiled bibliography order/count")


def package(doc: WordDocument) -> bytes:
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, required=True, help="compiled clone containing TeX, aux/bbl and figs/")
    parser.add_argument("--main-job", default="main_20p", help="matching AUX/BBL stem, e.g. main_20p_review")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true", help="convert, format and validate in memory; write nothing")
    action.add_argument("--output-dir", type=Path, help="new directory outside the compiled clone; write three DOCX files")
    parser.add_argument("--allow-stale-aux", action="store_true", help="allow timestamp warnings in snapshot checks only")
    parser.add_argument("--ceil-text", action="store_true", help="if necessary, use editable text for exactly ceil(3n/5)")
    args = parser.parse_args()
    try:
        require(not args.allow_stale_aux or args.check_only, "--allow-stale-aux requires --check-only")
        require(re.fullmatch(r"[\w-]+", args.main_job) is not None, "--main-job must be an AUX/BBL stem")
        root = args.source_dir.resolve(strict=True)
        require(root.is_dir(), f"Not a source directory: {root}")
        out = args.output_dir.resolve() if args.output_dir else None
        if out is not None:
            require(not out.exists() and out.parent.is_dir(), f"Output directory must be new, with an existing parent: {out}")
            require(not out.is_relative_to(root) and not root.is_relative_to(out), "Source and output directories must be separate")
        main_input, supp_input = Source(root), Source(root)
        main_tex, refs = main_source(main_input, args.main_job, args.allow_stale_aux)
        supp_tex = supplement_source(supp_input, args.allow_stale_aux)
        hl_tex = r"\begin{itemize}" + "\n" + environment(Source(root).read("highlights.tex"), "highlights") + "\n" + r"\end{itemize}"
        files: dict[str, bytes] = {}
        for name, tex, source in [("main", main_tex, main_input), ("supplementary", supp_tex, supp_input)]:
            doc, math, ceilings = convert(tex, source.assets, args.ceil_text)
            figures, tables = format_word(doc, source.assets, supp=name == "supplementary")
            if name == "main":
                check_references(doc, refs)
            files[name + ".docx"] = package(doc)
            extra = f", {refs} bibliography entries" if name == "main" else ""
            if ceilings:
                extra += f", {ceilings} ceiling(s) as {'editable text' if args.ceil_text else 'native delimiters'}"
            print(f"{name}: figures {', '.join(figures)}; tables {', '.join(tables)}; {math} native equations{extra}")
        doc, _, _ = convert(hl_tex, {}, args.ceil_text)
        bullets = len(re.findall(r"(?m)^\s*\\item\b", hl_tex))
        require(bullets > 0 and len(doc.paragraphs) == bullets and all(
            p.text.strip() and p._p.xpath("./w:pPr/w:numPr") for p in doc.paragraphs), "Highlights did not convert to editable bullets")
        files["highlights.docx"] = package(doc)
        print(f"highlights: {bullets} editable bullets")
        if out is not None:
            out.mkdir(exist_ok=False)
            for name, data in files.items():
                with (out / name).open("xb") as handle:
                    handle.write(data)
            print(f"Wrote three DOCX files to {out}. Rendering and visual review are separate steps.")
        else:
            print("Check only: no DOCX files written or pages rendered.")
    except (OSError, ValueError, subprocess.SubprocessError, StopIteration) as exc:
        print(f"Build stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
