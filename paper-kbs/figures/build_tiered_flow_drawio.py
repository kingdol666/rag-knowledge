"""Create an editable draw.io diagram for the tiered retrieval workflow."""
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

OUT = Path(__file__).resolve().parents[1] / 'tex' / 'journal_20p' / 'figs'
OUT.mkdir(parents=True, exist_ok=True)
root = Element('mxfile', host='app.diagrams.net', version='24.7.17')
page = SubElement(root, 'diagram', name='Tiered access', id='tiered-access')
model = SubElement(page, 'mxGraphModel', dx='1100', dy='680', grid='1', gridSize='10',
                   guides='1', tooltips='1', connect='1', arrows='1', fold='1',
                   page='1', pageScale='1', pageWidth='1220', pageHeight='700',
                   math='0', shadow='0')
cells = SubElement(model, 'root')
SubElement(cells, 'mxCell', id='0')
SubElement(cells, 'mxCell', id='1', parent='0')

base = ('whiteSpace=wrap;html=0;fontFamily=Arial;fontSize=19;'
        'strokeWidth=2;strokeColor=#40566c;fontColor=#172b3e;')
process = base + 'rounded=1;arcSize=12;fillColor=#f3f7fa;'
terminal = base + 'rounded=1;arcSize=45;fillColor=#eaf2f5;'
decision = base + 'rhombus;fillColor=#ffffff;'

def vertex(name, text, x, y, w, h, style):
    c = SubElement(cells, 'mxCell', id=name, value=text, style=style, vertex='1', parent='1')
    SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})

vertex('question','Question\nand rewrite',20,96,142,64,terminal)
vertex('policy','Choose\npath(s)',205,84,126,90,process)
vertex('pinned','Pinned collections\ntwo-stage or vector',390,26,246,72,process)
vertex('catalog','Catalogue and shelf\ndocument descriptions',390,174,246,72,process)
vertex('candidates','Candidate references\n(optional merge)',688,96,220,64,process)
vertex('gate','Use Laya\ngate?',965,84,140,90,decision)
vertex('judge','Fetch and score\nsegments (Laya)',930,282,210,72,process)
vertex('read','Read selected\ndocuments',660,282,200,72,process)
vertex('complete','Review\ncomplete?',403,273,140,90,decision)
vertex('incomplete','Report incomplete scope\nand partial evidence, if any',65,277,260,82,terminal)
vertex('support','Support\nfound?',403,478,140,90,decision)
vertex('answer','Answer with\nsource references',670,438,225,72,terminal)
vertex('notfound','Scoped not-found\nand blind spots',670,574,225,72,terminal)

def edge(name, source, target, label='', points=(), ports=''):
    style=('edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;'
           'html=0;endArrow=block;endFill=1;strokeWidth=2;strokeColor=#526d84;'
           'fontFamily=Arial;fontSize=20;fontColor=#334c61;labelBackgroundColor=#ffffff;' + ports)
    c=SubElement(cells,'mxCell',id=name,value=label,style=style,edge='1',parent='1',source=source,target=target)
    geom=SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
    if points:
        arr=SubElement(geom,'Array',**{'as':'points'})
        for x,y in points:
            SubElement(arr,'mxPoint',x=str(x),y=str(y))

edge('e1','question','policy',ports='exitX=1;exitY=.5;entryX=0;entryY=.5;')
edge('e2','policy','pinned',ports='exitX=.5;exitY=0;entryX=0;entryY=.5;',points=[(268,62)])
edge('e3','policy','catalog',ports='exitX=.5;exitY=1;entryX=0;entryY=.5;',points=[(268,210)])
edge('e4','pinned','candidates',ports='exitX=1;exitY=.5;entryX=0;entryY=.35;')
edge('e5','catalog','candidates',ports='exitX=1;exitY=.5;entryX=0;entryY=.65;')
edge('e6','candidates','gate',ports='exitX=1;exitY=.5;entryX=0;entryY=.5;')
edge('e7','gate','judge','Yes',ports='exitX=.5;exitY=1;entryX=.5;entryY=0;')
edge('e8','gate','read','No',ports='exitX=.25;exitY=.75;entryX=.5;entryY=0;',points=[(925,205),(925,235),(760,235)])
edge('e9','read','complete',ports='exitX=0;exitY=.5;entryX=1;entryY=.5;')
edge('e10','judge','complete',ports='exitX=.5;exitY=1;entryX=.75;entryY=.75;',points=[(1035,400),(565,400)])
edge('e11','complete','incomplete','No',ports='exitX=0;exitY=.5;entryX=1;entryY=.5;')
edge('e12','complete','support','Yes',ports='exitX=.5;exitY=1;entryX=.5;entryY=0;')
edge('e13','support','answer','Yes',ports='exitX=1;exitY=.35;entryX=0;entryY=.5;')
edge('e14','support','notfound','No',ports='exitX=1;exitY=.65;entryX=0;entryY=.5;')
ElementTree(root).write(OUT / 'fig_tiered_algorithm.drawio', encoding='utf-8', xml_declaration=True)
