from pathlib import Path
import base64
import re
import xml.etree.ElementTree as ET
import vtracer

here = Path(__file__).resolve().parent
tree = ET.parse(here / 'workflow.drawio')
root = tree.getroot()
graph = root.find('.//root')
cells = {c.get('id'): c for c in graph.findall('mxCell')}

# Remove the balance icon: the text must fit well inside the decision diamond.
graph.remove(cells['76'])
label = cells['96']
label.set('value', 'Use Laya<br>scoring?')
label.set('style', re.sub(r'fontSize=\d+', 'fontSize=29', label.get('style')))
g = label.find('mxGeometry')
g.set('x', '1522'); g.set('y', '209'); g.set('width', '144'); g.set('height', '56')

# An agent performs review in the intended workflow. The caption separately
# explains that this is not an API-enforced universal gate.
for c in graph.findall('mxCell'):
    if c.get('value') == 'Quality review<br>(agent, optional)':
        c.set('value', 'Agent quality<br>review')

# Make collection storage visibly independent of the optional index step by
# ordering the two blocks as Save -> collection -> entry-point-dependent index.
for ident, y in [('25','612'),('26','491'),('68','631'),('69','497'),('88','618'),('89','493')]:
    cells[ident].find('mxGeometry').set('y',y)
cells['25'].find('mxGeometry').set('height','105')
cells['26'].find('mxGeometry').set('height','79')
cells['69'].find('mxGeometry').set('height','68')

# Keep longer labels fully inside the original cards at the requested size.
for c in graph.findall('mxCell'):
    v=c.get('value','')
    if v == 'Pinned vector /<br>two-stage search':
        c.set('value','Pinned vector<br>/ two-stage<br>search')
        c.find('mxGeometry').set('y','377')
        c.find('mxGeometry').set('height','102')
    elif v == 'Laya scoring':
        c.set('value','Laya<br>scoring')
        c.find('mxGeometry').set('y','195')
        c.find('mxGeometry').set('height','72')
    elif v == 'Supported<br>answer<br>with sources':
        c.set('value','Supported<br>answer<br>+ sources')
    elif v == 'Incomplete /<br>tool failure':
        c.set('value','Incomplete<br>tool failure')
    elif v == 'Index<br>(entry-point dependent)':
        c.set('value','Index (entry-point<br>dependent)')
    elif v == 'Candidate documents':
        c.find('mxGeometry').set('x','1102')

# Increase the canvas and panel height just enough for the global failure note.
root.find('.//mxGraphModel').set('pageHeight','820')
cells['2'].find('mxGeometry').set('height','818')
for c in graph.findall('mxCell'):
    g0=c.find('mxGeometry')
    if g0 is not None and g0.get('y')=='58' and g0.get('height')=='680':
        g0.set('height','714')

def set_points(ident, coords, start=False):
    cell = cells[ident]
    geom = cell.find('mxGeometry')
    for child in list(geom):
        geom.remove(child)
    ET.SubElement(geom, 'mxPoint', x=str(coords[0][0]), y=str(coords[0][1]), **{'as':'sourcePoint'})
    ET.SubElement(geom, 'mxPoint', x=str(coords[-1][0]), y=str(coords[-1][1]), **{'as':'targetPoint'})
    if len(coords)>2:
        arr = ET.SubElement(geom,'Array',**{'as':'points'})
        for x,y in coords[1:-1]: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    cell.set('style', re.sub(r'startArrow=[^;]+', 'startArrow=none',cell.get('style')))

set_points('61', [(681,570),(681,610)])
cells['61'].set('style', cells['61'].get('style')+'dashed=1;dashPattern=7 5;')
set_points('58', [(900,531),(960,531),(960,347),(977,347)])
# Review, not parse, connects the acquisition and organisation stages.
set_points('56', [(398,626),(426,626),(426,211),(462,211)])
graph.remove(cells['57'])

# The failure outcome can be reached throughout execution, not just after read.
next_id = max(int(c.get('id')) for c in graph.findall('mxCell')) + 1
note = ET.SubElement(graph,'mxCell',id=str(next_id),value='Any stage: failure / timeout',
    style='text;html=1;whiteSpace=nowrap;strokeColor=none;fillColor=none;fontFamily=Arial;fontSize=28;fontColor=#3b4f66;fontStyle=2;align=center;verticalAlign=middle;',vertex='1',parent='1')
ET.SubElement(note,'mxGeometry',x='1469',y='729',width='504',height='38',**{'as':'geometry'})
note2 = ET.SubElement(graph,'mxCell',id=str(next_id+1),value='if triggered',
    style='text;html=1;whiteSpace=nowrap;strokeColor=none;fillColor=none;fontFamily=Arial;fontSize=29;fontColor=#3b4f66;align=left;verticalAlign=middle;',vertex='1',parent='1')
ET.SubElement(note2,'mxGeometry',x='700',y='572',width='180',height='37',**{'as':'geometry'})

# Convert every embedded bitmap icon into path-based SVG. These are separate
# draw.io image objects, but contain vector paths rather than bitmap pixels.
count = 0
for cell in graph.findall('mxCell'):
    style=cell.get('style','')
    match=re.search(r'image=data:image/png,([^;]+)',style)
    if not match: continue
    svg=vtracer.convert_raw_image_to_svg(base64.b64decode(match.group(1)),img_format='png',colormode='color',hierarchical='stacked',mode='spline',filter_speckle=2,color_precision=6,layer_difference=16,corner_threshold=60,length_threshold=4.0,max_iterations=10,splice_threshold=45,path_precision=2)
    encoded=base64.b64encode(svg.encode('utf-8')).decode('ascii')
    cell.set('style',style[:match.start()]+'image=data:image/svg+xml,'+encoded+style[match.end():])
    count+=1

# Raise the smallest type so the final double-column figure reaches 8 pt.
for c in graph.findall('mxCell'):
    s=c.get('style','')
    m=re.search(r'fontSize=(\d+)',s)
    if m and int(m.group(1)) < 31:
        c.set('style', s[:m.start(1)]+'31'+s[m.end(1):])

ET.indent(root,space='  ')
out=here/'workflow_vector.drawio'
tree.write(out,encoding='utf-8',xml_declaration=True)
print(f'Wrote {out}, converted {count} icons to SVG paths')
