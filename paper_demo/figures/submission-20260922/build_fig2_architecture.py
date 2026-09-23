"""Build fig2-architecture v2 (submission-20260922): platform operations and
the agent-executed retrieval workflow, in the fig1-core visual language.

Pipeline: playwright loads fig2-architecture.html, runs quality gates
(minimum font, out-of-bounds, text overlaps, box overflow, border crossings),
screenshots the SVG (2x PNG for review), prints a vector PDF, trims the
mediabox to 750 pt width, and asserts vector-only output with embedded fonts.
Run: python paper_demo/figures/submission-20260922/build_fig2_architecture.py
"""
from pathlib import Path
import json

import fitz
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
HTML = OUT / 'fig2-architecture.html'
W, H = 1000, 589
MBW = 750  # mediabox width in pt (0.75 pt per design px)


def main():
    report = {'figure': 'fig2-architecture v2', 'html': HTML.name}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': W, 'height': H},
                                device_scale_factor=2)
        page.goto(HTML.as_uri())
        page.wait_for_timeout(400)
        checks = page.evaluate('''() => {
            const svg = document.querySelector('svg');
            const s = svg.getBoundingClientRect();
            const ts = [...svg.querySelectorAll('text')];
            const rects = [...svg.querySelectorAll('rect')].map(r => r.getBoundingClientRect());
            const boxOverflow = rects.flatMap(r => {
                const over = ts.filter(t => {
                    const b = t.getBoundingClientRect();
                    const pad = 3;
                    return b.left > r.left && b.right < r.right && b.top > r.top && b.bottom < r.bottom
                        && (b.left - r.left < pad || r.right - b.right < pad
                            || b.top - r.top < pad || r.bottom - b.bottom < pad);
                }).map(t => t.textContent);
                return over.length ? [over] : [];
            });
            const borderCross = ts.flatMap(t => {
                const b = t.getBoundingClientRect();
                return rects.filter(r => r.width < 900
                    && Math.min(b.right, r.right) - Math.max(b.left, r.left) > b.width * 0.5
                    && ((b.top < r.top && b.bottom > r.top) || (b.top < r.bottom && b.bottom > r.bottom)))
                    .map(() => t.textContent);
            });
            return {
                minimum_font_px: Math.min(...ts.map(t => parseFloat(getComputedStyle(t).fontSize))),
                out_of_bounds: ts.filter(t => {
                    const b = t.getBoundingClientRect();
                    return b.left < s.left || b.top < s.top || b.right > s.right || b.bottom > s.bottom;
                }).map(t => t.textContent),
                box_overflow: boxOverflow,
                border_cross: borderCross,
                overlaps: ts.flatMap((a, i) => ts.slice(i + 1).filter(b => {
                    const x = a.getBoundingClientRect(), y = b.getBoundingClientRect();
                    return Math.min(x.right, y.right) - Math.max(x.left, y.left) > 1
                        && Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top) > 1;
                }).map(b => b.textContent))
            };
        }''')
        assert checks['minimum_font_px'] >= 11.9, checks
        assert not checks['out_of_bounds'] and not checks['overlaps'], checks
        assert not checks['box_overflow'], checks
        assert not checks['border_cross'], checks
        page.locator('svg').screenshot(path=str(OUT / 'fig2-architecture.png'))
        page.pdf(path=str(OUT / 'fig2-architecture.pdf'), width=f'{W}px', height=f'{H}px',
                 print_background=True, prefer_css_page_size=True,
                 margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
        page.close()
        with fitz.open(OUT / 'fig2-architecture.pdf') as pdf:
            pdf[0].set_mediabox(fitz.Rect(0, 0, MBW, H * (MBW / W)))
            trimmed = pdf.tobytes()
        (OUT / 'fig2-architecture.pdf').write_bytes(trimmed)
        with fitz.open(OUT / 'fig2-architecture.pdf') as pdf:
            pg = pdf[0]
            assert not pg.get_images(full=True), 'Raster image in PDF'
            assert len(pg.get_text()) > 300 and len(pg.get_drawings()) >= 10
            for font in pg.get_fonts(full=True):
                if font[2] != 'Type3':
                    assert pdf.extract_font(font[0])[3], 'Unembedded font: ' + str(font)
            checks.update(pdf_mediabox=list(pg.mediabox), pdf_images=0,
                          pdf_vector_paths=len(pg.get_drawings()))
            pg.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(
                OUT / 'fig2-architecture-pdf-proof.png')
        report['checks'] = checks
        browser.close()
    (OUT / 'verification-fig2.json').write_text(json.dumps(report, indent=2),
                                                encoding='utf-8')
    print('PASS fig2-architecture v2: vector PDF, fonts embedded, gates green')


if __name__ == '__main__':
    main()
