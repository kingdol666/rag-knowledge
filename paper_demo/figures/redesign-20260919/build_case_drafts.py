"""Build two editable, source-scoped academic figure drafts and browser previews.

Only writes fig1-concept-draft and fig3-evidence-draft SVG/HTML/PNG/PDF here.
Evidence: benchmark-suite/results/{bench10_qa,skill_track_evidence,
skill_track_answers,track_bc,honest_failure_probe}.json. Historical caveat:
archive-20260917-10000chunk/skill_track_answers.json, BQ01. The current
BQ01 score is 8, NOT 7; archived 7/8 must not be paired with current parts.
"""
from pathlib import Path
from html import escape
import json
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INK = '#253745'
BLUE = '#eaf2f9'
GREEN = '#e7f3ec'
SAND = '#f7efdf'
LAV = '#efedf7'


def text(x, y, value, size=18, weight=400, fill=INK, anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(value)}</text>'


def rect(x, y, w, h, fill='white', stroke='#c5cfd5'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" stroke="{stroke}"/>'


def arrow(path):
    return f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="1.4" marker-end="url(#arrow)"/>'


def doc(x, y, w=70, h=88, fill=BLUE, section=False):
    s = f'<path d="M{x},{y}h{w-14}l14,14v{h-14}h-{w}Z" fill="white" stroke="{INK}" stroke-width="1.2"/><path d="M{x+w-14},{y}v14h14" fill="none" stroke="{INK}"/>'
    for i in range(3 if h >= 80 else 2):
        s += rect(x+9, y+23+i*18, w-18, 10, fill, 'none')
    if section:
        s += text(x+12,y+32,'§',14,600)+text(x+12,y+50,'§',14,600)+text(x+12,y+68,'§',14,600)
    return s


def svg(title, desc, height, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L8 4L0 8" fill="{INK}"/></marker></defs>
<rect width="1000" height="{height}" fill="white"/>
<g font-family="Calibri, Carlito, sans-serif">{content}</g></svg>'''


CAPTIONS = {
    'fig1-concept-draft': 'Draft Figure 1. Process comparison for the same NISQ query (BQ02). Dense RAG denotes our reproduction: 800-character fixed chunks, top-2 retrieval, a 4,000-character evidence window and one generation call. Missing provenance is a harness logging limitation, not an intrinsic property of dense retrieval. QDCVR recalls organized, section-addressed evidence, reads candidates against a 0–8 rubric, and passes at ≥6; failure invokes librarian fallback and rechecking before a cited answer or a scoped not-found report. The diagram describes control flow, not measured superiority. Gate scores are execution-LLM self-assessments. Original manuscript caption must be corrected after approval; the manuscript is unchanged.',
    'fig3-evidence-draft': 'Draft Figure 3. Current 30k-run BQ01 evidence trace and P2 rejection probe; all prose is shorthand or paraphrase, not a verbatim answer quotation. A: Trace evidence maps current document parts 1/2 and 2/2 to §3.2.3 and §7 using skill_track_evidence.json, not verbatim answer citations; the current recorded gate is 8/8. Current blind spots concern the positional-encoding formula, training hyperparameters and benchmark scores, not an unread scaled-dot-product formula. B: the recorded answer gives more complete formula prose, but files_used is self-reported and does not demonstrate file reads. C: the generated answer reports parsing experiments and Table 4 and declares insufficient evidence; those input contents were not independently inspected, and the logged evidence_docs array is empty; chunking is only a hypothesis, since ranks and chunk-to-document provenance were not logged. P2 rejects BERT training-epoch text belonging to a different paper and reports a scan of 5 bases, 50 papers and 165 indexed documents. Gate scores: LLM self-assessments, not accuracy. This selected case illustrates traceability, not independent or universal accuracy. Archived-run distinctions are documented only in SOURCE-AUDIT.md. Original manuscript caption must be corrected after approval; the manuscript is unchanged.'
}


def fig1():
    s = rect(20,16,960,48,BLUE)
    s += text(36,46,'BQ02 · What defines NISQ technology and what is its central limitation?',21,600)
    s += arrow('M500 64V79H254V92')+arrow('M500 79H746V92')
    s += rect(20,94,468,324,'#fafbfc')+rect(512,94,468,324,'#fbfdfb')
    s += text(36,123,'Dense RAG (our reproduction)',23,700)
    s += text(528,123,'QDCVR',23,700)
    s += doc(40,140,57,85,BLUE)
    for x,y in [(120,146),(132,172),(115,198)]:
        s += rect(x,y,65,17,BLUE)+f'<path d="M{x+8} {y+8}h42" stroke="#7590a6"/>'
    s += arrow('M99 182H116')
    s += text(213,169,'800-char chunks',21,600)+text(213,199,'Fixed fragments',20)
    s += arrow('M254 226V240')
    s += rect(40,246,428,59,BLUE)+text(56,270,'Dense retrieval → top 2',21,600)
    s += text(56,295,'4,000-char evidence window',20)
    s += arrow('M254 305V324')
    s += rect(40,330,428,40,LAV)+text(56,357,'Single generation → answer',21,600)
    s += text(40,400,'Provenance not logged in this harness.',20)
    s += doc(532,140,57,85,GREEN,True)
    s += text(607,168,'Organized, section-addressed parts',20,600)
    s += text(607,198,'base / document / part / section',19)
    s += arrow('M746 226V240')
    s += rect(532,246,428,59,GREEN)+text(548,270,'Vector-first recall',21,600)
    s += text(548,295,'Read candidate text; score 0–8',20)
    s += arrow('M746 305V324')
    s += f'<path d="M746 330L842 363L746 396L650 363Z" fill="{GREEN}" stroke="{INK}"/>'
    s += text(746,370,'Gate ≥ 6?',21,600,anchor='middle')
    s += arrow('M650 363H615V435H426V458')+text(546,430,'pass',19,600)
    s += arrow('M842 363H935V458')+text(941,434,'fail',19,600)
    s += rect(20,464,468,77,GREEN)+text(36,494,'Cited answer + declared blind spots',22,600)
    s += text(36,522,'Section-addressed sources',20)
    s += rect(528,464,452,77,SAND)+text(544,494,'Librarian fallback → read + recheck',21,600)
    s += text(544,522,'Pass → cited answer; fail → not-found',20)
    s += arrow('M528 503H493')
    return svg('NISQ retrieval-process comparison','BQ02 shared query. Reproduced dense RAG uses fixed chunks, top-two retrieval and single generation; its harness does not log provenance. QDCVR reads section-addressed evidence and passes at six of eight or performs librarian fallback and rechecking.',560,s)


def fig3():
    s = text(20,26,'BQ01 · How is attention computed, and why replace recurrence and convolution?',21,600)
    s += text(20,49,'Current run · answer summaries and trace labels are paraphrases.',17,400,'#526472')
    for x,fill,label,sub in [(20,GREEN,'A  QDCVR','Trace evidence'),(344,BLUE,'B  Bare agent','Self-reported file source'),(668,SAND,'C  Dense RAG','Our reproduction')]:
        s += rect(x,62,312,327,'white')+rect(x,62,312,58,fill,'none')
        s += text(x+14,87,label,22,700)+text(x+14,110,sub,19)
    s += doc(34,132,52,85,GREEN,True)+doc(98,132,52,85,GREEN,True)
    s += text(165,157,'part 1/2 · §3.2.3',18,600)+text(165,185,'part 2/2 · §7',18,600)
    s += arrow('M177 219V237')+text(190,235,'read',17)
    s += text(34,260,'Multi-head attention replaces',20,600)+text(34,284,'recurrence; parallel computation.',19)
    s += text(34,313,'Gate: 8/8 · fast exit',21,600)
    s += text(34,340,'Unread: positional formula,',19)+text(34,363,'training details, benchmark scores.',18)
    s += doc(358,132,56,85,BLUE)
    s += text(427,158,'1706.03762',20,600)+text(427,185,'files_used: filename',19)
    s += arrow('M500 219V237')+text(513,235,'reports',17)
    s += text(358,260,'softmax(QKᵀ / √dₖ)V',22,600)
    s += text(358,284,'Multi-head; parallelism; short paths',18)
    s += text(358,313,'More complete formula prose',20,600)
    s += text(358,340,'Self-reported source,',19)+text(358,363,'not an observed file-read trace.',19)
    for y in [136,177]:
        s += rect(682,y,58,28,SAND)+text(711,y+20,'…',20,600,anchor='middle')
    s += text(754,157,'C reports: parsing',19,600)+text(754,185,'+ Table 4 results',19)
    s += arrow('M824 219V237')+text(837,235,'generate',17)
    s += text(682,260,'Reports insufficient evidence',20,600)
    s += text(682,284,'Abstains in the recorded answer.',19)
    s += text(682,313,'2 chunks · 2,854 characters',20,600)
    s += text(682,340,'Chunk/source metadata',19)+text(682,363,'not logged in this harness.',19)
    s += text(20,422,'P2 · Spectral Tuning for Low-Resource Odor Recognition',21,600)
    s += text(20,448,'Fabricated-paper probe: asks about training epochs',19)
    s += rect(20,468,263,86,BLUE)+text(34,494,'BERT near miss',21,600)
    s += text(34,520,'Epochs belong to',19)+text(34,543,'a different paper.',19)
    s += arrow('M283 511H311')
    s += rect(319,468,179,86,LAV)+text(333,495,'Gate: 1/8',21,600)
    s += text(333,523,'Read → reject',19)
    s += arrow('M498 511H526')
    s += rect(534,468,247,86,SAND)+text(548,495,'Librarian scan',21,600)
    s += text(548,520,'5 bases · 165 indexed docs',18)+text(548,543,'50 papers',19)
    s += arrow('M781 511H809')
    s += rect(817,468,163,86,GREEN)+text(829,501,'NOT FOUND',21,700)
    s += text(829,530,'Scope reported',18)
    s += text(20,578,'Gate scores: LLM self-assessments, not accuracy.',14)
    return svg('Current Transformer evidence trace and fabricated-paper probe','Current BQ01 only: QDCVR trace evidence maps parts one and two of two, sections 3.2.3 and seven, gate eight of eight. Its declared unread material is the positional formula, training details and benchmark scores. Bare agent self-reports the source file and a more complete formula. The generated answer of the dense reproduction reports parsing and Table 4, then abstains; the logged evidence_docs array is empty. P2 rejects BERT at one of eight, scans five bases and 165 documents, and reports not-found.',594,s)


def verify_sources():
    result = ROOT / 'benchmark-suite/results'
    def row(name, key, value):
        d = json.loads((result/name).read_text(encoding='utf-8'))
        def visit(v):
            if isinstance(v,dict):
                if v.get(key)==value: return v
                for child in v.values():
                    found=visit(child)
                    if found is not None: return found
            if isinstance(v,list):
                for child in v:
                    found=visit(child)
                    if found is not None: return found
        return visit(d)
    assert row('skill_track_answers.json','qid','BQ01')['gate']['score']==8
    assert row('skill_track_answers.json','qid','BQ02')['gate']['score']==8
    assert row('track_a_e2e_spot.json','qid','BQ02')['gate']['score']=='8/8'
    c=row('track_bc.json','qid','BQ01')['track_c_dense_rag']
    assert c['evidence_chunks']==2 and c['evidence_chars']==2854
    assert c['evidence_docs']==[]
    assert row('honest_failure_probe.json','pid','P2')['verdict']=='NOT_FOUND'
    old=row('archive-20260917-10000chunk/skill_track_answers.json','qid','BQ01')
    assert '7/8' in old['final_answer'] and '11/26' in old['final_answer']


def main():
    verify_sources()
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for name, source in [('fig1-concept-draft',fig1()),('fig3-evidence-draft',fig3())]:
            root=ET.fromstring(source)
            assert not root.findall('.//{http://www.w3.org/2000/svg}foreignObject')
            assert all(float(t.attrib['font-size'])>=14 for t in root.findall('.//{http://www.w3.org/2000/svg}text'))
            height=int(root.attrib['height'])
            assert height <= 600
            (OUT/f'{name}.svg').write_text(source,encoding='utf-8')
            html=f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{name}</title><style>@page{{size:1000px {height}px;margin:0}}html,body{{margin:0;width:1000px;background:white}}svg{{display:block}}figcaption{{padding:16px 24px;font:18px/1.5 Calibri,Carlito,sans-serif;color:#253745;border-top:1px solid #c5cfd5}}@media print{{figcaption{{display:none}}}}</style>{source}<figcaption>{escape(CAPTIONS[name])}</figcaption></html>'
            (OUT/f'{name}.html').write_text(html,encoding='utf-8')
            page=browser.new_page(viewport={'width':1000,'height':height},device_scale_factor=2)
            page.goto((OUT/f'{name}.html').as_uri())
            page.evaluate('document.fonts.ready')
            overflow=page.evaluate('''() => [...document.querySelectorAll('svg text')].filter(e=>{const b=e.getBBox();return b.x<0 || b.x+b.width>1000 || b.y<0 || b.y+b.height>document.querySelector('svg').height.baseVal.value}).map(e=>e.textContent)''')
            assert not overflow, overflow
            page.locator('svg').screenshot(path=str(OUT/f'{name}.png'))
            page.pdf(path=str(OUT/f'{name}.pdf'),width='1000px',height=f'{height}px',print_background=True,prefer_css_page_size=True)
            page.close()
            print(f'PASS {name}: XML, font sizes, viewport bounds, PNG/PDF render')
        browser.close()
    print('PASS source assertions: current versus archived BQ01, C evidence window, P2 verdict')

if __name__=='__main__':
    main()

