from pathlib import Path
import xml.etree.ElementTree as ET
import base64, io, urllib.parse
from PIL import Image

D=Path(r'D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\figure-reconstruction-20261116\architecture'); D.mkdir(parents=True,exist_ok=True)
ref=Image.open(r'C:\Users\87287\AppData\Local\Temp\codex-clipboard-516678fa-89c0-4762-8da3-c25e15925641.png').convert('RGB')
print('source dimensions',ref.size)
mx=ET.Element('mxfile',host='app.diagrams.net',modified='2026-11-16T00:00:00.000Z',agent='diagrams.net',version='24.7.17',type='device'); diag=ET.SubElement(mx,'diagram',id='reconstruction',name='Architecture'); model=ET.SubElement(diag,'mxGraphModel',dx='1753',dy='897',grid='0',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth='1753',pageHeight='897',math='0',shadow='0'); root=ET.SubElement(model,'root'); ET.SubElement(root,'mxCell',id='0'); ET.SubElement(root,'mxCell',id='1',parent='0')
n=0

def cell(x,y,w,h,val='',style=''):
 global n; n+=1
 c=ET.SubElement(root,'mxCell',id=str(n+1),value=val,style=style,vertex='1',parent='1'); ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'}); return c

def box(x,y,w,h,fill='#FFFFFF',stroke='#000000',sw=2,rounding=12,dashed=False):
 return cell(x,y,w,h,style=f'rounded=1;arcSize={rounding};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={sw};'+('dashed=1;dashPattern=8 6;' if dashed else ''))

def text(x,y,w,h,s,size=24,bold=False,align='left',v='middle',font='Arial'):
 return cell(x,y,w,h,s, f'text;html=1;align={align};verticalAlign={v};whiteSpace=wrap;overflow=hidden;strokeColor=none;fillColor=none;fontFamily={font};fontSize={size};fontColor=#000000;fontStyle={1 if bold else 0};spacing=0;')

def line(points,arrow=True,dash=False,sw=2):
 global n;n+=1
 sty=f'edgeStyle=none;rounded=0;html=1;strokeColor=#000000;strokeWidth={sw};endArrow={"block" if arrow else "none"};endFill=1;endSize=8;'+('dashed=1;dashPattern=4 4;' if dash else '')
 c=ET.SubElement(root,'mxCell',id=str(n+1),value='',style=sty,edge='1',parent='1'); g=ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'});ET.SubElement(g,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),**{'as':'sourcePoint'});ET.SubElement(g,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),**{'as':'targetPoint'})
 if len(points)>2:
  a=ET.SubElement(g,'Array',**{'as':'points'})
  for x,y in points[1:-1]:ET.SubElement(a,'mxPoint',x=str(x),y=str(y))

def icon(name,coords,alpha=True):
 x1,y1,x2,y2=coords; im=ref.crop(coords).convert('RGBA')
 if alpha:
  px=im.load()
  for yy in range(im.height):
   for xx in range(im.width):
    r,g,b,a=px[xx,yy]; lum=(r+g+b)/3
    # The icons are black line art on white or pale blue. Preserve alpha edges.
    q=max(0,min(255,round((205-lum)*2.3)))
    px[xx,yy]=(0,0,0,q)
 im.save(D/(name+'.png')); b=io.BytesIO();im.save(b,format='PNG'); data=urllib.parse.quote(base64.b64encode(b.getvalue()).decode(),safe='')
 cell(x1,y1,x2-x1,y2-y1,style='shape=image;html=1;imageAspect=0;image=data:image/png%3Bbase64,'+data+';')

# Canvas boundary anchors to preserve the entire source extent in export.
cell(0,0,1752,895,style='fillColor=#FFFFFF;strokeColor=none;')
# Four dashed areas.
for p in [(20,105,214,741),(246,105,615,741),(874,105,441,741),(1327,105,405,741)]:box(*p,fill='#FFFFFF',sw=1.7,rounding=12,dashed=True)
for p in [(43,126,169,68),(339,120,439,80),(894,120,400,80),(1345,125,370,68)]:box(*p,fill='#D5E8FC',stroke='none',sw=0,rounding=30)
text(43,126,169,68,'Clients',30,True,'center')
text(339,122,439,76,'Access &amp; Orchestration<br>(HMRS)',30,True,'center')
text(894,122,400,76,'Knowledge Management<br>Services (Shared)',30,True,'center')
text(1345,126,370,68,'Retrieval &amp; Navigation',30,True,'center')
# Main cards.
box(267,306,162,84,'#E0EFFF',sw=2);box(456,306,140,84,'#FFFFFF',sw=2);box(625,306,128,84,'#FFFFFF',sw=2)
box(275,525,238,122,'#E0EFFF',sw=2);box(276,730,302,92,'#FFFFFF',sw=2,dashed=True)
# Shared state card with blue title band, overlay top rounded blue section.
box(897,251,395,463,'#FFFFFF',sw=2,rounding=12); box(898,252,393,61,'#D6EAFD',stroke='none',rounding=20); cell(897,251,395,463,style='rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;strokeWidth=2;')
text(902,254,385,58,'Shared Managed State',29,True,'center')
for yy in (335,425,514,604):box(916,yy,360,76,'#FFFFFF',sw=1.5,rounding=20)
box(1379,324,342,103,'#E0EFFF',sw=2,rounding=20);box(1388,548,331,101,'#FFFFFF',sw=2,rounding=20)
# connectors behind labels/icons
for pts in [[(187,348),(267,348)],[(429,348),(456,348)],[(596,348),(625,348)],[(753,348),(784,348)],[(837,348),(898,348)],[(178,580),(275,580)],[(513,559),(898,559)],[(513,617),(898,617)],[(1292,483),(1348,483),(1348,375),(1379,375)],[(1348,483),(1348,598),(1388,598)]]:line(pts)
line([(320,647),(320,730)],dash=True);line([(472,730),(472,647)],dash=True)
# Exact glyphs taken as individually movable crops to preserve the drawn icon style.
for name,roi in [
 ('browser',(69,300,177,382)),('terminal',(71,537,180,620)),('nuxt',(278,326,323,370)),('api',(463,324,501,370)),('mineru',(633,329,670,368)),('markdown',(783,305,835,367)),('mcp',(291,548,349,607)),('laya',(318,744,366,812)),('file',(946,346,1001,400)),('registry',(943,436,999,486)),('metadata',(948,527,997,580)),('indices',(946,618,1001,664)),('retrieval',(1393,350,1446,401)),('graph',(1405,564,1476,630))]:icon(name,roi)
# Labels copied verbatim from the supplied reference.
text(58,386,140,40,'Browser',27,True,'center');text(55,621,151,40,'Agent / CLI',27,True,'center')
text(325,323,99,50,'Nuxt Web',21,True,'center');text(498,315,96,58,'<b>FastAPI</b><br>(Parsing)',22,False,'center');text(665,321,82,55,'MinerU',22,True,'center')
text(751,365,118,53,'Parsed<br>Markdown',21,False,'center')
text(353,543,149,37,'MCP',26,True);text(353,579,149,38,'Tool Server',26);text(381,742,180,32,'Laya',26,True);text(381,773,181,31,'(Evidence Scoring)',20)
text(362,659,145,30,'(Optional)',20,False,'center',font='Courier New')
text(560,498,332,58,'<b>Management Ops</b><br>(e.g., import, organize, update)',21)
text(562,586,300,26,'Retrieval Ops',21,True);text(562,620,300,25,'(e.g., search, get, evidence)',20)
for yy,title,sub in [(335,'Document Files','(source &amp; parsed)'),(425,'Tree Registry','(hierarchy &amp; structure)'),(514,'Library Metadata','(collections &amp; attributes)'),(604,'Dense + BM25 Indices','(retrieval indexes)')]:
 text(1025,yy+7,244,33,title,22 if title.startswith('Dense') else 25,True);text(1025,yy+39,244,27,sub,20)
text(1452,342,258,31,'Retrieval',26,True);text(1452,375,257,26,'(ChromaDB / BGE-M3 + BM25)',17)
text(1491,564,218,32,'Neo4j Graph',26,True);text(1491,596,218,28,'(Navigation Only)',21)
ET.indent(mx,space='  ');ET.ElementTree(mx).write(D/'architecture.drawio',encoding='utf-8',xml_declaration=True)
print('cells',n)
