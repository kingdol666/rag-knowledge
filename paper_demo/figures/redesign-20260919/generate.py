from pathlib import Path
from html import escape
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
INK='#263944'; LINE='#607580'; BLUE='#edf4fa'; GREEN='#edf5ef'; ROSE='#fbefeb'; SAND='#faf4e5'
class Figure:
    def __init__(self, key, height, title, desc):
        self.key=key; self.height=height
        self.items=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="{key}-title {key}-desc"><title id="{key}-title">{escape(title)}</title><desc id="{key}-desc">{escape(desc)}</desc><defs><marker id="{key}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="{LINE}" stroke-width="1.3"/></marker></defs><rect width="1000" height="{height}" fill="white"/>']
    def text(self,x,y,lines,size=16,weight=400,anchor='start',color=INK):
        if isinstance(lines,str): lines=[lines]
        for i,s in enumerate(lines): self.items.append(f'<text x="{x}" y="{y+i*(size+7)}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{escape(s)}</text>')
    def box(self,x,y,w,h,lines,fill=BLUE,size=16,dash=False):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" stroke="{LINE}" stroke-width="1.1"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
        n=1 if isinstance(lines,str) else len(lines)
        self.text(x+w/2,y+h/2-(n-1)*(size+7)/2+size*.34,lines,size,anchor='middle')
    def arrow(self,points,dash=False):
        self.items.append(f'<polyline points="{points}" fill="none" stroke="{LINE}" stroke-width="1.3" stroke-linejoin="round" marker-end="url(#{self.key}-arrow)"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
    def rule(self,x1,y1,x2,y2):
        self.items.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#cbd4d8" stroke-width="1"/>')
    def gate(self,x,y,w=150,h=100,word='Content gate'):
        self.items.append(f'<polygon points="{x},{y-h/2} {x+w/2},{y} {x},{y+h/2} {x-w/2},{y}" fill="{SAND}" stroke="{LINE}" stroke-width="1.2"/>')
        self.text(x,y-5,[word,'0–8; any ≥ 6?'],14,anchor='middle')
    def group(self,x,y,w,h,fill):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#dce0dd" stroke-width="0.8"/>')
    def doc(self,x,y):
        self.items.append(f'<path d="M{x} {y} h25 l10 10 v35 h-35 Z M{x+25} {y} v10 h10 M{x+7} {y+21} h21 M{x+7} {y+29} h21" fill="white" stroke="{LINE}" stroke-width="1.2"/>')
    def db(self,x,y,w,h,lines):
        self.items.append(f'<path d="M{x} {y+9} C{x} {y-3} {x+w} {y-3} {x+w} {y+9} V{y+h-9} C{x+w} {y+h+3} {x} {y+h+3} {x} {y+h-9} Z M{x} {y+9} C{x} {y+21} {x+w} {y+21} {x+w} {y+9}" fill="{GREEN}" stroke="{LINE}" stroke-width="1.1"/>')
        self.text(x+w/2,y+38,lines,15,anchor='middle')
    def header(self,title,sub):
        self.text(30,36,title,23,600); self.text(30,63,sub,14,color=LINE); self.rule(30,80,970,80)
    def access(self,y):
        self.box(30,y,220,44,'Web console · ragctl CLI',fill='white')
        self.box(660,y,310,44,'MCP agents · 41 kb_* tools',fill='white')
        self.arrow(f'140,{y+44} 140,{y+66}'); self.arrow(f'815,{y+44} 815,{y+66}')
        self.box(30,y+66,940,40,'FastAPI backend / shared platform services',fill=GREEN)
    def footer(self,y):
        self.rule(30,y,970,y)
        self.text(30,y+25,'Gate rubric: topic 0–3 + scenario 0–3 + concrete evidence 0–2; candidate passes at ≥ 6.',14)
        self.text(30,y+48,'Citations: base / document / part / section. Each stage persists an auditable per-query trace.',14)
        self.text(30,y+71,'Optional BM25 / graph channels: available, but NOT the benchmark retrieval route.',14,color=LINE)
        self.box(30,y+88,940,36,'Optional lifecycle: resolved Q&A logs → reusable entries (outside the required answer path)',fill='white',size=14,dash=True)
    def save(self):
        s='\n'.join(self.items)+'</svg>'; ET.fromstring(s)
        (ROOT/f'direction-{self.key}.svg').write_text(s,encoding='utf-8'); return s

DESC='QDCVR design draft. Web and CLI access shared FastAPI services separately from the MCP agent surface with 41 kb_* tools. PDFs are parsed by MinerU to section Markdown, classified by content into five bases, split and tagged as indexed evidence. ChromaDB BGE-M3, Neo4j, and YAML audit tree support the platform. Online query rewrite, vector-first recall, candidate reading, and a 0–8 gate with threshold 6 precede a conditional answer. Only initial failure invokes librarian shelf scan and targeted re-search; candidates are read and checked again. Passing evidence yields a cited five-section answer; no passing evidence after fallback yields searched scope, near miss, and reason. Optional BM25 and graph are not the benchmark route.'

# A: horizontal process strips with separate initial and fallback gates.
a=Figure('a',1110,'A · Evidence before generation',DESC)
a.header('QDCVR  /  Evidence before generation','A — horizontal academic process · explicit early exit and conditional recovery')
a.access(98)
a.group(20,220,960,274,'#fff9f7'); a.group(20,500,960,459,'#fffdf5')
a.text(30,241,'OFFLINE  /  DOCUMENT TO EVIDENCE',15,600)
a.doc(38,273); a.text(55,343,'PDF',15,anchor='middle')
a.box(105,265,185,88,['MinerU parse','Section Markdown'],ROSE)
a.rule(115,288,135,288); a.rule(115,297,130,297); a.rule(115,306,130,306)
a.box(325,265,240,88,['Read title + body','Classify into 5 bases'],ROSE)
a.box(600,265,180,88,['Section-path parts','Propagate tags'],ROSE)
a.arrow('75,309 105,309'); a.arrow('290,309 325,309'); a.arrow('565,309 600,309')
a.arrow('780,309 935,309 935,377 790,377 790,395')
a.arrow('790,377 505,377 505,395'); a.arrow('505,377 220,377 220,395')
a.text(830,294,'Index evidence',14)
a.db(95,395,250,83,['ChromaDB','BGE-M3 vectors'])
a.db(380,395,250,83,['Neo4j','Relations / graph'])
a.db(665,395,250,83,['YAML audit tree','Parts / provenance / traces'])
a.text(30,522,'ONLINE  /  READ, CHECK, THEN ANSWER',15,600)
a.arrow('220,478 220,490 640,490 640,548 355,548 355,580',True)
a.text(490,538,'Vector recall',14)
a.box(30,580,165,76,['Query','rewrite'])
a.box(235,580,200,76,['Vector-first recall','Cross-base balance'])
a.box(475,580,165,76,['Read candidate','text / parts'])
a.gate(750,618,160,104)
a.arrow('195,618 235,618'); a.arrow('435,618 475,618'); a.arrow('640,618 670,618')
a.box(840,735,130,138,['Cited answer','5 sections'],GREEN,size=15)
a.arrow('830,618 905,618 905,735'); a.text(860,604,'Pass',14)
a.box(400,755,235,84,['Librarian shelf scan','Targeted re-search'],ROSE)
a.arrow('750,670 750,707 518,707 518,755'); a.text(535,697,'None passes: fallback only',14)
a.box(165,755,195,84,['Read new candidates','Recheck content'])
a.arrow('400,797 360,797'); a.gate(70,797,125,100,'Recheck')
a.arrow('165,797 133,797')
a.arrow('70,847 70,903 820,903 820,804 840,804'); a.text(425,894,'Pass ≥ 6 → answer',14)
a.box(30,690,230,45,'Not found after fallback',ROSE,size=15)
a.arrow('70,747 70,735'); a.text(88,746,'None passes',14)
a.text(185,864,'Not found: searched scope + near miss + reason',14)
a.text(30,948,'Answer sections: search paths · answer · sources · confidence · blind spots',15)
a.footer(968)

# B: true swimlanes, one gate and a read/check return loop.
b=Figure('b',1170,'B · Offline / online swimlanes',DESC)
b.header('QDCVR  /  Two operating lanes','B — offline preparation beside online control flow · one gate, explicit retry loop')
b.access(98)
b.group(20,230,265,767,'#fff8f5'); b.group(310,230,670,767,'#fffdf3')
b.rule(300,231,300,992)
b.text(30,249,'OFFLINE · per document',16,600); b.text(330,249,'ONLINE · per query',16,600)
b.box(40,280,220,54,'PDF intake',ROSE)
b.arrow('150,334 150,365'); b.box(40,365,220,78,['MinerU','Section Markdown'],ROSE)
b.arrow('150,443 150,474'); b.box(40,474,220,88,['Read title + body','Classify into 5 bases'],ROSE)
b.arrow('150,562 150,593'); b.box(40,593,220,80,['Section-path parts','Tags → every part'],ROSE)
b.arrow('150,673 150,704'); b.db(40,704,220,80,['ChromaDB','BGE-M3 vectors'])
b.db(40,808,220,72,['Neo4j','Relations / graph'])
b.db(40,904,220,72,['YAML audit tree','Evidence / audit traces'])
b.arrow('260,634 279,634 279,844 260,844'); b.arrow('279,844 279,940 260,940')
b.box(360,280,250,54,'Query rewrite'); b.arrow('485,334 485,365')
b.box(360,365,250,80,['Vector-first recall','Cross-base balance']); b.arrow('485,445 485,482')
b.box(360,482,250,68,['Read candidate text','Parts / continuation reads'])
b.arrow('260,744 320,744 320,405 360,405',True); b.text(326,681,'Recall',14)
b.arrow('485,550 485,582'); b.gate(485,642,215,120)
b.box(740,596,230,92,['Cited five-section answer','Base / doc / part / §'],GREEN,size=15)
b.arrow('592,642 740,642'); b.text(621,630,'Any ≥ 6',14)
b.box(670,770,300,90,['Librarian shelf scan','Targeted re-search'],ROSE)
b.arrow('485,702 485,815 670,815'); b.text(499,742,['None passes','Initial attempt'],14)
b.arrow('970,815 988,815 988,516 610,516'); b.text(713,543,['Read new candidates','then recheck'],14)
b.box(360,914,270,65,['Not found','Scope + near miss + reason'],ROSE,size=15)
b.arrow('462,689 340,689 340,880 495,880 495,914')
b.text(366,849,['None passes','After fallback'],14)
b.text(669,909,['Five answer sections:','search paths · answer · sources','confidence · blind spots'],14)
b.footer(1015)

# C: numbered modules around a central repository, with a descending decision tree.
c=Figure('c',1240,'C · Evidence-centered modular architecture',DESC)
c.header('QDCVR  /  Evidence-centered architecture','C — numbered modules · central evidence repository · vertical branching protocol')
c.access(98)
c.box(30,244,275,190,['01  CONTENT INGESTION','PDF → MinerU','Section Markdown','Read content → 5 bases','Section-path parts + tags'],ROSE,size=16)
c.box(355,244,320,190,['02  INDEXED EVIDENCE','ChromaDB · BGE-M3','Neo4j relations','YAML audit tree','Parts / provenance / traces'],GREEN,size=16)
c.box(725,244,245,190,['OPTIONAL CHANNELS','BM25 / graph','Not benchmark route','Optional lifecycle:','resolved Q&A → entries'],'white',size=15,dash=True)
c.arrow('305,339 355,339')
c.box(355,495,320,90,['03  QUERY PREPARATION','Rewrite → vector-first recall','Balance across category bases'],size=16)
c.arrow('515,434 515,495',True); c.text(529,468,'Recall evidence',14)
c.box(355,620,320,62,['04  READ CANDIDATE TEXT','Parts / continuation reads'],size=16)
c.arrow('515,585 515,620'); c.arrow('515,682 515,710')
c.gate(515,765,210,110)
c.box(30,715,265,118,['06  CITED ANSWER','Five sections','Base / doc / part / section'],GREEN,size=16)
c.arrow('410,765 295,765'); c.text(309,751,'Any ≥ 6',14)
c.box(355,865,320,78,['05  LIBRARIAN FALLBACK','Shelf scan → targeted re-search'],ROSE,size=16)
c.arrow('515,820 515,865'); c.text(529,846,'None passes',14)
c.box(725,865,245,78,['Read new candidates','Recheck content'],size=16)
c.arrow('675,904 725,904'); c.arrow('847,943 847,975')
c.gate(847,1025,205,100,'Recheck')
c.arrow('745,1025 275,1025 275,833'); c.text(410,1014,'Any ≥ 6 → cited answer',14)
c.box(355,1060,320,48,'Not found after fallback',ROSE,size=16)
c.arrow('847,1075 847,1084 675,1084'); c.text(709,1104,'None passes',14)
c.text(30,878,['Answer sections:','search paths','answer · sources','confidence · blind spots'],14)
c.text(355,1137,'Not found: searched scope + near miss + reason',14)
c.rule(30,1160,970,1160)
c.text(30,1187,'Gate: topic 0–3 + scenario 0–3 + evidence 0–2 = 0–8; pass ≥ 6. Audit trace at every stage.',14)
c.text(30,1213,'Solid arrows: data / control flow. Dashed arrows: evidence supply. Dashed modules: optional.',14,color=LINE)

svgs=[f.save() for f in [a,b,c]]
notes=[('A','克制的横向学术流程','以文档、数据库符号和浅色分区组织流程。首次通过沿右侧直接进入回答；首次无证据通过才进入下方回退支路。第二个门明确分开“复核通过”和“复核失败”。'),('B','双泳道与显式重读环','左侧是离线入库，右侧是在线协议。馆员检索后回到候选正文阅读，再次进入同一菱形门；门的两个失败出口区分首次失败与回退后的失败。'),('C','编号模块与证据中心','上部以证据仓连接入库和查询模块，下部展开纵向条件树。向左提前回答，向下馆员回退，重新阅读复核后再决定回答或未找到。编号仅标识模块，不代表所有查询必经。')]
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>QDCVR Fig.2 · 三个方向草稿</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f2ee;color:#263944;font-family:"Segoe UI","Microsoft YaHei",sans-serif}main{max-width:1160px;margin:auto;padding:48px 32px}header{border-top:3px solid #263944;padding-top:20px;margin-bottom:40px}.kicker{font-size:13px;letter-spacing:2px}h1{font-family:Georgia,"Microsoft YaHei",serif;font-size:38px;font-weight:500;margin:15px 0}p{line-height:1.85;max-width:860px}nav{display:flex;gap:12px;flex-wrap:wrap}a{color:inherit}nav a,button{border:1px solid #708087;background:transparent;padding:10px 16px;font:inherit;text-decoration:none;cursor:pointer}button[aria-pressed=true]{background:#263944;color:white}button:focus-visible,a:focus-visible{outline:3px solid #aa6737;outline-offset:4px}article{margin:34px 0 56px;padding-top:22px;border-top:1px solid #b8c1c5}h2{font-size:25px;font-weight:500;margin:0}article svg{display:block;width:100%;height:auto;background:white}.sheet{border:1px solid #d4dadd;margin-top:22px;overflow:auto}.actions{display:flex;gap:20px;align-items:center;flex-wrap:wrap}#status{min-height:30px;color:#345e4b}@media print{body{background:white}main{padding:0}header,article>h2,article>p,.actions{display:none}article{border:0;margin:0;break-after:page}.sheet{border:0;margin:0}}@media(max-width:600px){main{padding:26px 16px}h1{font-size:30px}.sheet svg{min-width:740px}}
</style><main><header><div class="kicker">QDCVR / FIGURE 02 / DIRECTION STUDIES / 2026-09-19</div><h1>先选结构，再替换论文图</h1><p>三套真实 SVG 草稿，不是最终论文替换稿。英文图中文字均为可编辑文本，宽度 1000，最小字号 14 px，正文以 16 px 为主；目标为 178 mm 双栏全宽，而非原图的 0.78 倍栏宽。白底、细线、无外部资源。三套结构不同，表达同一条件协议。Web／CLI 和 MCP 分别接入共享平台，不将所有客户端画成 MCP 客户端。</p><nav><a href="#a">A · 横向流程</a><a href="#b">B · 双泳道</a><a href="#c">C · 模块架构</a></nav><p id="status" role="status">尚未选择。按钮只在本浏览器保存偏好，不提交、不修改论文。</p></header>'''
for (key,title,note),svg in zip(notes,svgs):
    k=key.lower()
    html+=f'<article id="{k}"><h2>{key} / {title}</h2><p>{note}</p><div class="actions"><button type="button" data-choice="{key}" aria-pressed="false">偏好方向 {key}</button><a href="direction-{k}.svg" download>下载可编辑 SVG</a><a href="direction-{k}.png" download>下载 PNG</a></div><div class="sheet">{svg}</div></article>'
html+='<section id="companion"><h2>推荐方向的配套内容草图</h2><p>配套内容用于联动评估 Fig.1 与 Fig.3，不表示已选定 A／B／C，也不会替换论文。以下为其他协作者负责的独立文件。</p>'
for name,label in [('fig1-concept-draft.svg','Fig.1 · 概念草图'),('fig3-evidence-draft.svg','Fig.3 · 证据草图')]:
    html+=f'<p><a href="{name}">{label}（打开 SVG）</a></p>'
    if (ROOT/name).exists(): html+=f'<img src="{name}" alt="{label}" style="display:block;width:100%;height:auto;background:white">'
    else: html+='<p>文件待协作者生成；此处暂为静态链接，不加载图片。文件就绪后可直接打开链接。</p>'
html+='</section>'
html+='''<script>const buttons=[...document.querySelectorAll('[data-choice]')];const status=document.getElementById('status');function select(choice,save){buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.choice===choice)));let persisted=true;if(save){try{localStorage.setItem('qdcvr-fig2-direction',choice)}catch(e){persisted=false}}status.textContent='当前偏好：方向 '+choice+'。'+(persisted?'仅保存在本浏览器，不提交、不修改论文。':'仅在此页面有效；浏览器未允许保存。')}buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.choice,true)));try{const choice=localStorage.getItem('qdcvr-fig2-direction');if(['A','B','C'].includes(choice))select(choice,false)}catch(e){/* Local preference storage is optional. */}</script></main></html>'''
(ROOT/'gallery.html').write_text(html,encoding='utf-8')

if __name__=='__main__':
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1100,'height':1400},device_scale_factor=2)
        network=[]; errors=[]
        page.on('request',lambda r: network.append(r.url) if r.url.startswith(('http:','https:')) else None)
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto((ROOT/'gallery.html').as_uri())
        checks={}
        for key in 'abc':
            svg=page.locator(f'#{key} svg')
            # Export the actual rendered, inline SVG (not an unverified mock screenshot).
            page.set_viewport_size({'width':1066,'height':1400})
            svg.screenshot(path=str(ROOT/f'direction-{key}.png'))
            checks[key]=svg.evaluate('''svg=>{const rect=svg.viewBox.baseVal;return {textCount:svg.querySelectorAll('text').length,minFont:Math.min(...[...svg.querySelectorAll('text')].map(t=>parseFloat(t.getAttribute('font-size')))),outOfBounds:[...svg.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.x<0||b.y<0||b.x+b.width>rect.width||b.y+b.height>rect.height}).map(t=>t.textContent),foreignObject:svg.querySelectorAll('foreignObject').length}}''')
        page.get_by_role('button',name='偏好方向 B',exact=True).click()
        assert page.get_by_role('button',name='偏好方向 B',exact=True).get_attribute('aria-pressed')=='true'
        page.reload()
        assert page.get_by_role('button',name='偏好方向 B',exact=True).get_attribute('aria-pressed')=='true'
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not network and not errors
        for v in checks.values(): assert v['minFont']>=14 and not v['outOfBounds'] and v['foreignObject']==0
        report={'checks':checks,'remote_requests':network,'page_errors':errors,'preference_click_and_reload':'passed','mobile_page_overflow':'none','render':'Playwright Chromium, actual inline SVG, device scale 2'}
        (ROOT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        browser.close()
        print(json.dumps(report,indent=2))

