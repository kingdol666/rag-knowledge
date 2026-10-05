"""Build fig1-core: the teaser figure (v2, nature-figure style).

Figure contract:
  Core conclusion: QDCVR couples autonomous knowledge-base management with
  librarian-style, layer-by-layer content-verified retrieval through one set
  of base/document/part/section addresses; conventional dense RAG cannot
  offer addressable sources.
  Archetype: schematic-led composite; hero panel = the QDCVR two loops plus
  the layered-address stack; the conventional baseline is subordinate gray.
Run: python paper_demo/figures/submission-20260920/build_fig1_core.py
All-English enforced; playwright (Chromium) + PyMuPDF; vector PDF with
embedded fonts; text-collision / clipping / box-overflow / border-cross gates.
"""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
from importlib.metadata import version

import fitz
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
INK = '#253745'
SUB = '#526472'
TEAL = '#2f7d5f'
BLUE = '#6c86a8'
WARN = '#bf4b28'
SAND = '#c09a4e'


def node(tag, **attrs):
    return ET.Element('{' + NS + '}' + tag,
                      {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text(x, y, value, size=14, weight=400, anchor='start', fill=INK):
    e = node('text', x=x, y=y, font_size=size, font_weight=weight,
             fill=fill, text_anchor=anchor, font_family='Calibri, Carlito, sans-serif')
    e.text = value
    return e


def chip(x, y, w, h, label, fill, stroke='#c5cfd5', size=13.5, weight=400,
         tcolor=INK, rx=4):
    g = node('g')
    g.append(node('rect', x=x, y=y, width=w, height=h, rx=rx, fill=fill, stroke=stroke))
    lines = label.split(chr(10))
    ly = y + h / 2 - (len(lines) - 1) * (size * 0.62) + size * 0.32
    for ln in lines:
        t = node('text', x=x + w / 2, y=ly, font_size=size, font_weight=weight,
                 fill=tcolor, text_anchor='middle',
                 font_family='Calibri, Carlito, sans-serif')
        t.text = ln
        g.append(t)
        ly += size * 1.24
    return g


def icon_doc(x, y, color):
    g = node('g')
    g.append(node('rect', x=x, y=y, width=15, height=19, rx=1.5, fill='none',
                  stroke=color, stroke_width=1.8))
    g.append(node('path', d='M' + str(x + 3) + ' ' + str(y + 5) + 'h9 M' + str(x + 3) +
                  ' ' + str(y + 9) + 'h9 M' + str(x + 3) + ' ' + str(y + 13) + 'h6',
                  stroke=color, stroke_width=1.6))
    return g


def icon_library(x, y, color):
    g = node('g')
    g.append(node('path', d='M' + str(x) + ' ' + str(y + 4) + 'l11 -7 11 7z', fill=color))
    g.append(node('rect', x=x, y=y + 4, width=22, height=2.2, fill=color))
    for dx in (3, 9.4, 15.8):
        g.append(node('rect', x=x + dx, y=y + 7, width=3.2, height=8, fill=color))
    g.append(node('rect', x=x, y=y + 15.5, width=22, height=2.2, fill=color))
    return g


def icon_gear(x, y, color):
    g = node('g')
    g.append(node('circle', cx=x + 8, cy=y + 8, r=4.6, fill='none',
                  stroke=color, stroke_width=2))
    g.append(node('circle', cx=x + 8, cy=y + 8, r=1.4, fill=color))
    for dx, dy in ((0, -7), (0, 7), (-7, 0), (7, 0)):
        g.append(node('rect', x=x + 8 + dx - 1.2, y=y + 8 + dy - 1.2,
                      width=2.4, height=2.4, fill=color))
    return g


def icon_search(x, y, color):
    g = node('g')
    g.append(node('circle', cx=x + 7, cy=y + 6, r=5.6, fill='none',
                  stroke=color, stroke_width=1.8))
    g.append(node('path', d='M' + str(x + 11.5) + ' ' + str(y + 10.5) + 'l5 5',
                  stroke=color, stroke_width=2.2))
    return g


def arrow_h(x1, x2, y):
    return node('path', d='M' + str(x1) + ' ' + str(y) + 'H' + str(x2),
                stroke=INK, stroke_width=1.3, fill='none', marker_end='url(#arrow)')


def build():
    H = 562
    root = node('svg', xmlns=NS, width=1000, height=H,
                viewBox='0 0 1000 ' + str(H), role='img',
                aria_labelledby='title desc')
    root.append(node('title', id='title'))
    for t in root.findall('{' + NS + '}title'):
        t.text = 'QDCVR at a glance'
    desc = node('desc', id='desc')
    desc.text = (
        'Left, subordinate gray: a conventional dense-RAG configuration - fixed '
        '800-character chunks, dense retrieval of the top two excerpts, a packed '
        'context of at most 4,000 characters, single generation; the reader gets '
        'an answer without citations, sources it cannot address, and retrieval '
        'errors that pass through silently; provenance is not logged. Right, '
        'hero: QDCVR, an agent-executed skill running two loops over one store. '
        'Loop one manages the knowledge base autonomously: PDF, parse with '
        'MinerU, route by content, tag, index as parts - every part carries a '
        'layered address (base Computer Science and AI; document '
        'attention-is-all-you-need.md; part 1 of 2; section 3.2.1 Scaled '
        'Dot-Product Attention). Loop two retrieves librarian-style: query '
        'rewrite, cross-base vector recall, read the candidates, then a 0-8 '
        'content rubric gate; gate at least six yields a cited answer with '
        'section-addressed sources, gate below six sends the librarian to '
        'browse base summaries and tag-matched shelves, ending in a qualified '
        'answer with attribution or a scoped not-found report. The invariant: '
        'one set of base, document, part, section addresses powers both loops, '
        'so every answer can be checked at its source. The left lane is shown '
        'for contrast; the evaluated dense variant is specified in Table 1.')
    root.append(desc)
    g = node('g', font_family='Calibri, Carlito, sans-serif')
    root.append(g)
    g.append(node('rect', width=1000, height=H, fill='white'))
    defs = node('defs')
    marker = node('marker', id='arrow', viewBox='0 0 8 8', refX=7, refY=4,
                  markerWidth=7, markerHeight=7, orient='auto-start-reverse')
    marker.append(node('path', d='M0 0L8 4L0 8', fill=INK))
    defs.append(marker)
    root.append(defs)

    g.append(text(20, 26, 'QDCVR at a glance: from raw PDFs to inspectable answers', 21, 600))
    g.append(text(20, 48, 'One store, two agent loops - content-guided management and '
                  'librarian-style retrieval share the same section addresses', 14.5, fill=SUB))

    # left lane (subordinate)
    LX, LW = 20, 330
    g.append(node('rect', x=LX, y=58, width=LW, height=446, rx=4, fill='#fbfcfd', stroke='#c5cfd5'))
    g.append(node('rect', x=LX, y=64, width=LW, height=44, rx=3, fill='#eef1f4'))
    g.append(icon_doc(LX + 12, 72, BLUE))
    g.append(text(LX + 36, 80, 'Conventional dense RAG', 15, 700))
    g.append(text(LX + 36, 96, 'pack-then-generate', 13.5, fill=SUB))
    steps = [
        ('Fixed chunks (about 800 characters)', 122),
        ('Dense retrieval, top-2 excerpts', 172),
        ('Pack a 4,000-char context', 222),
        ('Single generation, one answer', 272),
    ]
    for i, (label, y) in enumerate(steps):
        g.append(chip(LX + 14, y, LW - 28, 36, label, '#f7fafd', size=13.5))
        if i < len(steps) - 1:
            g.append(node('path', d='M' + str(LX + LW / 2) + ' ' + str(y + 36) +
                          'V' + str(y + 50), stroke=INK, stroke_width=1.3,
                          fill='none', marker_end='url(#arrow)'))
    g.append(node('rect', x=LX + 14, y=322, width=LW - 28, height=86, rx=3,
                  fill='white', stroke='#c5cfd5'))
    g.append(text(LX + 26, 340, 'WHAT A READER GETS', 12.5, 700, fill=SUB))
    for i, ln in enumerate(['- an answer, no citations required',
                            '- sources it cannot address',
                            '- retrieval errors pass through']):
        g.append(text(LX + 26, 360 + i * 16, ln, 13, fill=SUB))
    g.append(chip(LX + 14, 420, LW - 28, 30, 'provenance not logged in this harness',
                  'white', stroke=WARN, size=13, weight=600, tcolor=WARN))
    g.append(text(LX + 14, 470, 'shown for contrast;', 13, fill=SUB))
    g.append(text(LX + 14, 486, 'not the evaluated configuration', 13, fill=SUB))

    # right lane (hero)
    RX, RW = 368, 612
    g.append(node('rect', x=RX, y=58, width=RW, height=446, rx=4,
                  fill='#f7fbf9', stroke=TEAL, stroke_width=1.6))
    g.append(node('rect', x=RX, y=64, width=RW, height=44, rx=3, fill='#e7f3ec'))
    g.append(icon_library(RX + 12, 72, TEAL))
    g.append(text(RX + 44, 80, 'QDCVR - agent-executed skill', 16, 700))
    g.append(text(RX + 44, 98, 'manage and retrieve in one loop', 13.5, fill=SUB))

    # loop 1 manage
    g.append(node('rect', x=RX + 14, y=116, width=RW - 28, height=64, rx=3,
                  fill='#f4faf7', stroke='#c5cfd5'))
    g.append(icon_gear(RX + 26, 124, TEAL))
    g.append(text(RX + 52, 138, 'LOOP 1 - MANAGE: autonomous ingest', 13.5, 700))
    mx = RX + 26
    for label, w in [('PDF', 44), ('parse (MinerU)', 96), ('route by content', 112),
                     ('tag', 42), ('index as parts', 96)]:
        g.append(chip(mx, 148, w, 26, label, '#e7f3ec', size=12.5, weight=600))
        mx += w + 6

    # layered-address stack (hero element)
    g.append(text(RX + 14, 200, 'EVERY PART CARRIES A LAYERED ADDRESS', 12.5, 700, fill=SUB))
    stack = [
        (RX + 14, 584, '#e7f3ec', 'base > Computer Science & AI'),
        (RX + 30, 568, '#d9ede4', 'document > attention-is-all-you-need.md'),
        (RX + 46, 552, '#c8e3d6', 'part > 1 of 2'),
        (RX + 62, 536, '#b5d9c8', 'section > 3.2.1 Scaled Dot-Product Attention'),
    ]
    sy = 208
    for x, w, fill, label in stack:
        g.append(node('rect', x=x, y=sy, width=w, height=17, rx=2, fill=fill, stroke='#c5cfd5'))
        g.append(text(x + 8, sy + 13, label, 12.5, weight=600))
        sy += 19

    # loop 2 retrieve
    g.append(node('rect', x=RX + 14, y=296, width=RW - 28, height=168, rx=3,
                  fill='#fcf9f2', stroke='#c5cfd5'))
    g.append(icon_search(RX + 26, 304, SAND))
    g.append(text(RX + 52, 318, 'LOOP 2 - RETRIEVE: librarian-style, content-gated', 13.5, 700))
    g.append(chip(RX + 26, 330, 132, 28, 'query rewrite', '#f7efdf', size=12.5, weight=600))
    g.append(chip(RX + 168, 330, 162, 28, 'vector recall (cross-base)', '#f7efdf', size=12.5, weight=600))
    g.append(chip(RX + 340, 330, 140, 28, 'read the candidates', '#f7efdf', size=12.5, weight=600))
    g.append(arrow_h(RX + 158, RX + 168, 344))
    g.append(arrow_h(RX + 330, RX + 340, 344))
    g.append(chip(RX + 26, 368, 214, 40,
                  'content gate 0-8' + chr(10) + '(topic + scenario + evidence)',
                  '#f7efdf', size=12.5, weight=600))
    g.append(node('path', d='M' + str(RX + 410) + ' 358V362H' + str(RX + 133) + 'V368',
                  stroke=INK, stroke_width=1.3, fill='none', marker_end='url(#arrow)'))
    g.append(text(RX + 252, 382, 'gate at least 6: cited answer', 13.5, 700, fill=TEAL))
    g.append(text(RX + 252, 398, 'section-addressed sources', 13, fill=SUB))
    g.append(text(RX + 26, 422, 'gate below 6: librarian browses', 13.5, 700, fill=SUB))
    g.append(text(RX + 210, 422, 'base summaries + tag-matched shelves, re-check', 13, fill=SUB))
    g.append(chip(RX + 26, 432, 122, 26, 'cited (P0 at least 6)', '#e7f3ec', size=12.5, weight=600))
    g.append(chip(RX + 156, 432, 168, 26, 'qualified (P1 = 5, attributed)', '#efedf7', size=12.5, weight=600))
    g.append(chip(RX + 332, 432, 148, 26, 'not found (scoped)', '#f7efdf', size=12.5, weight=600))

    # invariant strip
    g.append(node('rect', x=RX, y=512, width=RW, height=40, rx=3,
                  fill='#f4faf7', stroke=TEAL))
    g.append(text(RX + 14, 528, 'The invariant: one set of base / document / part / section '
                  'addresses powers both loops,', 14, 600))
    g.append(text(RX + 14, 546, 'so every answer can be checked at its source.', 14, 600))

    # footers under left lane
    g.append(text(LX, 518, 'Left lane: conventional dense RAG, shown for contrast;', 13.5, fill=SUB))
    g.append(text(LX, 534, 'the evaluated dense variant is specified in Table 1.', 13.5, fill=SUB))
    g.append(text(LX, 550, 'Scores are agent judgments, not accuracy measurements.', 13.5, fill=SUB))
    root.set('height', str(H))
    return root, H


def main():
    root, H = build()
    source = ET.tostring(root, encoding='unicode')
    assert '<image' not in source and '<foreignObject' not in source
    assert not re.search('[\\u4e00-\\u9fff]', source), 'CJK character found in figure'
    (OUT / 'fig1-core.svg').write_text(source, encoding='utf-8')
    html = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>fig1-core</title>'
            '<style>@page{size:1000px ' + str(H) + 'px;margin:0}html,body{margin:0;width:1000px;height:'
            + str(H) + 'px}svg{display:block}</style>' + source + '</html>')
    (OUT / 'fig1-core.html').write_text(html, encoding='utf-8')
    report = {'runtime': {'playwright': version('playwright'), 'PyMuPDF': version('PyMuPDF')}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        report['runtime']['chromium'] = browser.version
        page = browser.new_page(viewport={'width': 1000, 'height': H}, device_scale_factor=2)
        page.goto((OUT / 'fig1-core.html').as_uri())
        page.evaluate('document.fonts.ready')
        checks = page.evaluate('''() => {
            const svg=document.querySelector('svg'), s=svg.getBoundingClientRect();
            const ts=[...svg.querySelectorAll('text')];
            const rects=[...svg.querySelectorAll('rect')].map(r=>r.getBoundingClientRect());
            const boxOverflow=ts.filter(t=>{const b=t.getBoundingClientRect();
                const host=rects.find(r=>r.width<900&&b.left+b.width/2>=r.left&&b.left+b.width/2<=r.right&&b.top>=r.top-2&&b.top<=r.bottom);
                return host&&(b.right>host.right-3||b.bottom>host.bottom+2);}).map(t=>t.textContent);
            const borderCross=ts.flatMap(t=>{const b=t.getBoundingClientRect();
                return rects.filter(r=>r.width<900&&Math.min(b.right,r.right)-Math.max(b.left,r.left)>b.width*0.5
                    &&((b.top<r.top&&b.bottom>r.top)||(b.top<r.bottom&&b.bottom>r.bottom)))
                .map(()=>t.textContent)});
            return {minimum_font_px:Math.min(...ts.map(t=>parseFloat(getComputedStyle(t).fontSize))),
                out_of_bounds:ts.filter(t=>{const b=t.getBoundingClientRect();return b.left<s.left||b.top<s.top||b.right>s.right||b.bottom>s.bottom}).map(t=>t.textContent),
                box_overflow:boxOverflow, border_cross:borderCross,
                overlaps:ts.flatMap((a,i)=>ts.slice(i+1).filter(b=>{let x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return Math.min(x.right,y.right)-Math.max(x.left,y.left)>1&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>1}).map(b=>[a.textContent,b.textContent]))};
        }''')
        assert checks['minimum_font_px'] >= 12.5, checks
        assert not checks['out_of_bounds'] and not checks['overlaps'], checks
        assert not checks['box_overflow'], checks
        assert not checks['border_cross'], checks
        page.locator('svg').screenshot(path=str(OUT / 'fig1-core.png'))
        page.pdf(path=str(OUT / 'fig1-core.pdf'), width='1000px', height=str(H) + 'px',
                 print_background=True, prefer_css_page_size=True,
                 margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
        page.close()
        with fitz.open(OUT / 'fig1-core.pdf') as pdf:
            pdf[0].set_mediabox(fitz.Rect(0, 0, 750, H * .75))
            trimmed = pdf.tobytes()
        (OUT / 'fig1-core.pdf').write_bytes(trimmed)
        with fitz.open(OUT / 'fig1-core.pdf') as pdf:
            pg = pdf[0]
            assert not pg.get_images(full=True), 'Raster image in PDF'
            assert len(pg.get_text()) > 300 and len(pg.get_drawings()) >= 10
            for font in pg.get_fonts(full=True):
                if font[2] != 'Type3':
                    assert pdf.extract_font(font[0])[3], 'Unembedded font: ' + str(font)
            checks.update(pdf_mediabox=list(pg.mediabox), pdf_images=0,
                          pdf_vector_paths=len(pg.get_drawings()))
            pg.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(OUT / 'fig1-core-pdf-proof.png')
        report['checks'] = checks
        browser.close()
    (OUT / 'verification-fig1.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PASS fig1-core: vector PDF, fonts embedded, gates green')


if __name__ == '__main__':
    main()
