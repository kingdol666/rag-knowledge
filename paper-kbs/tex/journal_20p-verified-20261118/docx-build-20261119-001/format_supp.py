from pathlib import Path
import sys
from docx import Document
from docx.shared import Pt, Twips, Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

source, target = map(Path, sys.argv[1:3])
doc = Document(source)
widths = [
    [1050, 2300, 3500, 1070],
    [850, 1700, 2050, 1900, 1420],
    [1250, 2400, 2150, 2120],
    [1150, 1300, 1150, 1150, 1050, 1000, 1120],
    [1400, 2300, 1400, 1400, 1420],
    [630, 2000, 1050] + [470] * 9,
    [1900, 900, 850, 850, 900, 1200, 1320],
    [1500, 3210, 3210],
    [1400, 2000, 2100, 2420],
]
assert len(doc.tables) == len(widths)
for idx, (table, cols) in enumerate(zip(doc.tables, widths)):
    assert len(table.columns) == len(cols), (idx, len(table.columns), len(cols))
    table.autofit = False
    for col, width in zip(table.columns, cols):
        col.width = Twips(width)
    for row_idx, row in enumerate(table.rows):
        trpr = row._tr.get_or_add_trPr()
        if trpr.find(qn('w:cantSplit')) is None:
            trpr.append(OxmlElement('w:cantSplit'))
        if row_idx == 0 or (idx == 5 and row_idx == 1):
            if trpr.find(qn('w:tblHeader')) is None:
                trpr.append(OxmlElement('w:tblHeader'))
        # Iterate physical cells so column-spanning header cells get correct widths.
        position = 0
        for cell in row._tr.tc_lst:
            tcpr = cell.get_or_add_tcPr()
            span_node = tcpr.find(qn('w:gridSpan'))
            span = int(span_node.get(qn('w:val'))) if span_node is not None else 1
            tcw = tcpr.find(qn('w:tcW'))
            if tcw is None:
                tcw = OxmlElement('w:tcW')
                tcpr.insert(0, tcw)
            tcw.set(qn('w:w'), str(sum(cols[position:position + span])))
            tcw.set(qn('w:type'), 'dxa')
            position += span
        assert position == len(cols), (idx, row_idx, position)
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.space_before = Pt(0)
                for run in para.runs:
                    run.font.size = Pt(8 if idx == 5 else 9)

for para in doc.paragraphs:
    if para._p.xpath('.//w:drawing'):
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.keep_together = True
for shape in doc.inline_shapes:
    if shape.height > Inches(4.4):
        factor = Inches(4.4) / shape.height
        shape.width = int(shape.width * factor)
        shape.height = Inches(4.4)
doc.save(target)
print('Formatted nine supplementary tables and five images')
