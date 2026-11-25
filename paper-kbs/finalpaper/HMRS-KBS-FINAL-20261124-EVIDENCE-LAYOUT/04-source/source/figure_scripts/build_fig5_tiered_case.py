#!/usr/bin/env python3
"""Build the single-column Figure 5 from the bundled BQ07 trace (no live calls).

Run with Python and Matplotlib: python figure_scripts/build_fig5_tiered_case.py
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
from matplotlib.text import Text

SOURCE = Path(__file__).resolve().parents[1]
DATA = SOURCE / "experiment_data" / "tiered_case"
OUTPUT = SOURCE / "figs" / "fig5_tiered_case.pdf"
WIDTH, HEIGHT = 252, 406  # PDF points, not a scaled-down multi-column layout.
INK, MUTED = "#142A3C", "#40576A"
BLUE, TEAL, OCHRE = "#285475", "#1B625A", "#795014"
PALE_BLUE, PALE_TEAL, PALE_OCHRE = "#F0F5F9", "#EAF5F2", "#FAF3E5"
LINE, WHITE = "#B3C3CE", "#FFFFFF"
BODY, TITLE, META = 8.4, 10.2, 8.0
PART = re.compile(r"__(\d{4}\.\d{4,5})__.*\(part (\d+) of (\d+)\)\.md$")


@dataclass(frozen=True)
class Case:
    qid: str
    question: str
    collections: int
    selected_shelf: str
    shelf_total: int
    pages: tuple[int, ...]
    page_count: int
    per_page: int
    shortlist_page: int
    shortlist_turn: int
    paper_id: str
    parts: tuple[int, ...]
    part_count: int
    gate_engine: str
    scored: int
    passed: int
    threshold: float
    read_part: int
    first_line: int
    last_line: int
    evidence_quote: str
    model_type: str
    base_model: str
    answer_turn: int


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(f"Inconsistent BQ07 evidence: {detail}")


def part_of(path: str) -> tuple[str, int, int]:
    match = PART.search(path)
    if match is None:
        raise ValueError(f"Missing paper/part identifier: {path!r}")
    return match[1], int(match[2]), int(match[3])


def load_case(data: Path) -> Case:
    run = json.loads((data / "tiered-bq07.json").read_text(encoding="utf-8"))
    trace = json.loads((data / "trace-evidence.json").read_text(encoding="utf-8"))
    turns = trace["turns"]
    names = ["kb_list", *["kb_get_documents"] * 3, *["kb_laya_judge"] * 2, "kb_doc_read"]
    require(run["qid"] == trace["run"]["qid"] == "BQ07"
            and run["session_id"] == trace["run"]["session_id"], "session identity")
    require([t["name"] for t in turns] == names, "tiered tool sequence")
    for number, (turn, call) in enumerate(zip(turns, run["calls"], strict=True), 1):
        require(turn["turn"] == call["turn"] == number and turn["name"] == call["name"]
                and turn["args"] == json.loads(call["input"]["content"]), f"turn {number}")
    require(run["answer_turn"] == len(turns) + 1, "answer turn")

    catalogue = turns[0]["result"]
    shelf_calls = turns[1:4]
    shelf = [t["result"] for t in shelf_calls]
    selected, = catalogue["catalog"]  # Only the selected collection is bundled.
    kb_id = selected["kb_id"]
    total, page_count, page_size = (shelf[0][k] for k in ("total", "page_count", "page_size"))
    require(catalogue["success"] and total == selected["doc_count"], "catalogue selection")
    for call, page in zip(shelf_calls, shelf, strict=True):
        require(call["args"]["lightweight"] and page["success"] and page["view"] == "docs"
                and call["args"]["kb_id"] == page["kb_id"] == kb_id
                and (page["total"], page["page_count"], page["page_size"]) == (total, page_count, page_size)
                and page["count"] == page_size, "description shelf")
    pages = tuple(page["page"] for page in shelf)
    require(pages == tuple(range(1, len(shelf) + 1)) and pages[-1] < page_count
            and shelf[-1]["has_more"], "partial shelf browse")

    retry, gate_call, read_call = turns[4:]
    gate, read = gate_call["result"], read_call["result"]
    refs = gate_call["args"]["documents"]
    require("Validation failed" in retry["result"] and retry["args"]["refs"] == refs
            and retry["args"]["question"] == gate_call["args"]["query"] == run["question"], "gate retry")
    require(all(ref["kb_id"] == kb_id for ref in refs), "gate scope")
    cards = {c["doc_id"]: (p["page"], c) for p in shelf for c in p.get("catalog", [])}
    ref_ids = {r["doc_id"] for r in refs}
    require(set(cards) == ref_ids and all(c["description"] for _, c in cards.values()), "shortlisted cards")
    shortlist_page, = {p for p, _ in cards.values()}
    shortlist_turn, = (t["turn"] for t in shelf_calls if t["result"]["page"] == shortlist_page)
    part_refs = [part_of(cards[ref["doc_id"]][1]["doc_path"]) for ref in refs]
    paper_id, = {p[0] for p in part_refs}
    part_count, = {p[2] for p in part_refs}
    parts = tuple(p[1] for p in part_refs)

    survivors = gate["survivors"]
    require(gate["status"] == "ok" and gate["real_engine"] is True and gate["engine"] == "laya"
            and gate["criterion"] == gate_call["args"]["criterion"] == "evidence"
            and gate["scored_count"] == gate["candidate_count"] >= len(survivors) == gate["survivor_count"]
            and all(s["score"] >= gate["threshold"] for s in survivors), "bounded segment verdict")
    # The compact docs_with_yes groups paths (null in this ID-based run), not IDs.
    survivors_by_id = {s["doc_id"] for s in survivors}
    read_args = read_call["args"]
    require(read["success"] and read_args["kb_id"] == kb_id
            and read_args["doc_id"] in survivors_by_id <= ref_ids
            and read["path"] == cards[read_args["doc_id"]][1]["doc_path"], "source recheck")
    first = read_args["offset"]
    returned = read["returned_line_count"]
    require(returned == read_args["limit"] and read["truncated"], "read window")

    abstract = read["abstract"]
    definition = re.search(r"the first (open-source \d+B-parameter language model) built specifically for (\w+)\.", abstract)
    base = re.search(r"continue pretraining (.+?) to obtain", abstract)
    require(definition is not None and base is not None, "abstract excerpts")
    assert definition is not None and base is not None  # narrow the match types
    answer = run["answer"].replace("**", "")
    require(definition[0] in answer and base[1] in answer, "answer grounded in read excerpt")

    return Case(run["qid"], run["question"], catalogue["count"], selected["description"].split(":", 1)[0],
                total, pages, page_count, page_size, shortlist_page, shortlist_turn, paper_id, parts, part_count,
                gate["engine"].title(), gate["scored_count"], gate["survivor_count"], gate["threshold"],
                part_of(read["path"])[1], first, first + returned - 1, definition[0],
                f"{definition[1].replace('-parameter', '')} for {definition[2]}",
                base[1], run["answer_turn"])


class Diagram:
    def __init__(self, ax: Axes) -> None:
        self.ax = ax
        self.labels: list[tuple[Text, tuple[float, float, float, float]]] = []

    def box(self, x: float, y: float, w: float, h: float, face: str, edge: str = "none",
            radius: float = 3, z: int = 2) -> None:
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                        facecolor=face, edgecolor=edge, linewidth=0.7, zorder=z))

    def line(self, points: list[tuple[float, float]], color: str, lw: float = 0.85, z: int = 4) -> None:
        self.ax.plot(*zip(*points), color=color, linewidth=lw, zorder=z, solid_capstyle="round",
                     solid_joinstyle="round")

    def text(self, x: float, y: float, s: str, *, size: float = BODY, color: str = INK,
             weight: str = "normal", style: str = "normal", align: str = "left",
             span: tuple[float, float] = (40, 238)) -> None:
        artist = self.ax.text(x, y, s, fontsize=size, color=color, weight=weight, style=style,
                              ha=align, va="center", zorder=5, parse_math=False)
        self.labels.append((artist, (*span, 3, HEIGHT - 3)))

    def wrapped(self, x: float, y: float, value: str, *, size: float = BODY, color: str = INK,
                style: str = "normal", weight: str = "normal", right: float = 238,
                leading: float = 10.5, max_lines: int = 2) -> None:
        renderer = self.ax.figure.canvas.get_renderer()

        def width(s: str) -> float:
            probe = Text(text=s, fontsize=size, weight=weight, style=style, parse_math=False)
            probe.set_figure(self.ax.figure)
            return probe.get_window_extent(renderer).width * 72 / self.ax.figure.dpi

        lines: list[str] = []
        line = ""
        for word in value.split():
            trial = f"{line} {word}" if line else word
            if line and width(trial) > right - x - 1:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        if len(lines) > max_lines:
            raise ValueError(f"Figure copy requires too many lines: {value!r}")
        for i, line in enumerate(lines):
            self.text(x, y + leading * i, line, size=size, color=color, weight=weight, style=style,
                      span=(x - 1, right))

    def icon(self, y: float, kind: str, color: str) -> None:
        x = 17
        self.ax.add_patch(Circle((x, y), 9.6, facecolor=WHITE, edgecolor=color, linewidth=0.9, zorder=3))
        strokes = {
            "catalogue": [[(-6, 4), (-6, -4), (-1, -4), (0, -2), (6, -2), (6, 4), (-6, 4)],
                          [(-3, 1), (3, 1)]],
            "shelf": [[(-6, 5), (6, 5)], [(-5, 3), (-5, -4), (-2, -4), (-2, 3), (-5, 3)],
                      [(0, 3), (0, -5), (2, -5), (2, 3), (0, 3)], [(3, -4), (5, 3)]],
            "cards": [[(-5, 4), (-5, -3), (3, -3), (3, 4), (-5, 4)],
                      [(-2, -5), (5, -5), (5, 2)], [(-3, -1), (1, -1)], [(-3, 1), (1, 1)]],
            "gate": [[(-6, -4), (6, -4), (2, 1), (2, 4), (-2, 5), (-2, 1), (-6, -4)]],
            "read": [[(0, -3), (-3, -4.5), (-6, -4), (-6, 3.5), (-3, 3), (0, 5),
                      (3, 3), (6, 3.5), (6, -4), (3, -4.5), (0, -3), (0, 5)]],
            "answer": [[(-5, -4), (5, -4), (5, 2.5), (-1, 2.5), (-4, 5), (-4, 2.5),
                        (-5, 2.5), (-5, -4)], [(-2.5, -1), (2.5, -1)]],
        }
        for stroke in strokes[kind]:
            self.line([(x + dx, y + dy) for dx, dy in stroke], color)

    def stage(self, y: float, h: float, label: str, turn: str, icon: str, color: str = BLUE,
              face: str = PALE_BLUE) -> None:
        self.box(32, y, 214, h, face, LINE)
        self.icon(y + 12, icon, color)
        self.text(40, y + 12, label, size=TITLE, color=color, weight="bold")
        self.text(238, y + 12, turn, size=META, color=MUTED, align="right")

    def check_text(self) -> None:
        canvas = self.ax.figure.canvas
        canvas.draw()
        renderer = canvas.get_renderer()
        placed = []
        for artist, (left, right, top, bottom) in self.labels:
            bounds = artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if not (left - 0.6 <= bounds.xmin <= bounds.xmax <= right + 0.6
                    and top <= bounds.ymin <= bounds.ymax <= bottom):
                raise ValueError(f"Text outside its clear area: {artist.get_text()!r}")
            for prior, prev in placed:
                if min(prev.xmax, bounds.xmax) - max(prev.xmin, bounds.xmin) > 0.2 and (
                    min(prev.ymax, bounds.ymax) - max(prev.ymin, bounds.ymin) > 0.2
                ):
                    raise ValueError(f"Overlapping text: {prior!r} and {artist.get_text()!r}")
            placed.append((artist.get_text(), bounds))


def draw(ax: Axes, c: Case) -> None:
    f = Diagram(ax)
    f.box(6, 6, 240, 47, INK)
    f.text(14, 18, "Tiered retrieval in practice", size=11.1, color=WHITE, weight="bold", span=(13, 239))
    f.text(238, 18, c.qid, size=8.7, color=WHITE, weight="bold", align="right", span=(13, 239))
    f.wrapped(14, 31, c.question, size=9.1, color=WHITE, right=200, leading=11)

    # The rail links successive stages, not parallel arms or ranked items.
    for begin, end in zip((53, 72, 120, 168, 223, 288), (72, 120, 168, 223, 288, 354), strict=True):
        f.line([(17, begin), (17, end - 11)], BLUE, 0.85, 1)
        ax.add_patch(Polygon([(14.7, end - 14), (19.3, end - 14), (17, end - 10)],
                             facecolor=BLUE, edgecolor="none", zorder=1))

    f.stage(60, 42, "Catalogue", "TURN 1", "catalogue")
    f.text(40, 85, f"{c.collections} collections returned by the catalogue.")
    f.text(40, 95.5, f"Selected {c.selected_shelf}.", weight="bold")

    f.stage(108, 42, "Shelf", "TURNS 2–4", "shelf")
    f.text(40, 133, f"{c.shelf_total} entries; pages {c.pages[0]}–{c.pages[-1]} of {c.page_count} fetched.")
    f.text(40, 143.5, f"{c.per_page} entries reported per page.")

    f.stage(156, 49, "Document descriptions", f"TURN {c.shortlist_turn}", "cards")
    f.text(40, 181, f"Shortlist from page {c.shortlist_page} · arXiv:{c.paper_id}")
    for index, part in enumerate(c.parts):
        x = 40 + index * 54
        f.box(x, 189, 48, 12, WHITE, LINE, radius=1.5, z=3)
        ax.add_patch(Rectangle((x + 3.3, 191.9), 4.5, 6.1, facecolor="none", edgecolor=BLUE,
                               linewidth=0.65, zorder=4))
        f.line([(x + 4.4, 194), (x + 6.7, 194)], BLUE, 0.55)
        f.line([(x + 4.4, 196), (x + 6.7, 196)], BLUE, 0.55)
        f.text(x + 11, 195, f"Part {part}", size=META, color=BLUE, weight="bold")

    f.stage(211, 59, f"Bounded {c.gate_engine} gate", "TURNS 5–6", "gate", OCHRE, PALE_OCHRE)
    f.text(40, 236, "Turn 5 failed argument validation; retried.")
    f.text(40, 249, f"{c.scored} segments scored → {c.passed} passed", size=9.3, weight="bold", color=OCHRE)
    f.text(40, 261.5, f"Pass if score ≥ {c.threshold:.2f} · filter, not ranker.")

    f.stage(276, 60, "Read and recheck", "TURN 7", "read", TEAL, PALE_TEAL)
    f.text(40, 301, f"Part {c.read_part} of {c.part_count} · requested lines {c.first_line}–{c.last_line}")
    f.text(238, 301, "Abstract", size=META, color=TEAL, align="right")
    f.line([(41, 310), (41, 330)], TEAL, 1.05)
    f.wrapped(46, 314.5, f"“{c.evidence_quote}”", size=8.2, style="italic", color=TEAL)

    f.stage(342, 45, "Answer", f"TURN {c.answer_turn}", "answer", TEAL, PALE_TEAL)
    f.text(88, 354, "English paraphrase", size=META, color=MUTED)
    f.text(40, 366, f"An {c.model_type}.")
    f.text(40, 377, f"Continued pretraining of {c.base_model}.")
    f.text(7, 398, "Illustrative run only · not in E2 or E3 aggregates", size=8.2, color=MUTED,
           span=(6, 246))
    f.check_text()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT, help="PDF destination (default: source/figs)")
    args = parser.parse_args()
    case = load_case(DATA)
    with rc_context({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "savefig.bbox": None}):
        fig = Figure(figsize=(WIDTH / 72, HEIGHT / 72), dpi=144, facecolor=WHITE)
        FigureCanvasAgg(fig)
        ax = fig.add_axes((0, 0, 1, 1), xlim=(0, WIDTH), ylim=(HEIGHT, 0))
        ax.set_axis_off()
        draw(ax, case)
        fig.savefig(args.output, format="pdf", metadata={"CreationDate": None, "ModDate": None,
                                                           "Title": f"{case.qid} tiered retrieval trace"})
    print(f"Wrote {args.output} ({WIDTH} × {HEIGHT} pt)")


if __name__ == "__main__":
    main()
