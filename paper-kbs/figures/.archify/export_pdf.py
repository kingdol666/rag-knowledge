# Export finalized archify HTML diagrams to cropped vector PDFs for LaTeX.
# Usage: python export_pdf.py <html> <out_pdf>
import sys, os
from playwright.sync_api import sync_playwright
import pymupdf

HIDE_CSS = """
header, [class*="header"], [class*="summary"], [class*="cards"], [class*="toolbar"],
[class*="Header"], [class*="breadcrumb"], footer, [class*="footer"],
[class*="share"], [class*="meta-row"], [class*="titlebar"], [class*="export-menu"],
[class*="legend"] { display: none !important; }
body { background: #ffffff !important; }
"""

BUMP_JS = """() => {
  const svg = document.querySelector('svg');
  if (!svg) return null;
  const texts = svg.querySelectorAll('text');
  texts.forEach(t => {
    const fsAttr = t.getAttribute('font-size');
    if (fsAttr) {
      const fs = parseFloat(fsAttr);
      const nf = fs <= 9.5 ? Math.round(fs * 1.25 * 2) / 2 : Math.round(fs * 1.22 * 2) / 2;
      t.setAttribute('font-size', nf);
    } else {
      const cs = getComputedStyle(t).fontSize;
      const fs = parseFloat(cs);
      if (fs && fs < 12) t.style.fontSize = (Math.round(fs * 1.3 * 2) / 2) + 'px';
    }
  });
  // hide any legend group inside the svg
  svg.querySelectorAll('[data-legend]').forEach(g => g.remove());
  const r = svg.getBoundingClientRect();
  return {x: r.x, y: r.y, w: r.width, h: r.height,
          bodyW: document.body.scrollWidth, bodyH: document.body.scrollHeight};
}"""

def export(html_path, pdf_path, diagram_width_px=None):
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(900)
        page.add_style_tag(content=HIDE_CSS)
        page.wait_for_timeout(200)
        box = page.evaluate(BUMP_JS)
        if diagram_width_px:
            # Crop the PDF page canvas to the figure itself instead of retaining the 1500px reader viewport.
            svg = page.locator("svg").first
            svg_box = svg.bounding_box()
            if not svg_box:
                raise RuntimeError("diagram SVG has no browser bounds")
            await_width = int(diagram_width_px)
            page_height = int(box["bodyH"] * await_width / box["w"])
            page.pdf(path=pdf_path, print_background=True,
                     width=f"{await_width}px", height=f"{page_height}px",
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                     page_ranges="1")
            print("diagram box:", box, "cropped page:", await_width, page_height)
        else:
            page.pdf(path=pdf_path, print_background=True,
                     width=f"{int(box['bodyW'])}px", height=f"{int(box['bodyH'])}px",
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                     page_ranges="1")
            print("diagram box:", box)
        browser.close()
    return box

def crop(pdf_path):
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    rects = []
    for b in page.get_text("blocks"):
        rects.append(pymupdf.Rect(b[:4]))
    for d in page.get_drawings():
        rects.append(d["rect"])
    bb = rects[0]
    for r in rects[1:]:
        bb |= r
    bb = bb + (-2, -2, 2, 2)
    page.set_cropbox(bb & page.rect)
    doc.saveIncr()
    doc.close()
    doc = pymupdf.open(pdf_path)
    print("cropped size (pt):", round(doc[0].cropbox.width, 1), round(doc[0].cropbox.height, 1))
    doc.close()

if __name__ == "__main__":
    html, pdf = sys.argv[1], sys.argv[2]
    export(html, pdf)
    crop(pdf)
