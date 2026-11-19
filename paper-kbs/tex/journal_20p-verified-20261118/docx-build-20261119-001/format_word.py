from docx import Document
from docx.shared import Inches, Pt, Twips
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:3])
doc = Document(source)
widths = [
    [1100, 1700, 1800, 1700, 1620],
    [1150, 1470, 1520, 1150, 1600, 1030],
    [1200, 2300, 3200, 1220],
    [1150, 1550, 1900, 1450, 1870],
]
assert len(doc.tables) == len(widths)
for table, cols in zip(doc.tables, widths):
    assert len(table.columns) == len(cols)
    table.autofit = False
    for col, width in zip(table.columns, cols):
        col.width = Twips(width)
    for row in table.rows:
        trpr = row._tr.get_or_add_trPr()
        if trpr.find(qn('w:cantSplit')) is None:
            trpr.append(OxmlElement('w:cantSplit'))
        for cell, width in zip(row.cells, cols):
            cell.width = Twips(width)
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.space_before = Pt(0)
                for run in para.runs:
                    run.font.size = Pt(9)

images = 0
for index, para in enumerate(doc.paragraphs):
    if para._p.xpath('.//w:drawing'):
        assert index + 1 < len(doc.paragraphs)
        cap = doc.paragraphs[index + 1]
        assert cap.style.name == 'Image Caption'
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.keep_together = True
        cap.paragraph_format.keep_together = True
        images += 1
assert images == 9
for shape in doc.inline_shapes:
    if shape.height > Inches(4.4):
        factor = Inches(4.4) / shape.height
        shape.width = int(shape.width * factor)
        shape.height = Inches(4.4)
doc.save(target)
print(f'Formatted {len(widths)} tables and {images} figure-caption pairs')
