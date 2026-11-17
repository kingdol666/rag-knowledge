from pathlib import Path
import xml.etree.ElementTree as ET
import base64, urllib.parse, re, vtracer
here=Path(__file__).resolve().parent
tree=ET.parse(here/'architecture.drawio');root=tree.getroot();graph=root.find('.//root');cells={c.get('id'):c for c in graph.findall('mxCell')};count=0
for c in graph.findall('mxCell'):
 style=c.get('style',''); m=re.search(r'image=data:image/png%3Bbase64,([^;]+)',style)
 if not m: continue
 raw=base64.b64decode(urllib.parse.unquote(m.group(1)))
 svg=vtracer.convert_raw_image_to_svg(raw,img_format='png',colormode='color',hierarchical='stacked',mode='spline',filter_speckle=2,color_precision=6,layer_difference=16,corner_threshold=60,length_threshold=4.0,max_iterations=10,splice_threshold=45,path_precision=2)
 data=base64.b64encode(svg.encode('utf8')).decode('ascii'); c.set('style',style[:m.start()]+'image=data:image/svg+xml,'+data+style[m.end():]);count+=1
for c in graph.findall('mxCell'):
 style=c.get('style','');m=re.search(r'fontSize=(\d+)',style)
 if m and int(m.group(1))<24:c.set('style',style[:m.start(1)]+'24'+style[m.end(1):])
def geometry(i,**kw):
 for k,v in kw.items():cells[i].find('mxGeometry').set(k,str(v))
# Widen the Nuxt card enough for its label; move the outbound line endpoint.
# the labels and symbols remain editable draw.io objects.
for c in graph.findall('mxCell'):
 g=c.find('mxGeometry')
 if g is not None and g.get('x')=='267' and g.get('y')=='306' and g.get('width')=='162':g.set('width','171')
 if c.get('edge')=='1' and g is not None:
  for p in g.findall('mxPoint'):
   if p.get('x')=='429' and p.get('y')=='348':p.set('x','438')
geometry('58',x=324,width=110)
for id in ('58','59','65'):
 cells[id].set('style',cells[id].get('style').replace('fontFamily=Arial;','fontFamily=Arial Narrow;'))
geometry('59',x=503,width=91)
# Abbreviate illustrative examples to keep this label inside the dashed group.
cells['67'].set('value','<b>Management Ops</b><br>(import / organize / update)')
cells['69'].set('value','(search / get / evidence)')
# Subtitles fit their cards after enlargement.
geometry('75',x=1018,width=257)
cells['76'].set('style',cells['76'].get('style').replace('fontFamily=Arial;','fontFamily=Arial Narrow;'))
# Keep the full retrieval configuration, wrapping into two lines.
cells['79'].set('value','(ChromaDB / BGE-M3<br>+ BM25)');geometry('79',y=375,height=60)
for c in graph.findall('mxCell'):
 g=c.find('mxGeometry')
 if g is not None and g.get('x')=='1379' and g.get('y')=='324' and g.get('width')=='342':g.set('height','118')
# Parsing yields an artefact; a separate save operation makes it managed.
n=max(int(c.get('id')) for c in graph.findall('mxCell'))+1
note=ET.SubElement(graph,'mxCell',id=str(n),value='save',style='text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;strokeColor=none;fillColor=#FFFFFF;fontFamily=Arial;fontSize=24;fontColor=#000000;',vertex='1',parent='1')
ET.SubElement(note,'mxGeometry',x='836',y='311',width='63',height='30',**{'as':'geometry'})
ET.indent(root,space='  ');tree.write(here/'architecture_vector.drawio',encoding='utf-8',xml_declaration=True)
print('converted icons:',count)
