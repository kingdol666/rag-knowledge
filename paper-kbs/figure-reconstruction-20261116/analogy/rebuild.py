import base64,io
from PIL import Image
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,ElementTree

out=Path(__file__).parent
src=Image.open(r'C:\Users\87287\AppData\Local\Temp\codex-clipboard-6a1dd2d0-1682-4aac-9512-26df1c3ed46c.png').convert('RGB')
root=Element('mxfile',{'host':'app.diagrams.net','modified':'2026-11-16T00:00:00.000Z','agent':'draw.io','version':'24.7.17','type':'device'})
diag=SubElement(root,'diagram',{'id':'library-hmrs','name':'Library and HMRS'})
model=SubElement(diag,'mxGraphModel',{'dx':'1752','dy':'897','grid':'1','gridSize':'10','guides':'1','tooltips':'1','connect':'1','arrows':'1','fold':'1','page':'1','pageScale':'1','pageWidth':'1752','pageHeight':'897','math':'0','shadow':'0','background':'#ffffff'})
rt=SubElement(model,'root');SubElement(rt,'mxCell',{'id':'0'});SubElement(rt,'mxCell',{'id':'1','parent':'0'}); n=1

def rect(x,y,w,h,style,value=''):
 global n
 n+=1;c=SubElement(rt,'mxCell',{'id':str(n),'value':value,'style':style,'vertex':'1','parent':'1'});SubElement(c,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'});return c

def edge(points,style):
 global n
 n+=1;c=SubElement(rt,'mxCell',{'id':str(n),'value':'','style':style,'edge':'1','parent':'1'});g=SubElement(c,'mxGeometry',{'relative':'1','as':'geometry'});SubElement(g,'mxPoint',{'x':str(points[0][0]),'y':str(points[0][1]),'as':'sourcePoint'});SubElement(g,'mxPoint',{'x':str(points[-1][0]),'y':str(points[-1][1]),'as':'targetPoint'})
 if len(points)>2:
  a=SubElement(g,'Array',{'as':'points'})
  for x,y in points[1:-1]:SubElement(a,'mxPoint',{'x':str(x),'y':str(y)})

# Draw every card, connector and text as a separate native editable object.
rect(1,1,1750,895,'strokeColor=none;fillColor=#ffffff;')
card='rounded=1;arcSize=16;whiteSpace=wrap;html=0;strokeColor=#050505;strokeWidth=2.7;fillColor=#ffffff;'
head='rounded=1;arcSize=16;whiteSpace=wrap;html=0;strokeColor=#050505;strokeWidth=2.7;fillColor=#d5e6f6;gradientColor=#cbdff0;gradientDirection=south;'
rect(59,30,590,102,head);rect(796,30,626,102,head)
for x,y,w,h in [(59,173,590,139),(796,173,626,139),(59,365,590,129),(796,365,626,129),(59,541,590,128),(796,541,626,128),(59,714,590,136),(796,714,563,136)]:rect(x,y,w,h,card)
rect(1400,782,312,95,'rounded=1;arcSize=14;whiteSpace=wrap;html=0;strokeColor=#000000;strokeWidth=2.5;dashed=1;dashPattern=6 5;fillColor=#ffffff;')
line='endArrow=none;startArrow=none;html=0;rounded=0;strokeColor=#7890a3;strokeWidth=1.8;dashed=1;dashPattern=6 5;'
for y in (241,426,601,780):edge([(649,y),(796,y)],line)
arrow='endArrow=block;endFill=1;endSize=10;startArrow=none;html=0;rounded=0;strokeColor=#000000;strokeWidth=3;'
for x in (354,1109):
 for y1,y2 in ((312,365),(494,541),(669,714)):edge([(x,y1),(x,y2)],arrow)
edge([(1359,738),(1553,738),(1553,782)],'endArrow=block;endFill=1;endSize=8;startArrow=none;html=0;rounded=0;strokeColor=#667b89;strokeWidth=2;dashed=1;dashPattern=6 5;')
# Icons are individually embedded crops, for exact reproduction; movable and replaceable in draw.io.
icons=[('catalogue',(108,200,268,294)),('shelf',(123,376,268,482)),('book',(145,550,257,657)),('passage',(105,729,282,838)),('folder',(836,192,970,295)),('list',(844,379,974,482)),('document',(864,550,975,658)),('segment',(843,729,975,835))]
for name,box in icons:
 im=src.crop(box).convert('RGBA'); px=im.load()
 # Remove white surroundings while retaining original line-art antialiasing approximately.
 for yy in range(im.height):
  for xx in range(im.width):
   r,g,b,a=px[xx,yy]
   if r>248 and g>248 and b>248: px[xx,yy]=(255,255,255,0)
 buf=io.BytesIO();im.save(buf,format='PNG'); b64=base64.b64encode(buf.getvalue()).decode()
 x0,y0,x1,y1=box
 rect(x0,y0,x1-x0,y1-y0,'shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;image=data:image/png,'+b64+';')
text='text;html=0;align=center;verticalAlign=middle;whiteSpace=wrap;strokeColor=none;fillColor=none;fontFamily=Arial;fontStyle=1;fontColor=#080808;'
rect(87,38,548,80,text+'fontSize=51;','Library search')
rect(827,38,585,80,text+'fontSize=52;','HMRS access')
for x,y,w,h,s,v in [(257,180,330,118,44,'Catalogue'),(215,365,330,117,44,'Shelf'),(218,541,330,117,44,'Book'),(255,719,330,120,44,'Passage'),(977,179,435,118,40,'Collection catalogue'),(972,365,420,117,44,'Document shelf'),(915,541,420,117,44,'Document'),(929,719,370,120,44,'Segment'),(1410,789,293,80,32,'Evidence scoring\n(optional)')]:rect(x,y,w,h,text+'fontSize='+str(s)+';',v)
ElementTree(root).write(out/'library-hmrs.drawio',encoding='utf-8',xml_declaration=True)
print('Wrote',out/'library-hmrs.drawio')

