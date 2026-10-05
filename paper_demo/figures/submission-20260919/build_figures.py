"""Build the submission figures from frozen approved SVG inputs.

Run: python paper_demo/figures/submission-20260919/build_figures.py
Requires Python, playwright (Chromium installed), and PyMuPDF.
Only writes within this directory. PDFs retain paths and embedded selectable text.
"""
from pathlib import Path
import ast
import hashlib
from importlib.metadata import version
import json
import xml.etree.ElementTree as ET

import fitz
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
INK = '#253745'


def node(tag, **attrs):
    return ET.Element(f'{{{NS}}}{tag}', {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text(x, y, value, size=18, weight=400, anchor='start'):
    e = node('text', x=x, y=y, font_size=size, font_weight=weight,
             fill=INK, text_anchor=anchor, font_family='Calibri, Carlito, sans-serif')
    e.text = value
    return e


def box(x, y, width, height, fill):
    return node('rect', x=x, y=y, width=width, height=height, rx=3,
                fill=fill, stroke='#c5cfd5')


def arrow(path):
    return node('path', d=path, fill='none', stroke=INK,
                stroke_width=1.4, marker_end='url(#arrow)')


def load(name):
    return ET.parse(OUT / 'inputs' / name).getroot()


def resize(root, height):
    root.set('height', str(height))
    root.set('viewBox', f'0 0 1000 {height}')
    for e in root:
        if e.tag.endswith('rect') and e.get('width') == '1000':
            e.set('height', str(height))


def concept():
    root = load('fig1-concept-draft.svg')
    resize(root, 590)
    g = root.find(f'{{{NS}}}g')
    # Retain the approved shared query and both retrieval paths through the gate.
    tail = next(i for i, e in enumerate(g) if e.tag.endswith('path') and e.get('d') == 'M650 363H615V435H426V458')
    for e in list(g)[tail:]:
        g.remove(e)
    for e in g:
        if e.tag.endswith('rect') and e.get('x') == '512' and e.get('y') == '94':
            e.set('height', '468')
        if e.tag.endswith('text'):
            e.text = {'QDCVR': 'QDCVR (agent-executed skill)',
                      '800-char chunks': '≈800-character windows',
                      'Dense retrieval → top 2': 'Dense retrieval → pack 2 excerpts',
                      '4,000-char evidence window': '≤4,000-character evidence window'}.get(e.text, e.text)
    additions = [
        arrow('M650 363H551V502'), text(563,398,'≥6: direct',16,600),
        arrow('M842 363H935V407'), text(849,400,'Initial <6',16,600),
        box(652,413,308,54,'#f7efdf'),
        text(666,435,'Librarian fallback',20,600),
        text(666,457,'Keep 5; discard ≤4; read + recheck',16),
        arrow('M677 467V478H612V502'), text(626,497,'P0 ≥6',14),
        arrow('M752 467V502'), text(772,492,'P1 =5',14),
        arrow('M901 467V502'), text(913,486,'No usable',14), text(913,502,'P0/P1',14),
        box(532,508,140,48,'#e7f3ec'),
        text(542,527,'Cited answer',17,600), text(542,549,'Sources + limits',16),
        box(680,508,145,48,'#efedf7'),
        text(690,527,'Qualified answer',16,600), text(690,549,'With attribution',16),
        box(833,508,127,48,'#f7efdf'),
        text(843,527,'Not found',17,600), text(843,549,'Scoped report',16),
        text(40,470,'Compared configurations,',20,600),
        text(40,497,'not a claim of accuracy superiority.',19),
        text(20,582,'0–8 rubric: ≥6 direct; usable P1 =5 may support an attributed answer after fallback. Scores are agent judgments.',16),
        # lane accent bars (visual polish: blue = dense baseline, teal = QDCVR)
        node('rect', x=20, y=94, width=468, height=4, fill='#6c86a8'),
        node('rect', x=512, y=94, width=468, height=4, fill='#2f7d5f'),
    ]
    g.extend(additions)
    root.find(f'{{{NS}}}desc').text = (
        'BQ02 shared NISQ query. Left: current reproduction scripts use approximately 800-character windows, '
        'retrieve ten candidates, then pack two excerpts within a 4,000-character budget for single generation; provenance is not logged '
        'by this harness. Right: an agent executes QDCVR, reads candidates and self-assesses them on a 0–8 '
        'rubric. Initial score ≥6 yields a direct cited answer; score 5 is retained as a P1 backstop and scores ≤4 are discarded while fallback runs. '
        'After librarian fallback and read/recheck, P0 ≥6 supports a cited answer; usable P1 score 5 supports a qualified answer with attribution, including a retained backstop. '
        'Only no usable P0/P1 evidence yields a scoped not-found report. All QDCVR outcomes remain within the right-hand lane. This is not an accuracy comparison.')
    return root


def architecture():
    root = load('direction-b.svg')
    resize(root, 590)
    root.find(f'{{{NS}}}title').text = 'Platform services and agent-executed QDCVR workflow'
    root.find(f'{{{NS}}}desc').text = (
        'Web search uses HTTP, ragctl handles setup and services, and agents use an MCP adapter to shared backend primitives. '
        'The packaged agent skills execute content classification, the QDCVR gate and retry policy; these are '
        'not automatically enforced on every web or HTTP search. Web uploads use a selected destination; this diagram shows agent-assisted ingestion, not automatic routing of all uploads. Offline: MinerU parses PDFs into section '
        'Markdown; an agent reads and routes content into five demo bases and selects or propagates tags, with deterministic split, index and store primitives. This is not a guarantee that every MCP-created part is tagged. Evidence is stored '
        'using ChromaDB/BGE-M3, Neo4j and YAML metadata. Online agent-executed QDCVR: query rewrite, '
        'vector-first cross-base recall, candidate reading, and a 0–8 rubric. Initial ≥6 supports direct answering; initial score 5 is retained as a P1 backstop, while ≤4 is discarded; both trigger fallback. '
        'After reading and rechecking, P0 ≥6 supports a cited answer, usable P1 score 5 supports an attributed qualified answer, and only no usable P0/P1 supports not-found. Tools/backend supply the capabilities, not automatic policy enforcement.')
    replacements = {
        'Web console · ragctl CLI': 'Web HTTP / CLI setup',
        'MCP agents · 41 kb_* tools': 'Agents → MCP adapter',
        'FastAPI / shared platform': 'Backend / storage primitives',
        'Read content': 'Agent reads / routes',
        'Classify into 5 bases': 'Selects / propagates tags',
        'Parts + section paths': 'Split / index / store',
        'Propagate tags': 'Retain section paths',
        'Neo4j · YAML audit': 'File tree + YAML metadata',
        'ChromaDB / BGE-M3': 'ChromaDB / BGE-M3 · Neo4j',
        '(a) Offline indexing': '(a) Agent-assisted ingest',
        'Content gate': 'Content rubric',
        '0–8; any ≥ 6?': '0–8 score',
        'Pass': '≥6: direct',
        'Initial: none passes': 'Initial <6: fallback',
        'After fallback:': 'After fallback:',
        'none passes': 'No usable P0/P1',
    }
    # Open one line below the two workflow headings without shrinking any glyphs.
    body = node('g', transform='translate(0 22)')
    active = False
    for e in list(root):
        if e.tag.endswith('text'):
            e.text = replacements.get(e.text, e.text)
            e.set('font-family', 'Calibri, Carlito, sans-serif')
            if float(e.get('font-size', '16')) < 16:
                e.set('font-size', '16')
        if e.tag.endswith('rect') and e.get('y') == '76':
            e.set('height', '494')
        if e.tag.endswith('path') and (e.get('d') or '').startswith('M35 126'):
            active = True
        if active:
            root.remove(e)
            body.append(e)
    body.extend([
        box(300,238,174,67,'#efedf7'),
        text(387,263,'Qualified answer',18,600,anchor='middle'),
        text(387,287,'With attribution',16,anchor='middle'),
        node('polyline',points='501,364 470,364 470,309',fill='none',stroke='#607580',stroke_width=1.3,marker_end='url(#b-arrow)'),
        text(306,330,'After fallback:',16), text(306,351,'Usable P1 =5',16,600),
        text(572,458,'5 retained; ≤4 discarded',16),
    ])
    root.append(body)
    root.append(text(295,119,'Agent-executed QDCVR skill',18,600))
    root.append(text(30,119,'Demo: five category bases',16))
    root.append(text(20,586,'Skills execute gate / retry / classification; web or HTTP search does not automatically enforce this policy.',16))
    return root


def evidence():
    root = load('fig3-evidence-draft.svg')
    resize(root, 590)
    root.find(f'{{{NS}}}desc').text = (
        'Tool records and agent-authored summaries, not an autonomous benchmark or matched efficacy comparison. '
        'Current BQ01 evidence: parts 1/2 §3.2.3 and 2/2 §7, recorded gate 8/8. Declared unread material: positional formula, training details and benchmark scores. '
        'B file sources are self-reported, not an observed file-read trace. C reports parsing and Table 4, abstains, and logs two excerpts with 2,854 characters but no usable chunk-to-document metadata. '
        'The bottom row is a scripted P2 probe record: script-collected retrieval and catalog evidence, predefined agent-authored judgment 1/8, and a templated saved NOT_FOUND report. '
        'The BERT epoch near miss concerns another paper. Catalog census: five bases, 165 entries, only 153 names retained; no exhaustive body reading is evidenced. '
        'The saved report is scoped, not proof of absence or an observed autonomous decision. Scores are recorded agent judgments, not accuracy.')
    for e in root.iter(f'{{{NS}}}text'):
        changes = {
            'Fabricated-paper probe: asks about training epochs':'Scripted probe record · fabricated-paper question about training epochs',
            'Gate: 1/8':'Recorded: 1/8',
            'Read → reject':'Agent judgment',
            'Librarian scan':'Catalog census',
            '5 bases · 165 indexed docs':'5 bases · 165 entries',
            '50 papers':'153 names retained',
            'NOT FOUND':'Saved report:',
            'Scope reported':'NOT_FOUND',
            'Gate scores: LLM self-assessments, not accuracy.':'Scores are recorded agent judgments, not independent accuracy measurements.',
        }
        e.text = changes.get(e.text,e.text)
        if e.text == 'Recorded: 1/8':
            e.set('font-size','19')
        if e.text == 'Saved report:':
            e.set('font-size','19')
        if e.text == 'Scores are recorded agent judgments, not independent accuracy measurements.':
            e.set('font-size','16')
        if e.text == 'Trace evidence':
            e.text = 'Saved evidence trace'
        if e.text == 'Current run · answer summaries and trace labels are paraphrases.':
            e.text = 'Tool records + agent-authored summaries; not an autonomous benchmark.'
        if e.text == 'Unread: positional formula,':
            e.text = 'Declared unread: positional formula,'
            e.set('font-size', '18')
        if e.text == 'Gate scores: LLM self-assessments, not accuracy.':
            e.set('font-size', '16')
    return root


def find_record(filename, key, value):
    data = json.loads((ROOT / 'benchmark-suite' / 'results' / filename).read_text(encoding='utf-8'))
    def walk(item):
        if isinstance(item, dict):
            if item.get(key) == value:
                return item
            children = item.values()
        elif isinstance(item, list):
            children = item
        else:
            return None
        for child in children:
            result = walk(child)
            if result is not None:
                return result
        return None
    result = walk(data)
    assert result is not None, (filename, key, value)
    return result


def find_frozen(filename, key, value):
    data = json.loads((OUT / 'inputs' / filename).read_text(encoding='utf-8'))
    def walk(item):
        if isinstance(item, dict):
            if item.get(key) == value:
                return item
            children = item.values()
        elif isinstance(item, list):
            children = item
        else:
            return None
        for child in children:
            result = walk(child)
            if result is not None:
                return result
        return None
    result = walk(data)
    assert result is not None, (filename, key, value)
    return result


def verify_sources():
    skill = (ROOT/'.claude/skills/knowledgebase-search/SKILL.md').read_text(encoding='utf-8')
    for phrase in ('Keep as **P1 backstop**', 'adopt with attribution', 'answer from the backstop', 'yields no P0/P1'):
        assert phrase in skill, phrase
    shelf = find_record('probe_evidence_raw.json','pid','P2')['phase2_librarian']['shelf']
    assert len(shelf) == 5 and sum(x['n_docs'] for x in shelf) == 165
    assert sum(len(x['names']) for x in shelf) == 153
    judge = ast.parse((ROOT/'benchmark-suite/scripts/80_honest_probe_judge.py').read_text(encoding='utf-8-sig'))
    judgments = next(n for n in judge.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'JUDGMENT' for t in n.targets))
    assert sum(ast.literal_eval(judgments.value)['P2'][:3]) == 1
    corpus = ast.parse((ROOT/'benchmark-suite/algorithms/corpus.py').read_text(encoding='utf-8-sig'))
    chunker = next(n for n in corpus.body if isinstance(n,ast.FunctionDef) and n.name == 'chunk_fixed')
    assert [ast.literal_eval(n) for n in chunker.args.defaults] == [800,400]
    methods = ast.parse((ROOT/'benchmark-suite/algorithms/methods.py').read_text(encoding='utf-8-sig'))
    budget = next(n for n in methods.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'BUDGET' for t in n.targets))
    assert ast.literal_eval(budget.value) == 4000
    # fig3-evidence renders the 2026-09-19 approved saved case; the live
    # results/ files are overwritten by later runs, so assertions read the
    # frozen copies (commit 8e56951) recorded in inputs/. fig3-evidence is a
    # legacy asset: the manuscript now includes fig3-answers (submission-20260920).
    assert find_frozen('frozen-skill_track_answers.json','qid','BQ01')['gate']['score'] == 8
    assert find_record('honest_failure_probe.json','pid','P2')['gate']['score'] == '1/8'
    assert find_record('honest_failure_probe.json','pid','P2')['verdict'] == 'NOT_FOUND'
    c = find_frozen('frozen-track_bc.json','qid','BQ01')['track_c_dense_rag']
    assert (c['evidence_chunks'], c['evidence_chars'], c['evidence_docs']) == (2,2854,[])
    hits = find_frozen('frozen-skill_track_evidence.json','qid','BQ01')['hits']
    assert any('part 1 of 2' in h['doc_path'] and '3.2.3' in h['chunk_text'] for h in hits)
    assert any('part 2 of 2' in h['doc_path'] and '7 Conclusion' in h['chunk_text'] for h in hits)


def main():
    verify_sources()
    report = {'source_assertions':'passed',
              'runtime':{'playwright':version('playwright'),'PyMuPDF':version('PyMuPDF')}, 'architecture_audit':'SYSTEM-AUDIT, EVIDENCE-AUDIT, CONTENT-REVIEW and packaged search skill applied (2026-09-19)',
              'policy_sha256':hashlib.sha256((ROOT/'.claude/skills/knowledgebase-search/SKILL.md').read_bytes()).hexdigest(),
              'content_review_sha256':hashlib.sha256((ROOT/'paper_demo/review/submission-revision-20260919/CONTENT-REVIEW.md').read_bytes()).hexdigest(),
              'audit_sha256': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'paper_demo/review/submission-revision-20260919').glob('*AUDIT.md')},
              'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((OUT/'inputs').glob('*.svg'))}, 'figures':{}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        report['runtime']['chromium'] = browser.version
        for name, root in [('fig1-concept',concept()),('fig2-architecture',architecture()),('fig3-evidence',evidence())]:
            source = ET.tostring(root, encoding='unicode')
            assert '7/8' not in source and '<image' not in source and '<foreignObject' not in source
            assert root.find(f'{{{NS}}}desc').text
            assert '800-char chunks' not in source and 'Dense retrieval → top 2' not in source
            assert 'YAML audit' not in source
            labels = [e.text for e in root.iter(f'{{{NS}}}text')]
            if name != 'fig3-evidence':
                assert 'Qualified answer' in labels and 'With attribution' in labels
                assert any('P1 =5' in t for t in labels)
                assert any('P0/P1' in t for t in labels)
                assert 'none passes' not in labels
            else:
                for phrase in ('Recorded: 1/8','Agent judgment','Catalog census','5 bases · 165 entries','153 names retained','Saved report:','NOT_FOUND'):
                    assert phrase in labels, phrase
                assert not any('indexed docs' in t or 'Librarian scan' in t for t in labels)
            (OUT/f'{name}.svg').write_text(source, encoding='utf-8')
            height = int(root.get('height'))
            html = f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{name}</title><style>@page{{size:1000px {height}px;margin:0}}html,body{{margin:0;width:1000px;height:{height}px}}svg{{display:block}}</style>{source}</html>'
            (OUT/f'{name}.html').write_text(html, encoding='utf-8')
            page = browser.new_page(viewport={'width':1000,'height':height}, device_scale_factor=2)
            page.goto((OUT/f'{name}.html').as_uri())
            page.evaluate('document.fonts.ready')
            checks = page.evaluate('''() => {
                const svg=document.querySelector('svg'), s=svg.getBoundingClientRect();
                const ts=[...svg.querySelectorAll('text')];
                return {minimum_font_px:Math.min(...ts.map(t=>parseFloat(getComputedStyle(t).fontSize))),
                    out_of_bounds:ts.filter(t=>{const b=t.getBoundingClientRect();return b.left<s.left||b.top<s.top||b.right>s.right||b.bottom>s.bottom}).map(t=>t.textContent),
                    overlaps:ts.flatMap((a,i)=>ts.slice(i+1).filter(b=>{let x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return Math.min(x.right,y.right)-Math.max(x.left,y.left)>1&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>1}).map(b=>[a.textContent,b.textContent]))};
            }''')
            assert checks['minimum_font_px'] >= 14, checks
            assert not checks['out_of_bounds'] and not checks['overlaps'], checks
            page.locator('svg').screenshot(path=str(OUT/f'{name}.png'))
            page.pdf(path=str(OUT/f'{name}.pdf'), width='1000px',height=f'{height}px',
                     print_background=True,prefer_css_page_size=True,margin={'top':'0','right':'0','bottom':'0','left':'0'})
            page.close()
            # Chromium rounds CSS paper heights; trim to the exact SVG page box.
            with fitz.open(OUT/f'{name}.pdf') as pdf:
                pdf[0].set_mediabox(fitz.Rect(0,0,750,height*.75))
                trimmed = pdf.tobytes()
            (OUT/f'{name}.pdf').write_bytes(trimmed)
            with fitz.open(OUT/f'{name}.pdf') as pdf:
                assert len(pdf) == 1
                pg = pdf[0]
                assert abs(pg.rect.width - 750) < 1 and abs(pg.rect.height-height*.75) < 1
                assert not pg.get_images(full=True), 'Raster image found in PDF'
                assert len(pg.get_text()) > 300 and len(pg.get_drawings()) > 10
                fonts = []
                for font in pg.get_fonts(full=True):
                    data = pdf.extract_font(font[0])
                    assert data[3], f'Unembedded font: {font}'
                    fonts.append({'name':font[3], 'embedded_bytes':len(data[3])})
                spans = [s for b in pg.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
                checks.update(pdf_mediabox=list(pg.mediabox),pdf_images=0,pdf_vector_paths=len(pg.get_drawings()),
                              pdf_selectable_characters=len(pg.get_text()),pdf_fonts=fonts,
                              minimum_print_font_pt_at_504pt=min(s['size'] for s in spans)*504/pg.rect.width)
                pg.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(OUT/f'{name}-pdf-proof.png')
                pg.get_pixmap(matrix=fitz.Matrix(504/750,504/750),alpha=False).save(OUT/f'{name}-504pt-proof.png')
            report['figures'][name] = checks
            print(f'PASS {name}: vector PDF, embedded fonts, selectable text, no text overlaps or clipping')
        browser.close()
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS packaged P1 fallback policy; scripted P2 judgment; census 165 / retained names 153; unchanged BQ01 8/8 and C metadata')


if __name__ == '__main__':
    main()
