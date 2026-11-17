#!/usr/bin/env python3
"""Render the native Draw.io XML to SVG for local PDF/PNG export."""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "kbs_revision_20261106"
TARGET = ROOT.parent / "tex" / "journal_20p" / "figs"


def style_map(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in style.split(";"):
        if "=" in entry:
            k, v = entry.split("=", 1)
            out[k] = v
    return out


def number(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def attr_escape(value: str) -> str:
    return html.escape(value, quote=True)


def clean_text(value: str) -> list[tuple[str, bool]]:
    value = re.sub(r"<br\s*/?>|</(?:div|p|li)\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<(?:div|p|li)(?:\s[^>]*)?>", "", value, flags=re.I)
    result: list[tuple[str, bool]] = []
    for raw in value.replace("\r", "").split("\n"):
        bold = bool(re.search(r"<(?:b|strong)(?:\s[^>]*)?>", raw, flags=re.I))
        line = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        if line:
            result.append((line, bold))
    return result


def wrap_lines(lines: list[tuple[str, bool]], width: float, size: float) -> list[tuple[str, bool]]:
    max_chars = max(8, int(width / max(5.8, size * 0.55)))
    result: list[tuple[str, bool]] = []
    for line, bold in lines:
        if len(line) <= max_chars:
            result.append((line, bold))
            continue
        words = line.split(" ")
        acc = ""
        for word in words:
            candidate = f"{acc} {word}".strip()
            if acc and len(candidate) > max_chars:
                result.append((acc, bold))
                acc = word
            else:
                acc = candidate
        if acc:
            result.append((acc, bold))
    return result


def render_text(value: str, x: float, y: float, w: float, h: float,
                style: dict[str, str], *, shape_text: bool = False) -> str:
    lines = wrap_lines(clean_text(value), w - 18, number(style.get("fontSize"), 18))
    if not lines:
        return ""
    size = number(style.get("fontSize"), 18)
    line_height = size * 1.18
    align = style.get("align", "center")
    anchor = {"left": "start", "right": "end"}.get(align, "middle")
    tx = x + 9 if anchor == "start" else x + w - 9 if anchor == "end" else x + w / 2
    valign = style.get("verticalAlign", "middle")
    total = line_height * (len(lines) - 1)
    if valign == "top":
        first_y = y + size + 4
    elif valign == "bottom":
        first_y = y + h - total - 5
    else:
        first_y = y + (h - total) / 2 + size * 0.34
    color = style.get("fontColor", "#20262E")
    weight = "700" if "1" in style.get("fontStyle", "") else "400"
    italic = "italic" if "2" in style.get("fontStyle", "") else "normal"
    spans = "".join(
        f'<tspan x="{tx:.2f}" y="{first_y + i * line_height:.2f}" '
        f'font-weight="{"700" if line_bold else weight}">{attr_escape(line)}</tspan>'
        for i, (line, line_bold) in enumerate(lines)
    )
    return (f'<text text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size:g}px" font-weight="{weight}" font-style="{italic}" '
            f'fill="{attr_escape(color)}">{spans}</text>')


def geometry(cell: ET.Element) -> tuple[float, float, float, float] | None:
    g = cell.find("mxGeometry")
    if g is None or g.get("relative") == "1":
        return None
    return (number(g.get("x")), number(g.get("y")),
            number(g.get("width")), number(g.get("height")))


def vertex_svg(cell: ET.Element) -> str:
    x, y, w, h = geometry(cell) or (0, 0, 0, 0)
    style = style_map(cell.get("style", ""))
    fill = style.get("fillColor", "none")
    stroke = style.get("strokeColor", "none")
    sw = number(style.get("strokeWidth"), 1.2)
    shape = style.get("shape", "rect")
    rx = 13 if style.get("rounded") == "1" else 0
    dash = ' stroke-dasharray="5 4"' if style.get("dashed") == "1" else ""
    if shape == "line":
        return (f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x+w:.2f}" y2="{y+h:.2f}" '
                f'stroke="{attr_escape(stroke)}" stroke-width="{sw:g}"{dash}/>')
    if shape == "ellipse":
        shape_xml = (f'<ellipse cx="{x+w/2:.2f}" cy="{y+h/2:.2f}" rx="{w/2:.2f}" ry="{h/2:.2f}" '
                     f'fill="{attr_escape(fill)}" stroke="{attr_escape(stroke)}" stroke-width="{sw:g}"{dash}/>')
    elif shape in {"rhombus", "diamond"}:
        points = f"{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}"
        shape_xml = (f'<polygon points="{points}" fill="{attr_escape(fill)}" '
                     f'stroke="{attr_escape(stroke)}" stroke-width="{sw:g}"{dash}/>')
    else:
        shape_xml = (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                     f'rx="{rx}" fill="{attr_escape(fill)}" stroke="{attr_escape(stroke)}" '
                     f'stroke-width="{sw:g}"{dash}/>')
    label = render_text(cell.get("value", ""), x, y, w, h, style, shape_text=True)
    return shape_xml + label


def edge_svg(cell: ET.Element, cells: dict[str, ET.Element]) -> str:
    style = style_map(cell.get("style", ""))
    source, target = cells.get(cell.get("source", "")), cells.get(cell.get("target", ""))
    if source is None or target is None:
        return ""
    sg, tg = geometry(source), geometry(target)
    if sg is None or tg is None:
        return ""
    sx, sy, sw, sh = sg
    tx, ty, tw, th = tg
    ex, ey = number(style.get("exitX"), 0.5), number(style.get("exitY"), 0.5)
    ix, iy = number(style.get("entryX"), 0.5), number(style.get("entryY"), 0.5)
    x1, y1 = sx + sw * ex, sy + sh * ey
    x2, y2 = tx + tw * ix, ty + th * iy
    horiz_start = ex in (0, 1)
    horiz_end = ix in (0, 1)
    if horiz_start and horiz_end:
        mx = (x1 + x2) / 2
        points = [(x1, y1), (mx, y1), (mx, y2), (x2, y2)]
    elif not horiz_start and not horiz_end:
        if abs(x1 - x2) < 2:
            points = [(x1, y1), (x2, y2)]
        else:
            my = max(y1, y2) - 12 if y2 >= y1 else min(y1, y2) - 12
            points = [(x1, y1), (x1, my), (x2, my), (x2, y2)]
    elif horiz_start:
        points = [(x1, y1), (x2, y1), (x2, y2)]
    else:
        points = [(x1, y1), (x1, y2), (x2, y2)]
    d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points)
    color = style.get("strokeColor", "#53606B")
    swidth = number(style.get("strokeWidth"), 1.4)
    dash = ' stroke-dasharray="5 4"' if style.get("dashed") == "1" else ""
    arrow = ' marker-end="url(#arrow)"' if style.get("endArrow", "block") != "none" else ""
    out = (f'<path d="{d}" fill="none" stroke="{attr_escape(color)}" '
           f'stroke-width="{swidth:g}" stroke-linejoin="round" stroke-linecap="round"{dash}{arrow}/>')
    label = cell.get("value", "").strip()
    if label:
        lx = sum(p[0] for p in points) / len(points)
        ly = sum(p[1] for p in points) / len(points) - 7
        out += (f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'font-family="Arial, Helvetica, sans-serif" font-size="14px" '
                f'fill="{attr_escape(color)}">{attr_escape(label)}</text>')
    return out


def render(source: Path) -> Path:
    root = ET.parse(source).getroot()
    model = root.find(".//mxGraphModel")
    if model is None:
        raise ValueError(f"No mxGraphModel in {source}")
    width, height = number(model.get("pageWidth"), 1320), number(model.get("pageHeight"), 700)
    cells = {c.get("id", ""): c for c in model.findall(".//mxCell")}
    cell_order = list(model.findall(".//mxCell"))

    backgrounds: list[str] = []
    connectors = [edge_svg(c, cells) for c in cell_order if c.get("edge") == "1"]
    foreground: list[str] = []
    for c in cell_order:
        if c.get("vertex") != "1":
            continue
        geom = geometry(c)
        if geom is None:
            continue
        _, _, w, h = geom
        if w > width * 0.70 or h > height * 0.32:
            backgrounds.append(vertex_svg(c))
        else:
            foreground.append(vertex_svg(c))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" '
           f'viewBox="0 0 {width} {height}">'
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
           'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>'
           f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
           + "".join(backgrounds) + "".join(connectors) + "".join(foreground) + "</svg>")
    svg_output = TARGET / f"{source.stem}.svg"
    html_output = TARGET / f"{source.stem}.print.html"
    output = (f"<!doctype html><html><head><meta charset=\"utf-8\"><style>"
              f"@page{{size:{width}px {height}px;margin:0}}"
              f"html,body{{margin:0!important;padding:0;width:{width}px;height:{height}px;overflow:hidden}}"
              f"svg{{display:block;width:{width}px;height:{height}px}}"
              f"</style></head><body>{svg}</body></html>")
    TARGET.mkdir(parents=True, exist_ok=True)
    svg_output.write_text(svg, encoding="utf-8")
    html_output.write_text(output, encoding="utf-8")
    return html_output


def main() -> int:
    files = sorted(SOURCE.glob("fig*.drawio"))
    if not files:
        print(f"No Draw.io files found in {SOURCE}", file=sys.stderr)
        return 2
    for source in files:
        output = render(source)
        print(f"{source.name} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
