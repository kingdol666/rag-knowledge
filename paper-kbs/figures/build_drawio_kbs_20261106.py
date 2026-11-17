#!/usr/bin/env python3
"""Create native, editable Draw.io figures for the HMRS KBS manuscript."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from xml.etree import ElementTree as ET


HERE = Path(__file__).resolve().parent
OUT = HERE / "kbs_revision_20261106"
WIDTH = 1320

INK = "#20262E"
SUB = "#46515C"
BLUE = "#0072B2"
GREEN = "#009E73"
AMBER = "#E69F00"
VERM = "#D55E00"
PURPLE = "#7A5C93"
GREY = "#68737D"
PALE_BLUE = "#E8F1F8"
PALE_GREEN = "#EAF4EF"
PALE_AMBER = "#FBF2DF"
PALE_RED = "#FAECE8"
PALE_PURPLE = "#F2EDF5"
PALE_GREY = "#F3F5F6"
LINE = "#53606B"


class Diagram:
    def __init__(self, name: str, height: int):
        self.name = name
        self.height = height
        self.root = ET.Element("mxfile", {
            "host": "app.diagrams.net",
            "modified": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "agent": "Codex",
            "version": "24.7.17",
            "type": "device",
        })
        self.diagram = ET.SubElement(self.root, "diagram", {
            "id": name.lower().replace(" ", "-"), "name": name,
        })
        self.model = ET.SubElement(self.diagram, "mxGraphModel", {
            "dx": str(WIDTH), "dy": str(height), "grid": "1", "gridSize": "10",
            "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
            "fold": "1", "page": "1", "pageScale": "1", "pageWidth": str(WIDTH),
            "pageHeight": str(height), "math": "0", "shadow": "0",
        })
        self.cells = ET.SubElement(self.model, "root")
        ET.SubElement(self.cells, "mxCell", {"id": "0"})
        ET.SubElement(self.cells, "mxCell", {"id": "1", "parent": "0"})
        self.next_id = 2

    def vertex(self, cell_id: str, value: str, x: int, y: int, w: int, h: int,
               style: str, parent: str = "1"):
        cell = ET.SubElement(self.cells, "mxCell", {
            "id": cell_id, "value": value, "style": style,
            "vertex": "1", "parent": parent,
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(w), "height": str(h),
            "as": "geometry",
        })
        return cell_id

    def shape(self, cell_id: str, value: str, x: int, y: int, w: int, h: int,
              fill: str, stroke: str, *, size: int = 20, bold: bool = False,
              radius: bool = True, align: str = "center", dashed: bool = False,
              italic: bool = False, color: str = INK, stroke_width: float = 1.4):
        shape = "rounded=1;arcSize=12" if radius else "rounded=0"
        style = (
            f"{shape};whiteSpace=wrap;html=1;align={align};verticalAlign=middle;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth={stroke_width};"
            f"fontColor={color};fontSize={size};fontFamily=Arial;"
            f"fontStyle={(1 if bold else 0) + (2 if italic else 0)};"
            f"spacing=8;"
        )
        if dashed:
            style += "dashed=1;dashPattern=5 4;"
        return self.vertex(cell_id, value, x, y, w, h, style)

    def text(self, cell_id: str, value: str, x: int, y: int, w: int, h: int,
             *, size: int = 19, bold: bool = False, align: str = "left",
             color: str = INK, italic: bool = False):
        style = (
            "text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;"
            f"align={align};verticalAlign=middle;fontColor={color};fontSize={size};"
            f"fontFamily=Arial;fontStyle={(1 if bold else 0) + (2 if italic else 0)};"
            "spacing=2;"
        )
        return self.vertex(cell_id, value, x, y, w, h, style)

    def panel(self, cell_id: str, x: int, y: int, w: int, h: int,
              fill: str = "#FFFFFF", stroke: str = "#D5DDE5"):
        style = (
            "rounded=1;arcSize=8;whiteSpace=wrap;html=1;" 
            f"fillColor={fill};strokeColor={stroke};strokeWidth=1.0;"
        )
        return self.vertex(cell_id, "", x, y, w, h, style)

    def edge(self, cell_id: str, source: str, target: str, *, color: str = LINE,
             label: str = "", dashed: bool = False, width: float = 1.6,
             exit_x: str | None = None, exit_y: str | None = None,
             entry_x: str | None = None, entry_y: str | None = None,
             waypoints: list[tuple[int, int]] | None = None,
             arrow: str = "block"):
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;"
            f"html=1;strokeColor={color};strokeWidth={width};endArrow={arrow};endFill=1;"
        )
        if dashed:
            style += "dashed=1;dashPattern=5 4;"
        for key, val in (("exitX", exit_x), ("exitY", exit_y),
                         ("entryX", entry_x), ("entryY", entry_y)):
            if val is not None:
                style += f"{key}={val};"
        cell = ET.SubElement(self.cells, "mxCell", {
            "id": cell_id, "value": label, "style": style,
            "edge": "1", "parent": "1", "source": source, "target": target,
        })
        geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if waypoints:
            array = ET.SubElement(geo, "Array", {"as": "points"})
            for x, y in waypoints:
                ET.SubElement(array, "mxPoint", {"x": str(x), "y": str(y)})
        return cell_id

    def save(self, stem: str, overwrite: bool = False):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{stem}.drawio"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}")
        ET.indent(self.root, space="  ")
        ET.ElementTree(self.root).write(path, encoding="utf-8", xml_declaration=True)
        return path


def base_title(d: Diagram, title: str, subtitle: str):
    d.text("title", title, 28, 16, 1000, 36, size=25, bold=True)
    d.text("subtitle", subtitle, 30, 54, 1260, 28, size=18, color=SUB)


def make_architecture():
    d = Diagram("Architecture", 660)
    base_title(d, "HMRS deployment architecture", "Web, agent, parsing and retrieval services share one auditable knowledge state")

    # Interface and service paths.
    d.panel("interface_band", 24, 94, 1272, 84, "#FAFBFC", "#D5DDE5")
    d.text("interface_label", "ENTRY POINTS", 40, 99, 190, 24, size=18, bold=True, color=BLUE)
    d.shape("browser", "Browser / Web UI", 205, 108, 265, 52, PALE_BLUE, BLUE, size=20, bold=True)
    d.shape("agent", "Agent / CLI", 1050, 108, 220, 52, PALE_PURPLE, PURPLE, size=20, bold=True)

    d.panel("service_band", 24, 190, 1272, 154, "#FFFFFF", "#D5DDE5")
    d.text("service_label", "SERVICE BOUNDARIES", 40, 196, 240, 24, size=18, bold=True, color=GREEN)
    d.shape("nuxt", "Nuxt 3 server\nproxy · catalog · file operations", 205, 240, 265, 76, PALE_BLUE, BLUE, size=19, bold=True)
    d.shape("fastapi", "FastAPI parse API\nasynchronous parse tasks", 520, 240, 230, 76, PALE_GREEN, GREEN, size=19, bold=True)
    d.shape("mineru", "Managed MinerU worker\nseparate process · dynamic port", 800, 240, 230, 76, PALE_GREEN, GREEN, size=18, bold=True)
    d.shape("mcp", "MCP server · 95 tools\nstdio · HTTP · files", 1050, 240, 220, 76, PALE_PURPLE, PURPLE, size=18, bold=True)

    d.edge("browser_to_nuxt", "browser", "nuxt", color=BLUE, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("agent_to_mcp", "agent", "mcp", color=PURPLE, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("nuxt_to_fastapi", "nuxt", "fastapi", color=GREEN, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.edge("fastapi_to_mineru", "fastapi", "mineru", color=GREEN, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")

    # Operational modules and the independent optional gate.
    d.panel("module_band", 24, 356, 1272, 102, "#FAFBFC", "#D5DDE5")
    d.text("module_label", "PLATFORM FUNCTIONS", 40, 361, 245, 24, size=18, bold=True, color=PURPLE)
    d.shape("ingest", "Ingestion · quality · split · enrich", 205, 397, 265, 44, PALE_GREEN, GREEN, size=18, bold=True)
    d.shape("lifecycle", "KB catalog · lifecycle\naudits", 510, 397, 255, 44, PALE_AMBER, AMBER, size=18, bold=True)
    d.shape("search", "BM25 · vector · two-stage · graph", 800, 397, 230, 44, PALE_BLUE, BLUE, size=18, bold=True)
    d.shape("gate", "Optional Laya gate · segment score", 1050, 397, 220, 44, PALE_RED, VERM, size=18, bold=True)

    # Shared state row.
    d.panel("state_band", 24, 472, 1272, 150, "#FFFFFF", "#D5DDE5")
    d.text("state_label", "SHARED KNOWLEDGE STATE", 40, 479, 315, 24, size=18, bold=True, color=PURPLE)
    d.shape("docstore", "Document files\nMarkdown · extracted assets", 205, 526, 265, 68, PALE_PURPLE, PURPLE, size=18, bold=True)
    d.shape("registry", "Registries\n.tree-fs.json · per-KB YAML", 510, 526, 255, 68, PALE_PURPLE, PURPLE, size=18, bold=True)
    d.shape("indices", "Search indices\nChroma vectors · BM25", 800, 526, 230, 68, PALE_PURPLE, PURPLE, size=18, bold=True)
    d.shape("graph", "Knowledge graph\nNeo4j · navigation", 1050, 526, 220, 68, PALE_PURPLE, PURPLE, size=18, bold=True)

    d.edge("mcp_to_gate", "mcp", "gate", color=PURPLE, dashed=True, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("ingest_to_files", "ingest", "docstore", color=GREEN, dashed=True, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("lifecycle_to_registry", "lifecycle", "registry", color=AMBER, dashed=True, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("search_to_indices", "search", "indices", color=BLUE, dashed=True, exit_x="0.5", exit_y="1", entry_x="0.5", entry_y="0")
    d.edge("search_to_graph", "search", "graph", color=BLUE, dashed=True, exit_x="0.85", exit_y="1", entry_x="0.25", entry_y="0")
    d.text("footer", "Saving, indexing and evidence judging are separate operations; the gate is an optional tool call.", 50, 626, 1210, 24, size=18, color=SUB, align="center")
    return d.save("fig1_architecture")


def make_workflow():
    d = Diagram("Workflow", 700)
    base_title(d, "From document ingestion to evidence handling", "Agent-mediated placement, explicit indexing and optional query-time judging")

    # Ingestion band.
    d.panel("ingest_panel", 24, 94, 1272, 192, "#F8FBF9", "#B7D1C2")
    d.text("ingest_heading", "A   KNOWLEDGE CREATION AND MAINTENANCE", 42, 100, 600, 28, size=18, bold=True, color=GREEN)
    y, h, w = 162, 82, 205
    xs = [48, 296, 544, 792, 1040]
    steps = [
        ("Source files", "PDF · Office · scans", PALE_BLUE, BLUE),
        ("Parse + quality", "OCR · structure · checks", PALE_GREEN, GREEN),
        ("Read + route", "Agent uses content + descriptions", PALE_AMBER, AMBER),
        ("Save state", "Markdown · registry · YAML", PALE_PURPLE, PURPLE),
        ("Index + probe", "separate async step", PALE_GREEN, GREEN),
    ]
    for i, (title, body, fill, stroke) in enumerate(steps):
        d.shape(f"ingest_step_{i}", f"<b>{title}</b><br>{body}", xs[i], y, w, h, fill, stroke, size=18)
        if i < 4:
            d.edge(f"ingest_edge_{i}", f"ingest_step_{i}", f"ingest_step_{i+1}", color=GREEN, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.text("placement_note", "The calling agent selects the destination; the storage API does not classify placement.", 62, 132, 1195, 24, size=18, color=SUB, align="center")

    # Shared store bridge.
    d.shape("shared_state", "Shared state: document files · tree registry · per-KB YAML · Chroma / BM25 / Neo4j", 130, 313, 1060, 56, PALE_PURPLE, PURPLE, size=19, bold=True)
    d.edge("write_to_shared", "ingest_step_3", "shared_state", color=PURPLE, dashed=True, exit_x="0.5", exit_y="1", entry_x="0.32", entry_y="0")

    # Query path and outcomes.
    d.panel("query_panel", 24, 392, 1272, 280, "#F7FAFC", "#B6C9DB")
    d.text("query_heading", "B   QUESTION-TO-EVIDENCE WORKFLOW", 42, 398, 600, 28, size=18, bold=True, color=BLUE)
    d.shape("question", "Question\nrequest + scope", 48, 466, 155, 72, PALE_BLUE, BLUE, size=18, bold=True)
    d.shape("lane", "Select lane\nSearch · Librarian · Hybrid", 235, 466, 228, 72, PALE_BLUE, BLUE, size=18, bold=True)
    d.shape("candidate", "Gather candidates\ncatalog · BM25 · vector · graph", 496, 466, 224, 72, PALE_BLUE, BLUE, size=18, bold=True)
    d.shape("judge", "Optional Laya gate\nfetch · segment · score · source", 753, 466, 245, 72, PALE_RED, VERM, size=18, bold=True)
    d.shape("answer", "Evidence pack\nsource pointers", 1032, 452, 225, 52, PALE_GREEN, GREEN, size=18, bold=True)
    d.shape("notfound", "Completed search\nno support → scoped not-found", 1032, 512, 255, 68, PALE_GREY, GREY, size=18, bold=True)
    d.shape("failure", "Execution failure\ntimeout · fetch · tool", 1032, 588, 255, 52, PALE_AMBER, AMBER, size=18, bold=True)

    d.edge("query_to_lane", "question", "lane", color=BLUE, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.edge("lane_to_candidates", "lane", "candidate", color=BLUE, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.edge("candidate_to_gate", "candidate", "judge", color=BLUE, dashed=True, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.edge("gate_to_evidence", "judge", "answer", color=GREEN, dashed=True, exit_x="1", exit_y="0.25", entry_x="0", entry_y="0.5")
    d.edge("candidate_to_absence", "candidate", "notfound", color=GREY, exit_x="0.5", exit_y="1", entry_x="0", entry_y="0.5")
    d.edge("candidate_to_failure", "candidate", "failure", color=AMBER, dashed=True, exit_x="0.5", exit_y="1", entry_x="0", entry_y="0.5")
    d.edge("shared_to_candidates", "shared_state", "candidate", color=PURPLE, dashed=True, exit_x="0.55", exit_y="1", entry_x="0.5", entry_y="0")
    d.text("query_note", "A completed search with no support is distinct from an execution failure.", 50, 644, 930, 26, size=18, color=SUB)
    return d.save("fig2_workflow")


def make_routing():
    d = Diagram("Routing audit", 640)
    base_title(d, "Route selection and full-read containment audit", "72 gold questions · 10 domain libraries · scripted route probe plus full-corpus scan")

    # Protocol panel.
    d.panel("protocol_panel", 24, 96, 1272, 162, "#FAFBFC", "#D5DDE5")
    d.text("protocol_heading", "(a) Experimental protocol", 44, 103, 380, 27, size=18, bold=True)
    d.shape("qset", "72 questions\n10 gold domains", 48, 151, 205, 68, PALE_BLUE, BLUE, size=19, bold=True)
    d.shape("a0", "A0 · descriptions\ncorpus-derived cards", 303, 132, 235, 44, PALE_GREEN, GREEN, size=18, bold=True)
    d.shape("a3", "A3 · name-only cards\nfull-catalog fallback", 303, 181, 235, 44, PALE_GREY, GREY, size=18, bold=True)
    d.shape("agent_route", "Scripted route\ncard top-1 / fallback", 590, 151, 210, 68, PALE_AMBER, AMBER, size=18, bold=True)
    d.shape("same_retrieval", "Scoped search\n+ evidence gate", 852, 151, 210, 68, PALE_BLUE, BLUE, size=18, bold=True)
    d.shape("pack", "Evidence pack\nexact-string check", 1110, 151, 170, 68, PALE_PURPLE, PURPLE, size=18, bold=True)
    d.shape("readall", "A1 separate script · read all 879 parts → exact-string check · no LLM answer", 42, 230, 1240, 22, PALE_PURPLE, PURPLE, size=18, bold=False)
    d.edge("q_to_a0", "qset", "a0", color=BLUE, exit_x="1", exit_y="0.3", entry_x="0", entry_y="0.5")
    d.edge("q_to_a3", "qset", "a3", color=GREY, exit_x="1", exit_y="0.8", entry_x="0", entry_y="0.5")
    d.edge("a0_to_route", "a0", "agent_route", color=GREEN, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.25")
    d.edge("a3_to_route", "a3", "agent_route", color=GREY, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.8")
    d.edge("route_to_retrieval", "agent_route", "same_retrieval", color=BLUE, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")
    d.edge("retrieval_to_pack", "same_retrieval", "pack", color=PURPLE, exit_x="1", exit_y="0.5", entry_x="0", entry_y="0.5")

    # Routing outcome panel with exact marginals and paired table.
    d.panel("route_panel", 24, 270, 790, 330, "#FFFFFF", "#C7D3DE")
    d.text("route_heading", "(b) Scripted route result · measured before retrieval", 42, 278, 740, 28, size=18, bold=True, color=BLUE)
    d.text("axis0", "0", 246, 441, 34, 22, size=18, align="center", color=SUB)
    d.text("axis50", "50", 394, 441, 44, 22, size=18, align="center", color=SUB)
    d.text("axis100", "100%", 534, 441, 60, 22, size=18, align="center", color=SUB)
    d.vertex("axisline", "", 250, 436, 300, 1, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("tick0", "", 250, 432, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("tick50", "", 400, 432, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("tick100", "", 550, 432, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.text("a0_label", "A0 · descriptions", 48, 332, 190, 26, size=18, bold=True, color=GREEN)
    d.text("a3_label", "A3 · names only", 48, 382, 190, 26, size=18, bold=True, color=GREY)
    d.vertex("a0_bar", "", 250, 330, 300, 28, "rounded=1;arcSize=8;fillColor=" + GREEN + ";strokeColor=" + GREEN + ";html=1;")
    d.vertex("a3_bar", "", 250, 380, 154, 28, "rounded=1;arcSize=8;fillColor=" + GREY + ";strokeColor=" + GREY + ";html=1;")
    d.text("a0_value", "72/72 · 100%", 565, 328, 175, 30, size=18, bold=True, color=GREEN)
    d.text("a3_value", "37/72 · 51.4%", 450, 378, 180, 30, size=18, bold=True, color=GREY)
    # Wilson intervals, exact values reported in the manuscript.
    d.vertex("a0_ci", "", 535, 344, 15, 0, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.vertex("a3_ci", "", 370, 394, 68, 0, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.vertex("a0_low_cap", "", 535, 338, 0, 12, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.vertex("a0_high_cap", "", 550, 338, 0, 12, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.vertex("a3_low_cap", "", 370, 388, 0, 12, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.vertex("a3_high_cap", "", 438, 388, 0, 12, "shape=line;strokeColor=#20262E;strokeWidth=2;html=1;")
    d.text("route_p", "Paired: 37 both correct · 35 A0-only · 0 A3-only · 0 neither<br>Exact McNemar p = 5.82 × 10⁻¹¹<br>A3 fallback may use descriptions; trigger was not logged", 45, 474, 740, 100, size=18, color=SUB, align="center")

    # Separate evidence-pack containment panel.
    d.panel("contain_panel", 834, 270, 462, 330, "#FFFFFF", "#C7D3DE")
    d.text("contain_heading", "(c) Exact gold-string containment", 852, 278, 420, 28, size=18, bold=True, color=PURPLE)
    d.text("contain_sub", "Exact-string check · 72 gold questions", 852, 306, 420, 22, size=18, color=SUB)
    d.text("ca0_label", "A0", 856, 339, 42, 24, size=18, bold=True, color=GREEN)
    d.text("ca3_label", "A3", 856, 377, 42, 24, size=18, bold=True, color=GREY)
    d.text("ca1_label", "A1", 856, 415, 42, 24, size=18, bold=True, color=PURPLE)
    d.vertex("ca0_bar", "", 905, 340, 103, 21, "rounded=1;arcSize=8;fillColor=" + GREEN + ";strokeColor=" + GREEN + ";html=1;")
    d.vertex("ca3_bar", "", 905, 378, 92, 21, "rounded=1;arcSize=8;fillColor=" + GREY + ";strokeColor=" + GREY + ";html=1;")
    d.vertex("ca1_bar", "", 905, 416, 200, 21, "rounded=1;arcSize=8;fillColor=" + PURPLE + ";strokeColor=" + PURPLE + ";html=1;")
    d.text("ca0_value", "37/72 · 51.4%", 1112, 337, 170, 27, size=18, bold=True, color=GREEN)
    d.text("ca3_value", "33/72 · 45.8%", 1112, 375, 170, 27, size=18, bold=True, color=GREY)
    d.text("ca1_value", "72/72 · 100%", 1112, 413, 170, 27, size=18, bold=True, color=PURPLE)
    d.vertex("contain_axis", "", 905, 444, 200, 1, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("contain_tick0", "", 905, 440, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("contain_tick50", "", 1005, 440, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.vertex("contain_tick100", "", 1105, 440, 1, 8, "shape=line;strokeColor=#AAB4BE;strokeWidth=1;html=1;")
    d.text("contain_axis0", "0", 897, 447, 25, 22, size=18, align="center", color=SUB)
    d.text("contain_axis50", "50", 991, 447, 30, 22, size=18, align="center", color=SUB)
    d.text("contain_axis100", "100%", 1085, 447, 45, 22, size=18, align="center", color=SUB)
    d.text("contain_p", "p: A0/A3 = 0.4545 · A1/A0 < 0.0001<br>Cost/query: A1 24.3 MB, 253.7 s · A0 31.4 KB, 16.3 s<br>Exact-string only · no LLM answers", 846, 472, 440, 118, size=18, color=SUB, align="center")

    d.text("footer", "A1 is a mechanical full-corpus scan, not an answer-quality or careful-agent baseline.", 40, 606, 1240, 28, size=18, color=INK, align="center")
    return d.save("fig3_routing")


AUDITS = {
    "fig1_architecture": [
        "Canvas and title; white background; restrained blue, green, purple, amber and grey palette.",
        "Entry-point band: Browser / Web UI and Agent / CLI.",
        "Service band: Nuxt 3 server, FastAPI parse API, managed MinerU worker, MCP server (95 tools).",
        "Connectors separate web and MCP entry paths, the parse path, and data access.",
        "Platform-function band: ingest quality/split/enrich, KB lifecycle/audits, retrieval engines, optional Laya call.",
        "Shared-state band: Markdown/assets, tree registry and per-KB YAML, Chroma/BM25, Neo4j.",
        "Dashed data-access connectors and footer clarify separate save/index/judge operations.",
    ],
    "fig2_workflow": [
        "Canvas, title, and two swimlane panels on white background.",
        "Ingestion steps: source files, parse/quality, agent content-aware routing, save, separate index/probe.",
        "Placement note states that destination selection is agent-mediated, not a server classifier.",
        "Shared knowledge state bridge joins ingestion to query-time retrieval.",
        "Query steps: question, lane selection, candidate retrieval, optional Laya gate.",
        "Three distinct outcomes: evidence pack, completed empty search, and execution failure.",
        "Connector styles distinguish normal flow, optional gate, and failure path.",
    ],
    "fig3_routing": [
        "Canvas, title, subtitle, white background, consistent academic palette.",
        "Protocol: A0 description cards; nominal A3 name-only cards with unlogged description-aware fallback caveat.",
        "A1 separate script reads all 879 parts and performs exact-string containment; no LLM answer generation.",
        "Scripted route-card selection is distinguished from an LLM agent choosing a library.",
        "Route accuracy bars: A0 72/72; A3 37/72; Wilson intervals and 0-100 scale.",
        "Paired route counts: 37 both, 35 A0-only, zero A3-only and zero neither; exact McNemar p.",
        "Separate three-arm containment panel: A0 37/72; A3 33/72; A1 72/72 with p-values and per-query cost.",
        "Caption and panel labels keep route correctness separate from substring containment.",
    ],
}


def write_audit(stem: str, items: list[str]):
    lines = [f"# Visual audit: {stem}", "", "Reference: GPT Image 2.5 visual-direction board in `garden-gpt-image-2/image/hmrs-kbs-visual-direction-20261106.png`.", "", "Each visible region and element was recreated with native Draw.io shapes, text and connectors.", "", "| ID | Visible element / check | Medium | Status |", "|---|---|---|---|"]
    for i, item in enumerate(items, 1):
        lines.append(f"| {i:02d} | {item} | Native Draw.io | pending export audit |")
    (OUT / f"{stem}.audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    overwrite = "--overwrite" in sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, builder in (("fig1_architecture", make_architecture),
                          ("fig2_workflow", make_workflow),
                          ("fig3_routing", make_routing)):
        if overwrite:
            for path in (OUT / f"{stem}.drawio", OUT / f"{stem}.audit.md"):
                path.unlink(missing_ok=True)
        builder()
        write_audit(stem, AUDITS[stem])
    print(f"Created editable Draw.io figures and audit inventories under {OUT}")


if __name__ == "__main__":
    main()
