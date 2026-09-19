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
    def access(self,y=12):
        self.box(20,y,225,34,'Web console · ragctl CLI','white',16)
        self.box(275,y,290,34,'MCP agents · 41 kb_* tools','white',16)
        self.box(610,y,370,34,'FastAPI / shared platform',GREEN,16)
        self.arrow(f'565,{y+17} 610,{y+17}')
        self.arrow(f'132,{y+34} 132,{y+47} 592,{y+47} 592,{y+17} 610,{y+17}')
    def hierarchy(self,x,y):
        self.items.append(f'<g fill="white" stroke="{LINE}" stroke-width="1"><rect x="{x}" y="{y}" width="43" height="49"/><rect x="{x+4}" y="{y+5}" width="35" height="8" fill="{ROSE}"/><path d="M{x+8} {y+18} v22 m0 -17 h6 m-6 13 h6"/><rect x="{x+14}" y="{y+19}" width="24" height="9"/><rect x="{x+14}" y="{y+32}" width="24" height="9"/></g>')
    def save(self):
        s='\n'.join(self.items)+'</svg>'; ET.fromstring(s)
        (ROOT/f'direction-{self.key}.svg').write_text(s,encoding='utf-8'); return s

DESC='QDCVR design draft. Web and CLI access shared FastAPI services separately from the MCP agent surface with 41 kb_* tools. PDFs are parsed by MinerU to section Markdown, classified by content into five bases, split and tagged as indexed evidence. ChromaDB BGE-M3, Neo4j, and YAML audit tree support the platform. Online query rewrite, vector-first recall, candidate reading, and a 0–8 gate with threshold 6 precede a conditional answer. Only initial failure invokes librarian shelf scan and targeted re-search; candidates are read and checked again. Passing evidence yields a cited five-section answer; no passing evidence after fallback yields searched scope, near miss, and reason. Optional BM25 and graph are not the benchmark route.'

# A: compact horizontal ingestion, store band, and two conditional gates.
a=Figure('a',560,'A · Horizontal process architecture',DESC)
a.access()
a.group(20,76,960,165,'#fff8f5'); a.text(30,98,'(a) Offline indexing',16,600)
a.doc(33,120); a.text(50,183,'PDF',14,anchor='middle')
a.box(100,113,230,67,[],ROSE); a.text(245,136,['MinerU →','Section Markdown'],16,anchor='middle')
a.hierarchy(108,122)
a.box(370,113,250,67,['Read title + body','Classify into 5 bases'],ROSE)
a.box(660,113,310,67,['Section-path parts','Tags → every part'],ROSE)
a.arrow('68,146 100,146'); a.arrow('330,146 370,146'); a.arrow('620,146 660,146')
a.box(30,202,940,30,'Indexed evidence: ChromaDB / BGE-M3     |     Neo4j     |     YAML audit tree',GREEN,16)
a.arrow('815,180 815,202')
a.group(20,253,960,295,'#fffdf3'); a.text(30,277,'(b) Online retrieval',16,600)
a.box(30,303,150,64,['Query','rewrite'])
a.box(215,303,205,64,['Vector-first recall','Cross-base balance'])
a.box(460,303,165,64,['Read candidate','text / parts'])
a.gate(730,335,165,94)
a.arrow('180,335 215,335'); a.arrow('420,335 460,335'); a.arrow('625,335 647,335')
a.arrow('318,232 318,303',True); a.text(330,293,'Recall',14)
a.box(845,303,125,69,['Cited answer','5 sections'],GREEN,16)
a.arrow('812,335 845,335'); a.text(814,317,'Pass',14)
a.box(465,435,275,65,['Librarian shelf scan','Targeted re-search'],ROSE)
a.arrow('730,382 730,412 602,412 602,435'); a.text(744,407,'None passes',14)
a.box(235,435,190,65,['Read new text','Recheck content'])
a.arrow('465,468 425,468'); a.gate(112,468,185,90,'Recheck'); a.arrow('235,468 205,468')
a.arrow('19,468 9,468 9,554 989,554 989,337 970,337'); a.text(760,539,'Pass ≥ 6 → answer',14)
a.box(250,513,490,29,'Not found: scope + near miss + reason',ROSE,16)
a.arrow('112,513 112,528 250,528'); a.text(122,519,'None passes',14)

# B: narrow offline lane; online gate with an explicit return-to-read loop.
b=Figure('b',560,'B · Offline / online workflow',DESC)
b.access(); b.group(20,76,245,472,'#fff8f5'); b.group(280,76,700,472,'#fffdf3')
b.text(30,98,'(a) Offline indexing',16,600); b.text(295,98,'(b) Online retrieval',16,600)
b.doc(35,126); b.text(51,188,'PDF',14,anchor='middle')
b.box(100,120,145,63,['MinerU','parse'],ROSE); b.arrow('70,149 100,149')
b.box(35,210,210,66,[],ROSE); b.text(165,238,['Section','Markdown'],16,anchor='middle'); b.hierarchy(43,218)
b.arrow('172,183 172,210')
b.box(35,302,210,65,['Read content','Classify into 5 bases'],ROSE); b.arrow('140,276 140,302')
b.box(35,392,210,50,['Parts + section paths','Propagate tags'],ROSE,15); b.arrow('140,367 140,392')
b.box(35,469,210,64,['ChromaDB / BGE-M3','Neo4j · YAML audit'],GREEN,15); b.arrow('140,442 140,469')
b.box(300,122,150,61,['Query','rewrite'])
b.box(490,122,235,61,['Vector-first recall','Cross-base balance']); b.arrow('450,153 490,153')
b.arrow('245,501 272,501 272,196 606,196 606,183',True); b.text(310,214,'Indexed evidence → recall',14)
b.box(490,237,235,63,['Read candidate text','Parts / continuation'])
b.arrow('606,183 748,183 748,225 606,225 606,237')
b.gate(606,364,210,100); b.arrow('606,300 606,314')
b.box(810,325,160,78,['Cited answer','5 sections'],GREEN)
b.arrow('711,364 810,364'); b.text(742,352,'Pass',14)
b.box(760,460,210,65,['Librarian shelf scan','Targeted re-search'],ROSE)
b.arrow('606,414 606,436 865,436 865,460'); b.text(627,425,'Initial: none passes',14)
b.arrow('970,492 988,492 988,268 725,268'); b.text(780,255,'Read new text + recheck',14)
b.box(310,460,245,65,['Not found','Scope + near miss + reason'],ROSE,15)
b.arrow('501,364 432,364 432,460'); b.text(310,396,['After fallback:','none passes'],14)

# C: numbered modules, centered evidence, and a vertically branching protocol.
c=Figure('c',560,'C · Modular evidence-centered architecture',DESC)
c.access(); c.text(30,91,'(a) Offline indexing',16,600); c.text(695,91,'(b) Online retrieval',16,600)
c.box(20,110,270,140,[],ROSE,16)
c.hierarchy(31,119); c.text(182,140,'01  Content ingestion',16,anchor='middle'); c.text(155,184,['PDF → MinerU → Markdown','Read content → 5 bases','Section-path parts + tags'],16,anchor='middle')
c.box(340,110,300,140,['02  Indexed evidence','ChromaDB / BGE-M3','Neo4j · YAML audit tree','Parts / provenance / traces'],GREEN,16)
c.arrow('290,180 340,180'); c.text(295,165,'Index',14)
c.box(690,110,290,63,['03  Rewrite → vector recall','Cross-base balance'],BLUE,16)
c.arrow('640,141 690,141',True)
c.box(690,197,290,53,['04  Read candidate text'],BLUE,16); c.arrow('835,173 835,197')
c.gate(600,319,200,96); c.arrow('835,250 835,264 600,264 600,271')
c.box(285,285,190,67,['06  Cited answer','5 sections'],GREEN,16)
c.arrow('500,319 475,319'); c.text(461,279,'Pass',14)
c.box(690,386,290,60,['05  Librarian shelf scan','Targeted re-search'],ROSE,16)
c.arrow('600,367 600,416 690,416'); c.text(510,391,'None passes',14)
c.box(430,455,225,63,['Read new candidate text','Recheck content'],BLUE,16)
c.arrow('835,446 835,486 655,486')
c.gate(300,487,195,92,'Recheck'); c.arrow('430,487 398,487')
c.arrow('300,441 300,395 380,395 380,352'); c.text(315,383,'Pass ≥ 6',14)
c.box(20,455,160,67,['Not found','Scope / near miss','Reason'],ROSE,14)
c.arrow('202,487 180,487'); c.text(32,440,'None passes after fallback',14)
c.text(30,550,'Solid: data / control flow. Dashed: indexed evidence supply.',14,color=LINE)

svgs=[f.save() for f in [a,b,c]]
notes=[('A','克制的横向学术流程','以文档、数据库符号和浅色分区组织流程。首次通过沿右侧直接进入回答；首次无证据通过才进入下方回退支路。第二个门明确分开“复核通过”和“复核失败”。'),('B','双泳道与显式重读环','左侧是离线入库，右侧是在线协议。馆员检索后回到候选正文阅读，再次进入同一菱形门；门的两个失败出口区分首次失败与回退后的失败。'),('C','编号模块与证据中心','上部以证据仓连接入库和查询模块，下部展开纵向条件树。向左提前回答，向下馆员回退，重新阅读复核后再决定回答或未找到。编号仅标识模块，不代表所有查询必经。')]
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>QDCVR Fig.2 · 三个方向草稿</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f2ee;color:#263944;font-family:"Segoe UI","Microsoft YaHei",sans-serif}main{max-width:1160px;margin:auto;padding:48px 32px}header{border-top:3px solid #263944;padding-top:20px;margin-bottom:40px}.kicker{font-size:13px;letter-spacing:2px}h1{font-family:Georgia,"Microsoft YaHei",serif;font-size:38px;font-weight:500;margin:15px 0}p{line-height:1.85;max-width:860px}.audit-notice{border:1px solid #b9a47c;background:#fff9eb;padding:16px 20px;margin:22px 0}.audit-notice p{font-size:14px;line-height:1.65;margin:8px 0}.audit-notice strong{font-size:16px}nav{display:flex;gap:12px;flex-wrap:wrap}a{color:inherit}nav a,button{border:1px solid #708087;background:transparent;padding:10px 16px;font:inherit;text-decoration:none;cursor:pointer}button[aria-pressed=true]{background:#263944;color:white}button:focus-visible,a:focus-visible{outline:3px solid #aa6737;outline-offset:4px}article{margin:34px 0 56px;padding-top:22px;border-top:1px solid #b8c1c5}h2{font-size:25px;font-weight:500;margin:0}article svg{display:block;width:100%;height:auto;background:white}.sheet{border:1px solid #d4dadd;margin-top:22px;overflow:auto}.actions{display:flex;gap:20px;align-items:center;flex-wrap:wrap}#status{min-height:30px;color:#345e4b}@media print{body{background:white}main{padding:0}header,article>h2,article>p,.actions{display:none}article{border:0;margin:0;break-after:page}.sheet{border:0;margin:0}}@media(max-width:600px){main{padding:26px 16px}h1{font-size:30px}.sheet svg{min-width:740px}}
</style><main><header><div class="kicker">QDCVR / FIGURE 02 / DIRECTION STUDIES / 2026-09-19</div><h1>先选结构，再替换论文图</h1><p>三套真实 SVG 草稿，不是最终论文替换稿。英文图中文字均为可编辑文本，尺寸统一为 1000 × 560（宽高比 1.79:1），最小字号 14 px，正文以 16 px 为主；目标为 178 mm 双栏全宽，而非原图的 0.78 倍栏宽。白底、细线、无外部资源。三套结构不同，表达同一条件协议。Web／CLI 和 MCP 分别接入共享平台，不将所有客户端画成 MCP 客户端。</p><aside class="audit-notice" aria-label="图源与运行一致性说明"><strong>图源与运行一致性说明</strong><p>原 Fig.3 混用了不同运行：当前 BQ01 为 8/8，分片 1/2 + 2/2；归档运行是 7/8，分片 11/26 + 25/26。当前草图仅使用当前运行；来源审计另行记录。</p><p>已检查参考：DeepRead v3（预印本，未核实为 CIKM 发表版本）；已发表于 CIKM 2025 的 AppAgent-Pro 与 CyberBOT 的作者 PDF，其中 CyberBOT 为 14 页扩展版，非 camera-ready 版本。</p><p><a href="../../review/figure-redesign-20260919/DESIGN-REVIEW.md">设计审查记录</a> · <a href="../../review/figure-redesign-20260919/PUBLISHED-REFERENCES.md">发表参考来源审计</a></p></aside><nav><a href="#a">A · 横向流程</a><a href="#b">B · 双泳道</a><a href="#c">C · 模块架构</a></nav><p id="status" role="status">尚未选择。按钮只在本浏览器保存偏好，不提交、不修改论文。</p></header>'''
for (key,title,note),svg in zip(notes,svgs):
    k=key.lower()
    html+=f'<article id="{k}"><h2>{key} / {title}</h2><p>{note}</p><div class="actions"><button type="button" data-choice="{key}" aria-pressed="false">偏好方向 {key}</button><a href="direction-{k}.svg" download>下载可编辑 SVG</a><a href="direction-{k}.png" download>下载 PNG</a></div><div class="sheet">{svg}</div><p>图注：评分 = 主题 0–3 + 场景 0–3 + 具体证据 0–2；候选通过阈值 ≥6。回答五节为检索路径、回答、来源、置信度、盲区；引用定位到库／文档／分片／章节。所有阶段记录查询审计。可选 BM25／图谱渠道不是基准检索路线；可选生命周期将已解决问答提炼为条目，不是回答必经阶段。</p></article>'
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
            render=browser.new_page(viewport={'width':1000,'height':560},device_scale_factor=2)
            render.goto((ROOT/f'direction-{key}.svg').as_uri())
            render.locator('svg').screenshot(path=str(ROOT/f'direction-{key}.png'))
            render.close()
            checks[key]=svg.evaluate('''svg=>{const rect=svg.viewBox.baseVal;return {width:rect.width,height:rect.height,ratio:rect.height/rect.width,textCount:svg.querySelectorAll('text').length,minFont:Math.min(...[...svg.querySelectorAll('text')].map(t=>parseFloat(t.getAttribute('font-size')))),outOfBounds:[...svg.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.x<0||b.y<0||b.x+b.width>rect.width||b.y+b.height>rect.height}).map(t=>t.textContent),foreignObject:svg.querySelectorAll('foreignObject').length}}''')
        page.get_by_role('button',name='偏好方向 B',exact=True).click()
        assert page.get_by_role('button',name='偏好方向 B',exact=True).get_attribute('aria-pressed')=='true'
        page.reload()
        assert page.get_by_role('button',name='偏好方向 B',exact=True).get_attribute('aria-pressed')=='true'
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not network and not errors
        for v in checks.values(): assert v['width']==1000 and v['height']<=620 and v['ratio']<=0.62 and v['minFont']>=14 and not v['outOfBounds'] and v['foreignObject']==0
        report={'checks':checks,'remote_requests':network,'page_errors':errors,'preference_click_and_reload':'passed','mobile_page_overflow':'none','render':'Playwright Chromium, actual standalone SVG, device scale 2 (2000 × 1120)'}
        (ROOT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        browser.close()
        print(json.dumps(report,indent=2))

