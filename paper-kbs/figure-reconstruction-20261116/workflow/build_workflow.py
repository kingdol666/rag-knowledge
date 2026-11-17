from pathlib import Path
import base64, io, xml.etree.ElementTree as ET
from PIL import Image

HERE = Path(__file__).resolve().parent
REF = Path(r'C:\Users\87287\AppData\Local\Temp\codex-clipboard-da681d0d-38bf-446b-a6b3-8ed6c75dc78c.png')
im = Image.open(REF).convert('RGB')
root = ET.Element('mxfile', host='app.diagrams.net', version='24.7.17', type='device')
diagram = ET.SubElement(root, 'diagram', name='Workflow')
model = ET.SubElement(diagram, 'mxGraphModel', dx='1997', dy='788', grid='0', guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1', pageScale='1', pageWidth='1997', pageHeight='788', math='0', shadow='0')
graph = ET.SubElement(model, 'root')
ET.SubElement(graph, 'mxCell', id='0'); ET.SubElement(graph, 'mxCell', id='1', parent='0')
seq = 1
def cell(x,y,w,h,style,value=''):
 global seq
 seq += 1
 c=ET.SubElement(graph,'mxCell',id=str(seq),value=value,style=style,vertex='1',parent='1')
 ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
 return c
def text(x,y,w,h,s,size=30,bold=False,align='left'):
 return cell(x,y,w,h,f'text;html=1;whiteSpace=nowrap;overflow=visible;strokeColor=none;fillColor=none;fontFamily=Arial;fontSize={size};fontColor=#000000;fontStyle={1 if bold else 0};align={align};verticalAlign=middle;spacing=0;',s.replace('\n','<br>'))
def rect(x,y,w,h,fill='#d7e9fd',line='none',rounded=True,dashed=False):
 return cell(x,y,w,h,f'rounded={1 if rounded else 0};absoluteArcSize=1;arcSize=30;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={line};strokeWidth=2;'+('dashed=1;dashPattern=8 6;' if dashed else ''))
def edge(points, end=True, start=False, dashed=False, width=4):
 global seq
 seq+=1
 c=ET.SubElement(graph,'mxCell',id=str(seq),value='',style=f'edgeStyle=none;rounded=1;roundedArcSize=12;html=1;strokeColor=#000000;strokeWidth={width};endArrow={"block" if end else "none"};endFill=1;endSize=7;startArrow={"block" if start else "none"};startFill=1;startSize=7;'+('dashed=1;dashPattern=8 6;' if dashed else ''),edge='1',parent='1')
 g=ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
 ET.SubElement(g,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),**{'as':'sourcePoint'})
 ET.SubElement(g,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),**{'as':'targetPoint'})
 if len(points)>2:
  a=ET.SubElement(g,'Array',**{'as':'points'})
  for p in points[1:-1]:ET.SubElement(a,'mxPoint',x=str(p[0]),y=str(p[1]))
def icon(x,y,w,h):
 # Each small reference artwork is a separately movable image object. Near-background
 # pale pixels are made transparent; strong colored foreground remains as in the source.
 crop=im.crop((x,y,x+w,y+h)).convert('RGBA')
 px=crop.load()
 for j in range(h):
  for i in range(w):
   r,g,b,a=px[i,j]
   mx=max(r,g,b); mn=min(r,g,b)
   if x==1547 and max(r,g,b)<120: px[i,j]=(r,g,b,0)
   elif mx-mn<45 and mn>180: px[i,j]=(r,g,b,0)
   elif r>180 and g>205 and b>225: px[i,j]=(r,g,b,0)
 out=io.BytesIO();crop.save(out,format='PNG')
 data=base64.b64encode(out.getvalue()).decode()
 return cell(x,y,w,h,f'shape=image;imageAspect=0;aspect=fixed;verticalLabelPosition=bottom;verticalAlign=top;image=data:image/png,{data};')

# Preserve the original 1997 x 788 canvas when draw.io crops the export.
rect(1,1,1995,786,'#fdfdfd','none',False)
# Four framed stages with flat-bottom blue headers.
stages=[(18,58,395,680,'Stage 1: Acquire'),(446,58,466,680,'Stage 2: Organize'),(946,58,481,680,'Stage 3: Retrieve'),(1453,58,527,680,'Stage 4: Inspect and report')]
for x,y,w,h,title in stages:
 rect(x,y,w,h,'#ffffff','#c8cfd5')
 rect(x+1,y+1,w-2,72,'#98c3ed','none')
 rect(x+1,y+38,w-2,35,'#98c3ed','none',False)
 text(x+30,y+7,w-55,52,title,36,True)

# Cards in the same order, size and position as the raster reference.
for box in [(37,174,362,120),(37,356,362,130),(39,566,359,120),
            (462,162,438,99),(462,292,438,80),(462,384,438,84),(462,491,438,79),(462,612,438,105),
            (975,158,438,74),(978,298,216,59),(979,385,221,58),(979,474,221,60),(1215,307,203,197),(994,618,420,87),
            (1757,192,216,82),(1470,399,497,70),(1471,556,160,158),(1643,556,156,158),(1812,556,162,158)]:
 rect(*box)
# Dashed robot review box and the optional Laya diamond.
rect(39,566,359,120,'#e3f0fd','#263748',True,True)
cell(1488,151,212,171,'rhombus;whiteSpace=wrap;html=1;fillColor=#e4f1fd;strokeColor=#182a3b;strokeWidth=2;dashed=1;dashPattern=7 6;')

# Native editable connectors.
for p in [[(225,294),(225,352)],[(225,486),(225,563)],[(681,262),(681,290)],[(681,372),(681,382)],[(681,468),(681,490)],
          [(1089,357),(1089,383)],[(1089,443),(1089,473)],[(1198,231),(1198,257),(1087,257),(1087,297)],[(1198,257),(1311,257),(1311,305)],
          [(1090,534),(1090,567),(1205,567),(1205,616)],
          [(1700,234),(1757,234)],[(1590,321),(1590,396)],[(1867,274),(1867,368),(1746,368),(1746,396)],
          [(1719,469),(1719,507),(1550,507),(1550,553)],[(1719,507),(1719,553)],[(1719,507),(1890,507),(1890,553)],
          [(414,405),(445,405)],[(913,405),(946,405)],[(900,670),(960,670),(960,347),(977,347)],[(1415,662),(1451,662),(1451,234),(1488,234)]]:
 edge(p)
# The branch joins the other route without an extra arrowhead; index/collection is bidirectional.
edge([(1312,503),(1312,567),(1205,567)],end=False)
edge([(681,570),(681,610)],end=True,start=True,width=3)

# Independent pictograms cropped from the given image. Labels, cards and lines stay editable.
icons=[(69,190,85,91),(65,377,89,90),(55,584,92,88),
       (493,177,77,69),(497,307,67,59),(493,399,70,58),(491,496,87,69),(495,625,89,78),
       (1070,163,61,57),(993,307,49,43),(1001,391,48,44),(998,480,49,49),(1285,325,65,60),(1026,627,68,68),
       (1547,160,75,55),(1772,201,48,55),(1530,405,105,58),(1493,562,99,56),(1689,560,74,56),(1852,560,68,56)]
for i in icons: icon(*i)

# Text is not burned into icons and can be edited as normal Draw.io text.
labels=[(184,190,200,78,'Documents',32,False,'left'),(190,365,190,111,'Parse when\nrequired\n(MinerU)',31,False,'left'),(168,581,220,85,'Quality review\n(agent, optional)',30,False,'left'),
 (592,168,295,85,'Content-based\ncollection assignment',30,False,'left'),(598,299,292,64,'Descriptions and tags',30,False,'left'),(602,394,260,61,'Save',31,False,'left'),(601,496,280,65,'Index\n(entry-point dependent)',28,False,'left'),(603,628,270,75,'Managed collection\n(shared)',30,True,'left'),
 (1159,168,235,55,'User question',31,False,'left'),(1058,306,126,43,'Catalogue',28,False,'left'),(1070,390,120,43,'Shelf',29,False,'left'),(1062,480,130,43,'Document',29,False,'left'),(1221,387,189,73,'Pinned vector /\ntwo-stage search',25,False,'center'),(1112,630,287,58,'Candidate documents',29,False,'left'),
 (1524,215,133,67,'Optional\nLaya scoring',28,False,'center'),(1824,204,145,54,'Laya scoring',26,False,'left'),(1659,406,268,58,'Read evidence',31,False,'left'),
 (1474,627,153,73,'Supported\nanswer\nwith sources',25,False,'center'),(1645,620,151,76,'Completed\nreview:\nno support',25,False,'center'),(1816,620,152,77,'Incomplete /\ntool failure',25,False,'center'),
 (1701,191,52,33,'Yes',25,False,'left'),(1602,328,40,35,'No',25,False,'left')]
for args in labels:text(*args)
ET.indent(root,space='  ')
(HERE/'workflow.drawio').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
print('wrote', HERE/'workflow.drawio', 'cells',seq)
