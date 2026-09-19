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


def fig1():
    s = text(28,36,'01  /  Same question, different evidence processes',27,700)
    s += text(28,65,'Process schematic · BQ02 · not a claim of universal answer accuracy',17,400,'#526472')
    s += rect(28,87,944,64,BLUE)
    s += text(48,113,'SHARED NISQ QUERY',15,700)
    s += text(48,138,'What defines NISQ technology and what is its central limitation?',22,600)
    s += arrow('M500 151V174H263V194')+arrow('M500 174H743V194')
    s += rect(28,195,458,385,'#fafbfc')+rect(506,195,466,385,'#fbfdfb')
    s += text(48,225,'Dense RAG (our reproduction)',24,700)
    s += text(526,225,'QDCVR',24,700)
    s += doc(53,250,64,90,BLUE)
    for x,y in [(143,252),(159,276),(139,300)]:
        s += rect(x,y,64,17,BLUE)+f'<path d="M{x+8} {y+8}h42" stroke="#7590a6"/>'
    s += arrow('M120 291H137')
    s += text(225,276,'800-char chunks',20,600)
    s += text(225,301,'Fixed fragments',18)
    s += arrow('M258 344V363')
    s += rect(53,369,408,61,BLUE)+text(73,394,'Dense retrieval → top 2',21,600)
    s += text(73,417,'4,000-char evidence window',18)
    s += arrow('M258 431V456')
    s += rect(53,461,408,48,LAV)+text(73,491,'Single generation → answer',21,600)
    s += text(53,542,'Provenance not logged in this harness.',18,600)
    s += text(53,565,'Not an intrinsic dense-retrieval limitation.',17)
    s += doc(531,250,64,90,GREEN,True)
    s += text(617,273,'Organized, section-addressed parts',19,600)
    s += text(617,300,'base / document / part / section',17)
    s += arrow('M738 341V363')
    s += rect(531,369,416,61,GREEN)+text(551,395,'Vector-first recall',21,600)
    s += text(551,418,'Read candidate text; score 0–8',18)
    s += arrow('M738 431V454')
    s += f'<path d="M738 459L832 494L738 529L644 494Z" fill="{GREEN}" stroke="{INK}"/>'
    s += text(738,501,'Gate ≥ 6?',21,600,anchor='middle')
    s += arrow('M644 494H610V599H443V620')+text(522,590,'pass',17,600)
    s += arrow('M832 494H927V620')+text(933,557,'fail',17,600)
    s += rect(28,627,468,81,GREEN)+text(48,657,'Cited answer + declared blind spots',22,600)
    s += text(48,687,'NISQ example: part 2/3, §6.4; gate 7/8',18)
    s += rect(534,627,438,81,SAND)+text(554,657,'Librarian fallback → read + recheck',21,600)
    s += text(554,687,'Pass → cited answer; fail → not-found',18)
    s += arrow('M534 667H500')
    s += text(28,745,'Scope: benchmark configuration. Gate scores are execution-LLM self-assessments.',17)
    s += text(28,771,'Glyphs show evidence structure; arrows show the protocol, not measured superiority.',17)
    return svg('NISQ retrieval-process comparison','Both processes receive BQ02. Reproduced dense RAG uses 800-character chunks, top two retrieval, a 4000-character window, and single generation. Its harness does not log provenance. QDCVR reads section-addressed candidates, passes at six of eight, or falls back to a librarian and rechecks before a cited answer or not-found report.',794,s)


def fig3():
    s = text(28,36,'03  /  What can be traced from an answer?',27,700)
    s += text(28,65,'BQ01 · Attention Is All You Need · selected case, not an accuracy ranking',18)
    s += rect(28,84,944,61,BLUE)
    s += text(46,108,'QUERY · PARAPHRASE',15,700)
    s += text(46,132,'How is attention computed, and why replace recurrence and convolution?',21,600)
    for x,fill,label,sub in [(28,GREEN,'A  QDCVR','Section-addressed evidence'),(350,BLUE,'B  Bare agent','Self-reported file source'),(672,SAND,'C  Dense RAG','Our reproduction')]:
        s += rect(x,167,300,387,'white')+rect(x,167,300,69,fill,'none')
        s += text(x+17,195,label,24,700)+text(x+17,222,sub,18)
    s += doc(45,251,62,88,GREEN,True)+doc(118,251,62,88,GREEN,True)
    s += text(193,275,'part 1/2',17,600)+text(193,300,'§3.2.3',18,600)
    s += text(193,324,'part 2/2 · §7',16,600)
    s += arrow('M174 344V372')+text(189,362,'read',16)
    s += text(45,399,'Multi-head applications;',20,600)+text(45,424,'attention replaces recurrence.',18)
    s += text(45,459,'Current gate: 8/8 · fast exit',19,600)
    s += text(45,490,'Base → document → part → §',17)
    s += text(45,522,'Blind spot: positional formula',17)+text(45,543,'and training details not read.',17)
    s += doc(367,251,70,88,BLUE)
    s += text(453,276,'1706.03762',19,600)+text(453,302,'filename in files_used',16)
    s += arrow('M498 344V372')+text(513,362,'reports',16)
    s += text(367,399,'softmax(QKᵀ / √dₖ)V',22,600)
    s += text(367,427,'Multi-head projection;',19)+text(367,451,'parallelism + shorter paths.',19)
    s += text(367,490,'More complete formula prose',18,600)
    s += text(367,522,'File claim, not an observed',17)+text(367,543,'file-read audit trail.',17)
    for y in [256,298]:
        s += rect(689,y,74,30,SAND)+text(726,y+21,'…',20,600,anchor='middle')
    s += text(779,277,'Parsing experiments',17,600)+text(779,303,'+ Table 4 results',17)
    s += arrow('M820 344V372')+text(835,362,'generate',16)
    s += text(689,399,'Abstains: insufficient evidence',19,600)
    s += text(689,427,'Evidence window lacks',19)+text(689,451,'the requested method.',19)
    s += text(689,490,'2 chunks · 2,854 characters',18,600)
    s += text(689,522,'Chunk/source metadata',17)+text(689,543,'not logged by this harness.',17)
    s += rect(28,571,944,76,LAV)
    s += text(44,595,'RUN BOUNDARY',15,700)
    s += text(190,595,'Archived BQ01: gate 7/8; exact attention formula outside read windows.',18,600)
    s += text(44,619,'That trace cites parts 11/26 + 25/26, not the current 1/2 + 2/2. Do not merge the runs.',17)
    s += text(44,640,'Chunking is a possible explanation for C, not a proved cause; ranks were not logged.',17)
    s += text(28,680,'P2  /  A plausible near miss is still not evidence',23,700)
    s += text(28,707,'Fabricated-paper probe · Spectral Tuning for Low-Resource Odor Recognition',20,600)
    s += text(28,732,'Asked for training epochs; the following is a paraphrase of the recorded rejection trace.',17)
    s += rect(28,752,267,98,BLUE)+doc(43,768,43,62,BLUE)
    s += text(99,779,'BERT near miss',21,600)+text(99,805,'Epoch strings belong',17)+text(99,829,'to a different paper.',17)
    s += arrow('M295 801H330')
    s += rect(339,752,180,98,LAV)+text(357,780,'Gate: 1/8',22,600)
    s += text(357,808,'Read → reject',18)+text(357,832,'wrong paper',17)
    s += arrow('M519 801H554')
    s += rect(563,752,212,98,SAND)+text(581,780,'Librarian scan',21,600)
    s += text(581,808,'5 bases · 165 docs',18)+text(581,832,'50 papers',17)
    s += arrow('M775 801H810')
    s += rect(819,752,153,98,GREEN)+text(834,789,'NOT FOUND',20,700)+text(834,817,'scope reported',16)
    s += text(28,888,'Scope: current 30k run + explicitly separated archived caveat; prose is paraphrased, not quoted.',16)
    s += text(28,913,'Scores are self-assessments. This case compares traceability, not independently judged accuracy.',16)
    return svg('Transformer evidence trace and fabricated-paper probe','Three columns compare current BQ01: QDCVR current parts one and two of two, sections 3.2.3 and seven, gate eight of eight; bare agent reports a full formula but only self-reported file access; dense reproduction abstains after receiving parsing evidence. A separate historical note records archived seven of eight and an unread exact formula, with different part numbers. P2 rejects BERT at one of eight and scans five bases and 165 documents before not-found.',936,s)


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
            (OUT/f'{name}.svg').write_text(source,encoding='utf-8')
            html=f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{name}</title><style>@page{{size:1000px {height}px;margin:0}}html,body{{margin:0;width:1000px;background:white}}svg{{display:block}}</style>{source}</html>'
            (OUT/f'{name}.html').write_text(html,encoding='utf-8')
            page=browser.new_page(viewport={'width':1000,'height':height},device_scale_factor=2)
            page.goto((OUT/f'{name}.html').as_uri())
            page.evaluate('document.fonts.ready')
            overflow=page.evaluate('''() => [...document.querySelectorAll('svg text')].filter(e=>{const b=e.getBBox();return b.x<0 || b.x+b.width>1000 || b.y<0 || b.y+b.height>document.querySelector('svg').height.baseVal.value}).map(e=>e.textContent)''')
            assert not overflow, overflow
            page.screenshot(path=str(OUT/f'{name}.png'),full_page=True)
            page.pdf(path=str(OUT/f'{name}.pdf'),width='1000px',height=f'{height}px',print_background=True,prefer_css_page_size=True)
            page.close()
            print(f'PASS {name}: XML, font sizes, viewport bounds, PNG/PDF render')
        browser.close()
    print('PASS source assertions: current versus archived BQ01, C evidence window, P2 verdict')

if __name__=='__main__':
    main()
