#!/usr/bin/env python3
r"""Single-column case figure for E2: the HMRS agent and the one-shot baselines
on one question.

``fig_opt_case`` lays its evidence paths side by side at full text width. This
figure keeps the same visual grammar -- question card, process cards with a
coloured title strip, evidence, terminal verdict -- and stacks it vertically,
so that it fits one journal column (252 pt) at 7.1 pt text:

    question card
    (a) HMRS agent:         recorded tool calls -> evidence -> answer
    (b) one-shot baselines: retrieval -> evidence -> answers
    overall judge score of all eight arms on this question

Every displayed value is read from the shipped records and asserted before
anything is drawn (tool sequence, result counts and scores, the number of
context units and the absence of the gold paper in them, verdicts and scores).
Answer excerpts are slices of the stored answers; ``…`` marks omitted words.
The tool-call facts come from ``fig-hmrs-case-provenance.json``, a copy of the
stored session transcript of the HMRS run.

Drawn at its printed size, 252 x about 491 pt. Include it with
``width=\columnwidth``. With a caption it fills about four fifths of a column,
more than LaTeX's default ``topfraction`` allows, so place it with ``[!t]``.
After drawing, the script checks that no two labels overlap or leave the page.

Run from any directory with ``python build_fig_hmrs_vs_baseline.py``.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import Circle, PathPatch, Polygon

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figs"
DATA = ROOT / "experiment_data" / "external_baselines_v3"
ANSWERS = DATA / "answers-v3.jsonl"
JUDGMENTS = DATA / "judgments-unified.jsonl"
PROVENANCE = DATA / "fig-hmrs-case-provenance.json"

QID = "BQ07"
HMRS, RRF, GRAG = "hmrs-agent", "rrf", "graphrag"
ARMS = (HMRS, "bm25", "dense", RRF, "raptor", "lightrag", "deepread-native", GRAG)
# Arm names as they appear in the manuscript's native-comparison table.
NAMES = {HMRS: "HMRS", "bm25": "BM25", "dense": "Dense", RRF: "RRF-order", "raptor": "RAPTOR",
         "lightrag": "LightRAG", "deepread-native": "DeepRead", GRAG: "GraphRAG"}
DIMS = ("factual", "completeness", "groundedness", "sources")
UNIT_CHARS = 800           # character cap of one context unit in the one-shot arms

INK = "#24384A"
NAVY = "#294765"
BLUE = "#2F9ED1"
PALE_BLUE = "#EAF5FB"
OCHRE = "#C88A2C"
PALE_OCHRE = "#FBF3E4"
BRICK = "#B65737"
PALE_BRICK = "#F9ECE7"
GREEN = "#36A866"
PALE_GREEN = "#EAF7EE"
SLATE = "#75818C"
GRID = "#D9E2E8"
CARD = "#F3F5F6"
EVIDENCE = "#F7F8F8"
ICON = "#8DB5E5"
WHITE = "#FFFFFF"
VERDICT_COLOR = {"correct": GREEN, "partial": OCHRE, "incorrect": BRICK}

# Geometry in points; the figure is drawn at its printed size.
W = 252.0                 # elsarticle 5p column width
MARGIN_L, MARGIN_R = 9.0, 2.5
SPINE_X = 3.2             # shared question rail, left of the panels
X0 = MARGIN_L
CW = W - MARGIN_L - MARGIN_R
BODY, TITLE, QPT = 7.1, 8.2, 7.8
LH, LH_Q = 8.4, 9.4
STRIP_H = 10.2
PAD, PAD_X = 3.0, 4.2
PAD_P = 4.5               # inner padding of a panel
TITLE_H = 12.5
LABEL_W, LANE_W = 40.0, 62.0
RADIUS = 2.2
SEP = 3.4                 # hairline between row groups
TAG_PAD, TAG_GAP = 3.0, 5.0
GAP, GAP_PANEL, GAP_FOOT = 9.5, 8.0, 6.5
MARGIN = 2.0

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": BODY,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": WHITE,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.dpi": 300,
})

K = 0.5522847498307936    # cubic Bezier approximation of a quarter circle


# --------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------
def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def overall(j: dict) -> float:
    return sum(j[k] for k in DIMS) / 4


def slice_between(text: str, start: str, end: str) -> str:
    """Verbatim slice of ``text`` from ``start`` up to and including ``end``."""
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


ARXIV_ID = re.compile(r"\d{4}\.\d{4,5}|physics-\d{7}")


def paper_of(doc_path: str) -> str:
    """Paper behind a context unit: its arXiv identifier, else its file name.
    The arms name their units differently (`` (part i of n).md``,
    ``..._part_i_of_n_.md.txt``), so parts of one paper must be merged."""
    m = ARXIV_ID.search(doc_path)
    if m:
        return m.group(0)
    name = re.split(r"[\\/]", doc_path)[-1]
    return re.sub(r" \(part \d+ of \d+\)|\.md$", "", name)


def shown_keyword(k: str) -> str:
    """The annotated keywords are stored lower-case; show them as written."""
    return k.capitalize() if k[:1].isalpha() else k.upper()


def load_case() -> dict:
    answers = {(r["arm"], r["qid"]): r for r in load_jsonl(ANSWERS)}
    judged = {(r["arm"], r["qid"]): r for r in load_jsonl(JUDGMENTS)}
    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))

    hm, jh = answers[(HMRS, QID)], judged[(HMRS, QID)]
    calls = prov["calls"]
    gold = hm["arxiv"]
    assert gold == prov["question"]["gold_arxiv"]
    assert [c["tool"] for c in calls] == ["kb_search_two_stage", "kb_search_vector", "kb_doc_read"]
    assert prov["session"]["final_text_equals_stored_answer"] is True
    assert abs(prov["session"]["duration_ms"] / 1000 - hm["wall_s"]) < 0.6
    assert all(c["is_error"] is False for c in calls)
    two, vec, read = (c["result"] for c in calls)
    assert [c["turn"] for c in calls] == [1, 1, 2], "two searches share a turn, then one read"
    assert prov["session"]["turn_of_final_reply"] == hm["turns"] == 3
    assert two["stage1_gold_rank"] == 1
    assert two["stage2_gold_results"] == two["stage2_results"]
    assert vec["first_non_gold_rank"] == vec["gold_results"] + 1     # the top hits are all gold
    assert read["is_gold"] and read["quote_in_document"]

    hm_answer = hm["answer"]
    hm_excerpt = slice_between(hm_answer, "MameLoshnLM is the first", "Llama 3.1 8B.")
    assert hm_answer.startswith("**" + hm_excerpt)
    evidence_quote = read["evidence_quote"]          # a sentence of the document that was read
    assert evidence_quote.rstrip(".") in hm_answer    # the answer quotes the same sentence
    assert all(k.lower() in hm_answer.lower() for k in prov["question"]["gold_keywords"])

    baselines = []
    for arm, retrieval, scope, pieces in (
            (RRF, "BM25 + dense document ranks fused (k = 60)", "full export",
             (("None of the sources", '"MameLoshnLM"'), ("so I cannot answer", "given material."))),
            (GRAG, "12 nearest entities, then their text units", "30 gold parts",
             (("Nothing in [S1]", "parameter scale"), ("I cannot answer", "this context.")))):
        a, j = answers[(arm, QID)], judged[(arm, QID)]
        paths = [s["doc_path"] for s in a["sources"]]
        assert len(paths) == 12 and a["turns"] == 1 and not ast.literal_eval(a["tool_names"])
        assert not any(gold in p for p in paths), f"{arm}: gold paper in its context"
        assert j["verdict"] == "incorrect"
        papers = {paper_of(p) for p in paths}
        assert max(len(s["text"]) for s in a["sources"]) <= UNIT_CHARS, f"{arm}: unit over the cap"
        baselines.append({
            "name": NAMES[arm], "retrieval": retrieval, "scope": scope,
            "off_topic": len(papers), "n_units": len(paths),
            "excerpt": " … ".join(slice_between(a["answer"], s, e) for s, e in pieces),
            "verdict": j["verdict"], "overall": overall(j),
        })
    assert len({(b["verdict"], b["overall"]) for b in baselines}) == 1, "lanes share one verdict"

    # The dagger: the BM25 row answered from outside its context (disclosed in E2).
    bm = answers[("bm25", QID)]["answer"]
    assert "From the project corpus" in bm and "not answerable from the provided context" in bm

    board = [{"name": NAMES[a] + ("†" if a == "bm25" else ""), "overall": overall(judged[(a, QID)]),
              "verdict": judged[(a, QID)]["verdict"]} for a in ARMS]
    part = re.search(r"\(part (\d+) of (\d+)\)", read["path"])
    return {
        "qid": QID, "question": hm["question"], "gold": gold,
        "keywords": prov["question"]["gold_keywords"],
        "two": two, "vec": vec, "read": read, "turns": [c["turn"] for c in calls],
        "answer_turn": prov["session"]["turn_of_final_reply"],
        "read_part": f"part {part.group(1)} of {part.group(2)}",
        "queries": [c["input"]["query"] for c in calls[:2]],
        "hm_excerpt": hm_excerpt, "evidence_quote": evidence_quote,
        "hm_verdict": jh["verdict"], "hm_overall": overall(jh),
        "baselines": baselines, "board": board,
    }


# --------------------------------------------------------------------------
# drawing primitives (data units are points; y decreases downwards from 0)
# --------------------------------------------------------------------------
def rpath(x: float, y: float, w: float, h: float, r: float, corners: str) -> MplPath:
    """Rectangle path (lower-left corner) with the listed corners rounded."""
    l, b, rg, t = x, y, x + w, y + h
    lt, rt, rb, lb = (k in corners for k in ("lt", "rt", "rb", "lb"))
    v: list = [(l + r if lt else l, t)]
    c: list = [MplPath.MOVETO]
    v.append((rg - r if rt else rg, t)); c.append(MplPath.LINETO)
    if rt:
        v += [(rg - r + K * r, t), (rg, t - r + K * r), (rg, t - r)]; c += [MplPath.CURVE4] * 3
    v.append((rg, b + r if rb else b)); c.append(MplPath.LINETO)
    if rb:
        v += [(rg, b + r - K * r), (rg - r + K * r, b), (rg - r, b)]; c += [MplPath.CURVE4] * 3
    v.append((l + r if lb else l, b)); c.append(MplPath.LINETO)
    if lb:
        v += [(l + r - K * r, b), (l, b + r - K * r), (l, b + r)]; c += [MplPath.CURVE4] * 3
    v.append((l, t - r if lt else t)); c.append(MplPath.LINETO)
    if lt:
        v += [(l, t - r + K * r), (l + r - K * r, t), (l + r, t)]; c += [MplPath.CURVE4] * 3
    v.append(v[0]); c.append(MplPath.CLOSEPOLY)
    return MplPath(v, c)


class NoDraw:
    """Stand-in for an axes during the measuring pass."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class Canvas:
    def __init__(self) -> None:
        self.fig = plt.figure(dpi=72, figsize=(W / 72, 10.0))
        self.renderer = self.fig.canvas.get_renderer()
        self._width: dict = {}

    def width(self, s: str, size: float = BODY, weight: str = "normal", style: str = "normal") -> float:
        key = (s, size, weight, style)
        if key not in self._width:
            t = self.fig.text(0, 0, s, fontsize=size, fontweight=weight, fontstyle=style)
            self._width[key] = t.get_window_extent(renderer=self.renderer).width   # 72 dpi: px == pt
            t.remove()
        return self._width[key]


class Fig:
    def __init__(self, ax, canvas: Canvas) -> None:
        self.ax, self.cv = ax, canvas

    def width(self, s, size=BODY, weight="normal", style="normal"):
        return self.cv.width(s, size, weight, style)

    def wrap(self, s: str, max_w: float, size: float = BODY, weight: str = "normal",
             style: str = "normal") -> list[str]:
        """Word wrap, then the narrowest lines that keep the greedy line count."""
        words = s.split(" ")

        def lines(limit: float) -> list[str]:
            out, cur = [], ""
            for wd in words:
                trial = f"{cur} {wd}" if cur else wd
                if cur and self.width(trial, size, weight, style) > limit:
                    out.append(cur)
                    cur = wd
                else:
                    cur = trial
            return out + [cur]

        greedy = lines(max_w)
        if len(greedy) < 2:
            return greedy
        lo, hi = 0.0, float(max_w)
        for _ in range(18):
            mid = (lo + hi) / 2
            if len(lines(mid)) > len(greedy):
                lo = mid
            else:
                hi = mid
        return lines(hi)

    def text(self, x, y, s, size=BODY, color=INK, weight="normal", style="normal",
             ha="left", z=5) -> None:
        self.ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                     fontstyle=style, ha=ha, va="center", zorder=z)

    def patch(self, x, y, w, h, face, edge, lw, corners, z, r=RADIUS, dashed=False) -> None:
        self.ax.add_patch(PathPatch(
            rpath(x, y, w, h, r, corners), facecolor=face, edgecolor=edge, linewidth=lw,
            zorder=z, linestyle=(0, (4.2, 3.0)) if dashed else "solid",
            capstyle="round", joinstyle="round"))

    def fill(self, x, y, w, h, color, corners="lt rt rb lb", z=1, r=RADIUS) -> None:
        self.patch(x, y, w, h, color, color, 0, corners, z, r)

    def outline(self, x, y, w, h, edge, lw=0.9, corners="lt rt rb lb", z=3, dashed=False) -> None:
        self.patch(x, y, w, h, "none", edge, lw, corners, z, dashed=dashed)

    def rule(self, x1, x2, y) -> None:
        self.ax.plot([x1, x2], [y, y], color=GRID, linewidth=0.55, zorder=2, solid_capstyle="round")

    def tag_width(self, s: str) -> float:
        return self.width(s, BODY, "bold") + 2 * TAG_PAD

    def tag(self, x_right, yc, s, color) -> None:
        w, h = self.tag_width(s), 8.2
        self.fill(x_right - w, yc - h / 2, w, h, color, z=4, r=1.3)
        self.text(x_right - w / 2, yc, s, BODY, WHITE, "bold", ha="center", z=6)

    def strip(self, x, y_top, w, left, color, right=None, tag=None) -> None:
        """Coloured title strip: bold white title, optional tag and right note."""
        yc = y_top - STRIP_H / 2
        self.fill(x, y_top - STRIP_H, w, STRIP_H, color, corners="lt rt", z=1.5)
        self.text(x + PAD_X, yc, left, BODY, WHITE, "bold", z=6)
        used = PAD_X + self.width(left, BODY, "bold")
        cursor = x + w - PAD_X
        if tag:
            self.tag(cursor, yc, tag[0], tag[1])
            cursor -= self.tag_width(tag[0]) + TAG_GAP
            used += self.tag_width(tag[0]) + TAG_GAP
        if right:
            self.text(cursor, yc, right, BODY, WHITE, ha="right", z=6)
            used += self.width(right) + TAG_GAP
        assert used <= w - PAD_X, f"title strip overflow: {left!r} / {right!r}"

    def arrow(self, x, y_from, y_to, color) -> None:
        self.ax.annotate("", xy=(x, y_to), xytext=(x, y_from), zorder=6, arrowprops={
            "arrowstyle": "-|>", "mutation_scale": 7.0, "linewidth": 0.9,
            "color": color, "shrinkA": 0, "shrinkB": 0})


class Rows:
    """Label / value rows; a tag sits at the right end of the row's first line."""

    def __init__(self, rows, label_w: float = LABEL_W) -> None:
        self.rows, self.label_w = rows, label_w

    def plan(self, f: Fig, w: float):
        vw = w - 2 * PAD_X - self.label_w
        plan, height = [], 2 * PAD
        for n, (label, value, *rest) in enumerate(self.rows):
            opts = rest[0] if rest else {}
            weight = "bold" if opts.get("bold") else "normal"
            style = "italic" if opts.get("italic") else "normal"
            assert not label or f.width(label, BODY, weight, style) <= self.label_w - 4, f"label too wide: {label!r}"
            avail = vw - (f.tag_width(opts["tag"][0]) + TAG_GAP if opts.get("tag") else 0)
            lines = f.wrap(value, avail)
            sep = SEP if opts.get("sep_after") and n < len(self.rows) - 1 else 0
            plan.append((label, lines, opts))
            height += len(lines) * LH + sep
        return plan, height

    def draw(self, f: Fig, x, y_top, w: float) -> None:
        plan, _ = self.plan(f, w)
        y = y_top - PAD
        for n, (label, lines, opts) in enumerate(plan):
            if opts.get("tag"):
                f.tag(x + w - PAD_X, y - LH / 2, opts["tag"][0], opts["tag"][1])
            if label:
                f.text(x + PAD_X, y - LH / 2, label, BODY, opts.get("color", SLATE),
                       "bold" if opts.get("bold") else "normal",
                       "italic" if opts.get("italic") else "normal")
            for k, ln in enumerate(lines):
                f.text(x + PAD_X + self.label_w, y - LH / 2 - k * LH, ln)
            y -= len(lines) * LH
            if opts.get("sep_after") and n < len(plan) - 1:
                f.rule(x + PAD_X, x + w - PAD_X, y - SEP / 2)
                y -= SEP


class Quote:
    def __init__(self, text: str) -> None:
        self.text = text

    def plan(self, f: Fig, w: float):
        lines = f.wrap(self.text, w - 2 * PAD_X)
        return lines, 2 * PAD + len(lines) * LH

    def draw(self, f: Fig, x, y_top, w: float) -> None:
        lines, _ = self.plan(f, w)
        for k, ln in enumerate(lines):
            f.text(x + PAD_X, y_top - PAD - LH / 2 - k * LH, ln)


def card(f: Fig, x, y_top, w, left, accent, face, body, right=None, tag=None) -> float:
    """Title strip over a body; returns the card height."""
    _, extra = body.plan(f, w)
    h = STRIP_H + extra
    f.fill(x, y_top - h, w, h, face)
    f.strip(x, y_top, w, left, accent, right, tag)
    body.draw(f, x, y_top - STRIP_H, w)
    f.outline(x, y_top - h, w, h, accent)
    return h


def document_icon(f: Fig, x, y_top) -> None:
    w, h = 9.4, 13.6
    f.fill(x, y_top - h, w, h, WHITE, z=5, r=1.4)
    f.outline(x, y_top - h, w, h, ICON, lw=0.9, z=6)
    f.ax.add_patch(Polygon([[x + w * 0.65, y_top], [x + w, y_top - h * 0.35],
                            [x + w * 0.65, y_top - h * 0.35]], closed=True,
                           facecolor=PALE_BLUE, edgecolor=ICON, linewidth=0.65, zorder=7))
    for frac in (0.40, 0.27, 0.14):
        f.ax.plot([x + w * 0.18, x + w * 0.80], [y_top - h * frac] * 2,
                  color=ICON, linewidth=0.55, zorder=7)


def question_card(f: Fig, x, y_top, w, case) -> float:
    h = 3.6 + LH + 2 * LH_Q + 5.0 + LH + 3.6
    f.fill(x, y_top - h, w, h, CARD, z=1)
    f.outline(x, y_top - h, w, h, INK, lw=0.8)
    document_icon(f, x + 4.4, y_top - 5.0)
    tx = x + PAD_X + 15.6
    tw = x + w - PAD_X - tx
    y = y_top - 3.6 - LH / 2
    meta = f"E2 blind comparison · {case['qid']}"
    assert f.width(meta, BODY, style="italic") <= tw
    f.text(tx, y, meta, BODY, SLATE, style="italic")
    qlines = f.wrap("Q: " + case["question"], tw, QPT, "bold")
    assert len(qlines) == 2, qlines
    for k, ln in enumerate(qlines):
        f.text(tx, y - LH / 2 - LH_Q / 2 - k * LH_Q, ln, QPT, INK, "bold")
    yq = y - LH / 2 - 2 * LH_Q
    f.rule(tx, x + w - PAD_X, yq - 2.4)
    target = (f"gold paper arXiv {case['gold']} · target "
              + " · ".join(f"“{shown_keyword(k)}”" for k in case["keywords"]))
    assert f.width(target, BODY, "bold") <= tw
    f.text(tx, yq - 5.0 - LH / 2 + 0.4, target, BODY, OCHRE, "bold")
    return h


def panel(f: Fig, x, y_top, w, title, note, content) -> float:
    assert f.width(title, TITLE, "bold") + f.width(note, BODY, style="italic") + 12 <= w - 2 * PAD_P, title
    f.text(x + PAD_P, y_top - TITLE_H / 2 + 0.5, title, TITLE, INK, "bold", z=6)
    f.text(x + w - PAD_P, y_top - TITLE_H / 2 + 0.3, note, BODY, SLATE, style="italic", ha="right", z=6)
    inner = content(f, x + PAD_P, y_top - TITLE_H, w - 2 * PAD_P)
    h = TITLE_H + inner + PAD_P
    f.outline(x, y_top - h, w, h, INK, lw=0.85, z=0.8, dashed=True)
    return h


def hmrs_flow(f: Fig, x, y_top, w, case) -> float:
    two, vec, read = case["two"], case["vec"], case["read"]
    t1, t2, t3 = case["turns"][0], case["turns"][2], case["answer_turn"]
    y, cx = y_top, x + w / 2

    def down(y_bottom: float) -> float:
        """Flow arrow across the gap below a card; returns the next card top."""
        f.arrow(cx, y_bottom, y_bottom - GAP, BLUE)
        return y_bottom - GAP

    h = card(f, x, y, w, f"turn {t1} · kb_search_two_stage", BLUE, PALE_BLUE, Rows([
        ("query", f"“{case['queries'][0]}”"),
        ("stage 1", f"documents: gold paper ranked 1st of {two['stage1_candidates']}"
                    f" ({two['stage1_gold_score']:.1f})"),
        ("stage 2", f"chunks: all {two['stage2_gold_results']} from the gold paper "
                    f"({two['stage2_score_min']:.2f}–{two['stage2_score_max']:.2f})"),
    ]))
    y -= h
    # Both searches were issued in one turn: a link without an arrowhead.
    f.ax.plot([cx, cx], [y, y - GAP], color=BLUE, linewidth=0.9, zorder=6)
    f.text(x + w - PAD_X, y - GAP / 2, "in parallel", BODY, SLATE, style="italic", ha="right", z=8)
    y -= GAP
    h = card(f, x, y, w, f"turn {t1} · kb_search_vector", BLUE, PALE_BLUE, Rows([
        ("query", f"“{case['queries'][1]}”"),
        ("top hits", f"top {vec['gold_results']} of {vec['results']} are gold-paper chunks"
                     f" ({vec['top_score']:.2f})"),
    ]))
    y = down(y - h)
    h = card(f, x, y, w, f"turn {t2} · kb_doc_read", BLUE, EVIDENCE, Rows([
        ("document", f"gold paper · {case['read_part']}"),
        ("returned", f"first {read['returned_chars']:,} characters"),
        ("abstract", f"“{case['evidence_quote']}”"),
    ]), tag=("HIT", GREEN))
    y = down(y - h)
    h = card(f, x, y, w, f"turn {t3} · ANSWER · verbatim excerpt", VERDICT_COLOR[case["hm_verdict"]],
             PALE_GREEN, Quote(f"“{case['hm_excerpt']}”"),
             right=f"{case['hm_verdict'].upper()} · {case['hm_overall']:.2f}")
    return y_top - (y - h)


def baseline_flow(f: Fig, x, y_top, w, case) -> float:
    lanes, y, cx = case["baselines"], y_top, x + w / 2
    last = len(lanes) - 1
    n_units = {b["n_units"] for b in lanes}
    assert len(n_units) == 1, "lanes share one context budget"
    rows = []
    for n, b in enumerate(lanes):
        rows.append((b["name"], b["retrieval"], {"bold": True, "color": INK}))
        rows.append((b["scope"], f"{b['off_topic']} off-topic papers; gold paper absent",
                     {"italic": True, "tag": ("MISS", BRICK), "sep_after": n < last}))
    h = card(f, x, y, w, "RETRIEVAL · one query", OCHRE, PALE_OCHRE, Rows(rows, LANE_W),
             right=f"{n_units.pop()} units × ≤{UNIT_CHARS} characters")
    f.arrow(cx, y - h, y - h - GAP, OCHRE)
    y = y - h - GAP
    v = lanes[0]
    h = card(f, x, y, w, "ANSWERS · verbatim excerpts", VERDICT_COLOR[v["verdict"]], PALE_BRICK,
             Rows([(b["name"], f"“{b['excerpt']}”",
                    {"bold": True, "color": INK, "sep_after": n < last}) for n, b in enumerate(lanes)], LANE_W),
             right=f"{v['verdict'].upper()} · {v['overall']:.2f} each")
    return y_top - (y - h)


def footer(f: Fig, x, y_top, w, case) -> float:
    """Every arm's score on this question, so that the two lanes above are not
    read as the overall result. Verdict colours as in the answer strips."""
    gap = 3.0
    head = "Eight arms, overall score:"
    dot = ("·", SLATE, "normal", "normal")
    lines, cur, n_pairs = [], [(head, SLATE, "bold", "normal")], 0
    cur_w = f.width(head, BODY, "bold")
    for b in case["board"]:
        pair = (f"{b['name']} {b['overall']:.2f}", VERDICT_COLOR[b["verdict"]], "bold", "normal")
        pw = f.width(pair[0], BODY, "bold")
        # No dot right after the head; a wider gap stands in for it.
        lead = 2 * gap if n_pairs == 0 else 2 * gap + f.width("·") + gap
        if n_pairs and cur_w + lead + pw > w:
            lines.append(cur)
            cur, cur_w, n_pairs = [pair], pw, 1
        else:
            if n_pairs:
                cur.append(dot)
            cur.append(pair)
            cur_w += lead + pw
            n_pairs += 1
    lines.append(cur)
    y = y_top - LH / 2
    for ln in lines:
        px = x
        for text, color, weight, style in ln:
            f.text(px, y, text, BODY, color, weight, style)
            px += f.width(text, BODY, weight, style) + gap
        y -= LH
    note = ("† BM25 answered from repository content outside its twelve passages (retained in E2). "
            "HIT/MISS: gold paper present/absent in the evidence. “…” marks omitted words.")
    y -= 1.2
    for ln in f.wrap(note, w, BODY, style="italic"):
        f.text(x, y - LH / 2, ln, BODY, SLATE, style="italic")
        y -= LH
    return y_top - y


def rail(f: Fig, q_top, q_h, a_top, b_top) -> None:
    """One question, two procedures: a shared rail with a branch into each panel."""
    y0 = q_top - q_h * 0.76
    f.ax.plot([X0, SPINE_X, SPINE_X], [y0, y0, b_top - TITLE_H / 2], color=NAVY, linewidth=0.9,
              zorder=4, solid_joinstyle="round")
    for top in (a_top, b_top):
        y = top - TITLE_H / 2
        f.ax.add_patch(Circle((SPINE_X, y), 2.0, facecolor=WHITE, edgecolor=NAVY,
                              linewidth=0.9, zorder=6))
        f.ax.annotate("", xy=(X0 - 0.3, y), xytext=(SPINE_X + 2.0, y), zorder=6, arrowprops={
            "arrowstyle": "-|>", "mutation_scale": 6.0, "linewidth": 0.9,
            "color": NAVY, "shrinkA": 0, "shrinkB": 0})


def draw(f: Fig, case) -> float:
    y = -MARGIN
    q_top, q_h = y, question_card(f, X0, y, CW, case)
    y -= q_h + GAP_PANEL
    a_top = y
    y -= panel(f, X0, y, CW, "(a)  HMRS agent · recorded tool calls", "agent loop",
               lambda fx, px, py, pw: hmrs_flow(fx, px, py, pw, case))
    y -= GAP_PANEL
    b_top = y
    y -= panel(f, X0, y, CW, "(b)  One-shot baselines · no tools", "one prompt each",
               lambda fx, px, py, pw: baseline_flow(fx, px, py, pw, case))
    y -= GAP_FOOT
    y -= footer(f, X0, y, CW, case)
    y -= MARGIN
    rail(f, q_top, q_h, a_top, b_top)
    return y


def assert_texts_apart(fig, ax, tol: float = 0.3) -> None:
    """Guards the hand layout: no two labels overlap and none leaves the page."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [(t.get_text(), t.get_window_extent(r)) for t in ax.texts]
    w_px, h_px = fig.canvas.get_width_height()
    for s, b in boxes:
        assert b.x0 >= -tol and b.x1 <= w_px + tol and b.y0 >= -tol and b.y1 <= h_px + tol, f"leaves the page: {s!r}"
    for i, (s1, a) in enumerate(boxes):
        for s2, b in boxes[i + 1:]:
            apart = (a.x1 - tol <= b.x0 + tol or b.x1 - tol <= a.x0 + tol
                     or a.y1 - tol <= b.y0 + tol or b.y1 - tol <= a.y0 + tol)
            assert apart, f"labels overlap: {s1!r} / {s2!r}"


def main() -> None:
    case = load_case()
    cv = Canvas()
    bottom = draw(Fig(NoDraw(), cv), case)          # measuring pass: no artist is created
    ax = cv.fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(bottom, 0)
    ax.axis("off")
    draw(Fig(ax, cv), case)
    cv.fig.set_size_inches(W / 72, -bottom / 72)
    assert_texts_apart(cv.fig, ax)

    FIG.mkdir(parents=True, exist_ok=True)
    cv.fig.savefig(FIG / "fig_hmrs_vs_baseline.pdf", format="pdf", facecolor=WHITE)
    cv.fig.savefig(FIG / "fig_hmrs_vs_baseline.png", dpi=300, format="png", facecolor=WHITE)
    plt.close(cv.fig)
    print(f"wrote {FIG / 'fig_hmrs_vs_baseline.pdf'} and .png "
          f"({W:.0f} x {-bottom:.1f} pt = {W / 72:.2f} x {-bottom / 72:.2f} in)")


if __name__ == "__main__":
    main()
