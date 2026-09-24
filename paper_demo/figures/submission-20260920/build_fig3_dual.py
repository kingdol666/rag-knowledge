"""Build fig3-answers-dual: TWO questions' real saved answers across modes.

Run: python paper_demo/figures/submission-20260920/build_fig3_dual.py
Data source: benchmark-suite/results/experiment_chat_20260922-211000/*.json
(the 2026-09-22 100-paper three-mode run). Panel 1: the Gene Ontology
question answered by all three modes (BQ04). Panel 2: the precipitation-
extremes question — the platform's verified answer (A) beside the dense
mode's measured abstention (C, BQ06). Every quoted fragment in the figure is
asserted to be a verbatim substring of the saved answer (after removing
markdown emphasis and collapsing whitespace); the build fails otherwise.
The per-mode tool timelines are transcribed from the saved trace timelines
(tool_use events, in order). All-English enforced (CJK assertion).
Rendering/QA machinery: playwright (Chromium) + PyMuPDF, vector PDF with
embedded fonts, text-collision / clipping / box-overflow gates.
"""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
from importlib.metadata import version

import fitz
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
RUN = ROOT / 'benchmark-suite' / 'results' / 'experiment_chat_20260922-211000'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
INK = '#253745'
SUB = '#526472'
STYLE = {
    'a': {'fill': '#e6f3ec', 'box': '#f4faf7', 'dot': '#1f7a5c',
          'label': 'A · QDCVR platform', 'route': 'answers with addressable sources'},
    'b': {'fill': '#eef2f6', 'box': '#f7f9fb', 'dot': '#52615c',
          'label': 'B · Bare agent', 'route': 'file tools over exported papers'},
    'c': {'fill': '#f6f1e4', 'box': '#fbf8f0', 'dot': '#a07d3a',
          'label': 'C · Dense retrieval', 'route': 'vector search over chunk index'},
}

# Panel 1 (BQ04): verbatim fragments, normalized-substring checked.
Q1 = {
    'qid': 'BQ04',
    'question': 'Which three independent ontologies subdivide the Gene Ontology?',
    'quotes': {
        'a': [
            '1. Molecular Function (MF) 2. Biological Process (BP) 3. Cellular Component (CC)',
            'The Gene Ontology is a controlled vocabulary of terms to represent biology in a structured way.',
        ],
        'b': [
            'Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).',
        ],
        'c': [
            'the GO is "a controlled vocabulary of terms to represent biology in a structured way,"',
        ],
    },
    'process': {
        'a': ['ToolSearch ×2 · link kb-mcp',
              'kb_search_vector ×2 — top 0.75',
              'kb_search_two_stage ×1 — confirm'],
        'b': ['Glob ×1 — 100 exported papers',
              'Grep ×1 — targeted search',
              'Read ×2 — the paper file'],
        'c': ['ToolSearch ×1 · link kb-mcp',
              'kb_search_vector ×1 — chunk recall'],
    },
    'sources': {
        'a': ['Sources: life-sciences base · 1602.01876',
              'part 1 of 2 · §2 verbatim quote'],
        'b': ['Source: …1602.01876__primer-',
              'on-the-gene-ontology.md (§2)'],
        'c': ['Chunks: …gene-ontology__k00.md',
              '(Corpus-Chunks800 index)'],
    },
    'verdicts': {
        'a': 'grounded ✓ · part/section address',
        'b': 'grounded ✓ · file + section name',
        'c': 'grounded ✓ · chunk-level quote',
    },
}

# Panel 2 (BQ06): platform answer vs measured dense abstention.
Q2 = {
    'qid': 'BQ06',
    'question': 'Which physical factor primarily controls the response of precipitation extremes to climate change?',
    'tracks': ['a', 'c'],
    'quotes': {
        'a': [
            'The temperature of the climate (mean surface temperature) is the primary physical factor',
            'roughly, whether the mean surface temperature is above or below ~295 K',
        ],
        'c': [
            'The retrieved chunks do not directly name a single physical factor as the primary control.',
        ],
    },
    'process': {
        'a': ['ToolSearch ×3 · link kb-mcp',
              'kb_search_vector ×5 — recall',
              'kb_doc_read ×2 — verify re-read'],
        'c': ['ToolSearch ×1 · link kb-mcp',
              'kb_search_vector ×1 — chunk recall'],
    },
    'sources': {
        'a': ['Sources: climate-science base · 1503.07557',
              'keyword-verified ✓ (precipitation efficiency)'],
        'c': ['Closest chunk: …1503.07557__k00.md',
              '"Several physical contributions govern…" — no single factor'],
    },
    'verdicts': {
        'a': 'grounded ✓ · keyword-verified answer',
        'c': 'MEASURED ABSTENTION — insufficient retrieved evidence',
    },
}

COLS = {'a': 20, 'b': 346, 'c': 672}
COLS2 = {'a': 20, 'c': 510}
CW = 308
CW2 = 470

ICONS = {
    'a': None,  # drawn inline (library)
    'b': None,  # document
    'c': None,  # magnifier
}


def norm_answer(txt: str) -> str:
    txt = txt.replace('**', '').replace('`', '')
    return re.sub(r'\s+', ' ', txt)


def load_track(trk: str, qid: str) -> dict:
    d = json.loads((RUN / f'track_{trk}_{qid}.json').read_text(encoding='utf-8'))
    assert not d.get('is_error'), f'track {trk} {qid} is_error'
    return d


def check_verbatim(panel: dict, answers: dict) -> None:
    for trk, quotes in panel['quotes'].items():
        hay = norm_answer(answers[trk])
        for q in quotes:
            seg_n = re.sub(r'\s+', ' ', q).strip(' .,')
            assert seg_n in hay, f'not verbatim ({panel["qid"]}/{trk}): {seg_n[:70]!r}'


def check_process(panel: dict, timelines: dict) -> None:
    """Every timeline line must carry an explicit xN count and the counted
    totals must exactly partition the trace's tool_use events — the figure
    is not allowed to elide or inflate tool calls."""
    for trk, lines in panel['process'].items():
        tools = {}
        for e in timelines[trk]:
            if e['event'] == 'tool_use':
                tools[e['detail']] = tools.get(e['detail'], 0) + 1
        assert tools, f'no tool events {panel["qid"]}/{trk}'
        counted = {}
        for ln in lines:
            head = ln.split('—')[0].split('·')[0].split('(')[0].strip()
            m = re.match(r'^(.+?)\s*×(\d+)$', head)
            assert m, f'{panel["qid"]}/{trk}: line without explicit count: {ln!r}'
            name, n = m.group(1).strip().lower(), int(m.group(2))
            cands = [t for t in tools
                     if t.lower() == name or t.lower().split('__')[-1] == name]
            assert cands, f'{panel["qid"]}/{trk}: no trace tool matching {name!r}'
            counted[cands[0]] = counted.get(cands[0], 0) + n
            assert counted[cands[0]] == tools[cands[0]], (
                f'{panel["qid"]}/{trk}: {cands[0]} figure x{counted[cands[0]]} '
                f'vs trace x{tools[cands[0]]}')
        assert sum(counted.values()) == sum(tools.values()), (
            f'{panel["qid"]}/{trk}: figure covers {sum(counted.values())} '
            f'of {sum(tools.values())} tool calls')


def node(tag, **attrs):
    return ET.Element(f'{{{NS}}}{tag}', {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text(x, y, value, size=14, weight=400, anchor='start', fill=INK):
    e = node('text', x=x, y=y, font_size=size, font_weight=weight,
             fill=fill, text_anchor=anchor,
             font_family='Helvetica Neue, Helvetica, Arial, Segoe UI, sans-serif')
    e.text = value
    return e


def icon(trk, x, y, color):
    g = node('g')
    if trk == 'a':
        g.append(node('path', d=f'M{x} {y + 4}l11 -7 11 7z', fill=color))
        g.append(node('rect', x=x, y=y + 4, width=22, height=2.2, fill=color))
        for dx in (3, 9.4, 15.8):
            g.append(node('rect', x=x + dx, y=y + 7, width=3.2, height=8, fill=color))
        g.append(node('rect', x=x, y=y + 15.5, width=22, height=2.2, fill=color))
    elif trk == 'b':
        g.append(node('rect', x=x + 3, y=y - 2, width=15, height=19, rx=1.5,
                      fill='none', stroke=color, stroke_width=1.8))
        for i, dy in enumerate((3, 7, 11)):
            g.append(node('path', d=f'M{x + 6} {y + dy}h{i == 2 and 5 or 9}',
                          stroke=color, stroke_width=1.6))
    else:
        g.append(node('circle', cx=x + 7, cy=y + 5, r=6, fill='none',
                      stroke=color, stroke_width=1.8))
        g.append(node('path', d=f'M{x + 12} {y + 10}l5.5 5.5', stroke=color,
                      stroke_width=2.4))
    return g


def wrap(s, width=46):
    lines, cur = [], ''
    for w in s.split():
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f'{cur} {w}'.strip()
    if cur:
        lines.append(cur)
    return lines


def panel_header(g, panel, y, cols, cw):
    g.append(text(20, y, f'QUESTION {panel["qid"]} · {panel["question"]}', 15.5, 600, fill=SUB))
    hy = y + 12
    for trk, x in cols.items():
        st = STYLE[trk]
        g.append(node('rect', x=x, y=hy, width=cw if cw < 900 else CW, height=38, rx=4,
                      fill=st['fill'], stroke='#c5cfd5'))
        g.append(icon(trk, x + 12, hy + 6, INK))
        g.append(text(x + 42, hy + 18, st['label'], 15, 700))
        g.append(text(x + 42, hy + 34, st['route'], 15, fill=SUB))
    return hy + 38


def panel_body(g, panel, y0, cols, cw, wrap_w=40):
    """One card per column: timeline / verbatim excerpt / sources separated by
    thin dividers instead of three separate boxes (compact layout)."""
    wrapped = {}
    for trk in cols:
        frag = panel['quotes'][trk][0]
        lines = wrap('\u201c\u2026' + frag, wrap_w)
        tail = '\u2026\u201d' if not frag.rstrip().endswith(('.', '!', '?')) else '\u201d'
        lines[-1] = lines[-1] + tail
        wrapped[trk] = lines
    qn = max(len(v) for v in wrapped.values())
    sn = max(len(panel['sources'][trk]) for trk in cols)
    P, SP = 19, 18
    label1_b = y0 + 19
    proc0_b = label1_b + 19
    div1_y = proc0_b + 2 * P + 8
    label2_b = div1_y + 16
    quote0_b = label2_b + 19
    div2_y = quote0_b + (qn - 1) * P + 8
    src0_b = div2_y + 17
    verdict_b = src0_b + (sn - 1) * SP + 20
    card_h = verdict_b - y0 + 6
    for trk, x in cols.items():
        st = STYLE[trk]
        g.append(node('rect', x=x, y=y0, width=cw, height=card_h, rx=4,
                      fill=st['box'], stroke='#c5cfd5'))
        g.append(text(x + 10, label1_b, 'HOW IT SEARCHED — TIMELINE', 15, 700, fill=SUB))
        py = proc0_b
        for ln in panel['process'][trk]:
            g.append(node('circle', cx=x + 14, cy=py - 5, r=2.4, fill=st['dot']))
            g.append(text(x + 23, py, ln, 15))
            py += P
        g.append(node('path', d=f'M{x + 10},{div1_y} H{x + cw - 10}',
                      stroke='#dbe3e8', stroke_width=1))
        g.append(text(x + 10, label2_b, 'VERBATIM ANSWER EXCERPT', 15, 700, fill=SUB))
        ty = quote0_b
        for line in wrapped[trk]:
            g.append(text(x + 10, ty, line, 15))
            ty += P
        g.append(node('path', d=f'M{x + 10},{div2_y} H{x + cw - 10}',
                      stroke='#dbe3e8', stroke_width=1))
        sy = src0_b
        for line in panel['sources'][trk]:
            g.append(text(x + 10, sy, line, 15, weight=600))
            sy += SP
        g.append(text(x + 10, verdict_b, panel['verdicts'][trk], 15, 600, fill=st['dot']))
    return y0 + card_h


def build_svg(panels):
    root = node('svg', xmlns=NS, width=1000, height=700, viewBox='0 0 1000 700',
                role='img', **{'aria-labelledby': 'title desc'})
    root.append(node('title', id='title'))
    root.find(f'{{{NS}}}title').text = 'Two questions answered under three retrieval modes'
    desc = node('desc', id='desc')
    desc.text = (
        'Verbatim answer excerpts, saved tool timelines, and source references from the '
        'monitored three-mode run over the 100-paper corpus; all modes used the same agent '
        'harness, model, and chat endpoint. Panel 1 (BQ04): all three modes answer the Gene '
        'Ontology question; the platform quotes the source passage verbatim and addresses it '
        'as part 1 of 2, section 2; the bare agent names the file and section; the dense mode '
        'quotes chunks. Panel 2 (BQ06): the platform answers the precipitation-extremes '
        'question (mean surface temperature, keyword-verified) after a verification re-read, '
        'while the dense mode returns a measured abstention because its chunks name no single '
        'physical factor. Ellipses elide text; markdown emphasis removed; source lines condensed.')
    root.append(desc)
    g = node('g', font_family='Helvetica Neue, Helvetica, Arial, Segoe UI, sans-serif')
    root.append(g)
    g.append(node('rect', width=1000, height=700, fill='white'))

    y = 20
    y = panel_header(g, Q1, y, COLS, CW)
    y = panel_body(g, Q1, y + 8, COLS, CW, wrap_w=40)
    y += 16
    y = panel_header(g, Q2, y, COLS2, CW2)
    y = panel_body(g, Q2, y + 8, COLS2, CW2, wrap_w=58)
    y += 14
    y = metrics_strip(g, y)
    H = int(y + 14)
    root.set('height', str(H))
    root.set('viewBox', f'0 0 1000 {H}')
    return root, H


def metrics_strip(g, y):
    """Bottom strip: the run's aggregate metrics, read live from the grading
    artifacts and asserted (replaces the manuscript's floating results table)."""
    grade = json.loads((ROOT / 'benchmark-suite' / 'results' / 'exp_r2_grade.json').read_text(encoding='utf-8'))
    aud = json.loads((RUN / 'audit_paper_numbers.json').read_text(encoding='utf-8'))
    gr = grade['grades']
    rows = [
        ('Grounded* (cites designated paper)', [str(gr[t]['gold_hit']) + '/10' for t in 'abc']),
        ('Keyword-verified (>=60% gold key facts)', [str(gr[t]['kw_ok']) + '/10' for t in 'abc']),
        ('Part/section-level citations', []),
        ('Mean latency (s)', [str(gr[t]['avg_latency_s']) for t in 'abc']),
        ('Mean tool calls', [str(gr[t]['avg_tools']) for t in 'abc']),
        ('Cost per question (USD)', [str(gr[t]['avg_cost_usd']) for t in 'abc']),
    ]
    import re as _re
    pat = _re.compile(r'part \d|§\s?\d|section \d|sections \d|table \d', _re.I)
    cites = {}
    for t in 'abc':
        n = 0
        for f in sorted(RUN.glob(f'track_{t}_*.json')):
            d = json.loads(f.read_text(encoding='utf-8'))
            blob = str(d.get('answer') or '') + '\n' + '\n'.join(d.get('texts_full') or [])
            if pat.search(blob):
                n += 1
        cites[t] = n
    rows[2] = ('Part/section-level citations', [str(cites[t]) + '/10' for t in 'abc'])
    # assertions: figure numbers must match the audited artifacts
    assert rows[0][1] == ['9/10', '10/10', '9/10'], rows[0]
    assert rows[1][1] == ['9/10', '6/10', '6/10'], rows[1]
    assert rows[2][1] == ['7/10', '4/10', '1/10'], rows[2]
    for t in 'abc':
        assert gr[t]['avg_latency_s'] == aud['per_track'][t]['avg_latency_s']
        assert abs(gr[t]['avg_cost_usd'] - aud['per_track'][t]['cost_usd_total'] / 10) < 0.001

    g.append(node('rect', x=20, y=y, width=960, height=24, rx=2, fill='#253745'))
    g.append(text(30, y + 17, 'MONITORED RUN — 10 QUESTIONS × 3 MODES · ONE HARNESS AND MODEL', 15, 700, fill='#ffffff'))
    g.append(text(970, y + 17, 'A Platform · B Bare agent · C Dense', 15, 600, anchor='end', fill='#ffffff'))
    y += 28
    # 2×3 grid: each cell = metric name + A/B/C values, three metrics per row
    # (mode columns are named in the figure caption: Platform, Bare agent, Dense)
    cells = [(rows[0], rows[1]), (rows[3], rows[4]), (rows[2], rows[5])]
    short = {'Grounded* (cites designated paper)': 'Grounded (cites paper)',
             'Keyword-verified (>=60% gold key facts)': 'Keyword-verified',
             'Mean latency (s)': 'Mean latency (s)',
             'Mean tool calls': 'Mean tool calls',
             'Part/section-level citations': 'Part/section citations',
             'Total cost (USD)': 'Total cost (USD)'}
    for left, right in cells:
        for xx, (name, vals) in ((20, left), (505, right)):
            g.append(node('rect', x=xx, y=y, width=475, height=24, rx=2,
                          fill='#f4f7f9', stroke='#dfe7ec'))
            g.append(text(xx + 10, y + 16.5, short.get(name, name), 15))
            for i, v in enumerate(vals):
                g.append(text(xx + 250 + i * 72, y + 17, v, 15, 600, fill=INK))
        y += 25
    return y + 4


def main():
    answers, tls = {}, {}
    for qid, tracks in ((Q1['qid'], 'abc'), (Q2['qid'], 'ac')):
        for trk in tracks:
            d = load_track(trk, qid)
            answers[(qid, trk)] = d['answer']
            tls[(qid, trk)] = d['timeline']
    check_verbatim(Q1, {t: answers[(Q1['qid'], t)] for t in 'abc'})
    check_verbatim(Q2, {t: answers[(Q2['qid'], t)] for t in 'ac'})
    check_process(Q1, {t: tls[(Q1['qid'], t)] for t in 'abc'})
    check_process(Q2, {t: tls[(Q2['qid'], t)] for t in 'ac'})
    root, H = build_svg(None)
    source = ET.tostring(root, encoding='unicode')
    assert '<image' not in source and '<foreignObject' not in source
    assert not re.search(r'[\u4e00-\u9fff]', source), 'CJK character found in figure'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'fig3-answers-dual.svg').write_text(source, encoding='utf-8')
    html = (f'<!doctype html><html lang="en"><meta charset="utf-8"><title>fig3-answers-dual</title>'
            f'<style>@page{{size:1000px {H}px;margin:0}}html,body{{margin:0;width:1000px;height:{H}px}}'
            f'svg{{display:block}}</style>{source}</html>')
    (OUT / 'fig3-answers-dual.html').write_text(html, encoding='utf-8')
    report = {'source': f'{RUN.name} traces (BQ04 a/b/c + BQ06 a/c)',
              'verbatim_check': 'all quoted fragments are normalized substrings of saved answers',
              'process_check': 'timelines fully counted from saved tool_use events; every xN asserted against the trace',
              'runtime': {'playwright': version('playwright'), 'PyMuPDF': version('PyMuPDF')}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        report['runtime']['chromium'] = browser.version
        page = browser.new_page(viewport={'width': 1000, 'height': H}, device_scale_factor=2)
        page.goto((OUT / 'fig3-answers-dual.html').as_uri())
        page.evaluate('document.fonts.ready')
        checks = page.evaluate('''() => {
            const svg=document.querySelector('svg'), s=svg.getBoundingClientRect();
            const ts=[...svg.querySelectorAll('text')];
            const rects=[...svg.querySelectorAll('rect')].map(r=>r.getBoundingClientRect());
            const boxOverflow=ts.filter(t=>{const b=t.getBoundingClientRect();
                const host=rects.find(r=>r.width<900&&b.left+b.width/2>=r.left&&b.left+b.width/2<=r.right&&b.top>=r.top-2&&b.top<=r.bottom);
                return host&&(b.right>host.right-3||b.bottom>host.bottom+2);}).map(t=>t.textContent);
            return {minimum_font_px:Math.min(...ts.map(t=>parseFloat(getComputedStyle(t).fontSize))),
                out_of_bounds:ts.filter(t=>{const b=t.getBoundingClientRect();return b.left<s.left||b.top<s.top||b.right>s.right||b.bottom>s.bottom}).map(t=>t.textContent),
                box_overflow:boxOverflow,
                overlaps:ts.flatMap((a,i)=>ts.slice(i+1).filter(b=>{let x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return Math.min(x.right,y.right)-Math.max(x.left,y.left)>1&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>1}).map(b=>[a.textContent,b.textContent]))};
        }''')
        assert checks['minimum_font_px'] >= 14.9, checks
        assert not checks['out_of_bounds'] and not checks['overlaps'], checks
        assert not checks['box_overflow'], checks
        page.locator('svg').screenshot(path=str(OUT / 'fig3-answers-dual.png'))
        page.pdf(path=str(OUT / 'fig3-answers-dual.pdf'), width='1000px', height=f'{H}px',
                 print_background=True, prefer_css_page_size=True,
                 margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
        page.close()
        with fitz.open(OUT / 'fig3-answers-dual.pdf') as pdf:
            pdf[0].set_mediabox(fitz.Rect(0, 0, 750, H * .75))
            trimmed = pdf.tobytes()
        (OUT / 'fig3-answers-dual.pdf').write_bytes(trimmed)
        with fitz.open(OUT / 'fig3-answers-dual.pdf') as pdf:
            pg = pdf[0]
            assert not pg.get_images(full=True), 'Raster image in PDF'
            assert len(pg.get_text()) > 300 and len(pg.get_drawings()) >= 10
            for font in pg.get_fonts(full=True):
                if font[2] != 'Type3':
                    assert pdf.extract_font(font[0])[3], f'Unembedded font: {font}'
            checks.update(pdf_mediabox=list(pg.mediabox), pdf_images=0,
                          pdf_vector_paths=len(pg.get_drawings()))
            pg.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(OUT / 'fig3-answers-dual-pdf-proof.png')
        report['checks'] = checks
        browser.close()
    (OUT / 'verification-dual.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'PASS fig3-answers-dual: verbatim quotes + tool timelines verified; H={H}; vector PDF, fonts embedded')


if __name__ == '__main__':
    main()
