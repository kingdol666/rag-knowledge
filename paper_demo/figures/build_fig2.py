#!/usr/bin/env python3
"""Build Fig. 2 — the UI composite figure — from real console screenshots.

Crops four panels out of the full-resolution captures (2x device scale),
arranges them in a 2x2 grid with numbered callout badges, and renders the HTML
to a print-resolution PNG via Playwright.

Output: paper_demo/figures/fig2_ui_composite.png  (+ .html source)
"""
from __future__ import annotations

import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
CROPS = HERE / "crops"
CROPS.mkdir(exist_ok=True)

# Panel definitions. `box` is in ORIGINAL capture pixels (3360x2100 for a
# 1680x1050 viewport at device_scale_factor=2). Every box is normalised to the
# same aspect ratio (CELL_ASPECT) so the two-column grid has no ragged rows and
# no stretched whitespace. Boxes are positioned to keep the panel's operative
# content (the real query, the real counts, the real hit cards).
CELL_ASPECT = 2.42

PANELS = [
    dict(key="org", src="knowledge-search__viewport.png", box=(940, 905, 2400, 1642),
         n="1", title="Category bases built from content",
         sub="five content-classified bases plus three frozen baseline indices, each with its own document count"),
    dict(key="ret", src="search__nisq__viewport.png", box=(944, 348, 3332, 1554),
         n="2", title="Content-verified retrieval, live",
         sub="real query; the gold NISQ paper returns first with fused score and owning base"),
    dict(key="doc", src="knowledge-base__viewport.png", box=(1578, 496, 3312, 1372),
         n="3", title="Parts carry headers; tags propagate",
         sub="long papers become (part k of N) and inherit base tags"),
    dict(key="graph", src="knowledge-graph__viewport.png", box=(944, 344, 3332, 1550),
         n="4", title="Cross-base relation graph",
         sub="165 documents, 321 relations, 27 shared tags over 8 bases"),
]


def crop() -> dict:
    from PIL import Image
    out = {}
    for p in PANELS:
        src = SHOTS / p["src"]
        im = Image.open(src)
        x0, y0, x1, y1 = p["box"]
        # normalise to CELL_ASPECT by expanding height (centred on the box)
        w = x1 - x0
        want_h = int(round(w / CELL_ASPECT))
        have_h = y1 - y0
        if want_h > have_h:
            grow = want_h - have_h
            y0 = max(0, y0 - grow // 2)
            y1 = min(im.height, y0 + want_h)
            y0 = max(0, y1 - want_h)
        else:
            y1 = y0 + want_h
        c = im.crop((x0, y0, x1, y1))
        dest = CROPS / f"{p['key']}.png"
        c.save(dest)
        out[p["key"]] = (c.width, c.height)
        print(f"  {p['key']:<6} {src.name}  box=({x0},{y0},{x1},{y1})  -> {c.size}"
              f"  aspect={c.width / c.height:.2f}")
    return out


def build_html(sizes: dict) -> Path:
    def panel(p):
        w, h = sizes[p["key"]]
        return f"""
      <figure class="panel" data-n="{p['n']}">
        <div class="badge">{p['n']}</div>
        <img src="crops/{p['key']}.png" alt="{html.escape(p['title'])}">
        <figcaption><b>{html.escape(p['title'])}</b>
          <span>{html.escape(p['sub'])}</span></figcaption>
      </figure>"""

    body = "".join(panel(p) for p in PANELS)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 2000px; padding: 26px 26px 20px;
    background: #ffffff;
    font-family: "Helvetica Neue", Helvetica, Arial, "Noto Sans", sans-serif;
    color: #1c1c1e; -webkit-font-smoothing: antialiased;
  }}
  .head {{ display: flex; align-items: baseline; gap: 16px;
           border-bottom: 2.5px solid #b4441f; padding-bottom: 9px;
           margin-bottom: 18px; }}
  .head h1 {{ font-size: 30px; font-weight: 700; letter-spacing: -.2px; }}
  .head .sub {{ font-size: 17px; color: #5c5c66; }}
  .head .k {{ margin-left: auto; font-size: 15px; color: #8a8a94;
              font-variant-numeric: tabular-nums; }}

  .grid {{ columns: 2; column-gap: 18px; }}
  .panel {{ position: relative; background: #fff;
            border: 1.4px solid #d8d5cd; border-radius: 9px;
            overflow: hidden; display: block;
            break-inside: avoid; margin: 0 0 18px; }}
  .panel img {{ width: 100%; display: block; }}
  .badge {{
    position: absolute; top: 9px; left: 9px; z-index: 3;
    width: 33px; height: 33px; border-radius: 50%;
    background: #b4441f; color: #fff;
    font-size: 18px; font-weight: 700; line-height: 33px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.30);
    border: 2px solid #fff;
  }}
  figcaption {{ padding: 10px 13px 11px; border-top: 1.4px solid #e6e3dc;
                background: #fbfaf7; font-size: 16px; line-height: 1.35; }}
  figcaption b {{ display: block; font-size: 17px; margin-bottom: 2px;
                  color: #17171a; }}
  figcaption span {{ color: #5c5c66; }}

  .foot {{ margin-top: 15px; display: flex; gap: 10px; align-items: center;
           font-size: 15px; color: #6a6a74;
           border-top: 1.4px solid #e6e3dc; padding-top: 11px; }}
  .chip {{ border: 1.2px solid #cfccc4; border-radius: 999px;
           padding: 3px 12px; font-size: 14px; color: #3d3d44;
           background: #fbfaf7; }}
  .chip.acc {{ border-color: #d9a08c; color: #8f3315; background: #fdf3ef; }}
</style></head>
<body>
  <div class="head">
    <h1>One console, three contracts</h1>
    <span class="sub">live captures of the running deployment</span>
    <span class="k">50 papers &middot; 5 category bases &middot; 165 indexed documents</span>
  </div>
  <div class="grid">{body}
  </div>
  <div class="foot">
    <span class="chip acc">content decides placement</span>
    <span class="chip">evidence is read, not scored</span>
    <span class="chip">parts carry section headers</span>
    <span class="chip">failure is reported, never fabricated</span>
    <span style="margin-left:auto">Screenshots taken from the deployed instance;
      no interface element is mocked.</span>
  </div>
</body></html>"""
    p = HERE / "fig2_ui_composite.html"
    p.write_text(doc, encoding="utf-8")
    return p


def render(src: Path) -> Path:
    from playwright.sync_api import sync_playwright
    out = HERE / "fig2_ui_composite.png"
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
        pg = br.new_page(viewport={"width": 2060, "height": 1400},
                         device_scale_factor=2)
        pg.goto(src.as_uri(), wait_until="load")
        pg.wait_for_timeout(1200)
        el = pg.locator("body")
        el.screenshot(path=str(out))
        h = pg.evaluate("() => document.body.scrollHeight")
        br.close()
    print(f"  -> {out}  (body height {h} css px, rendered at 2x)")
    return out


if __name__ == "__main__":
    print("[1/3] cropping panels")
    sizes = crop()
    print("[2/3] building HTML")
    src = build_html(sizes)
    print(f"  -> {src}")
    print("[3/3] rendering PNG")
    render(src)
