from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import sys

source, dest = map(Path, sys.argv[1:3])
doc = Document(source)
assert doc.tables[3].rows[0].cells[-1].text == 'Intended terminal report'
for index in (0, 1, 3):
    table = doc.tables[index]
    for cell in table.rows[0].cells:
        tcpr = cell._tc.get_or_add_tcPr()
        borders = tcpr.find(qn('w:tcBorders'))
        if borders is None:
            borders = OxmlElement('w:tcBorders')
            tcpr.append(borders)
        for edge in ('top', 'bottom'):
            border = borders.find(qn('w:' + edge))
            if border is None:
                border = OxmlElement('w:' + edge)
                borders.append(border)
            for attr, value in [('val', 'single'), ('sz', '6'), ('color', '000000'), ('space', '0')]:
                border.set(qn('w:' + attr), value)
        margins = tcpr.find(qn('w:tcMar'))
        if margins is None:
            margins = OxmlElement('w:tcMar')
            tcpr.append(margins)
        for edge in ('top', 'bottom'):
            margin = margins.find(qn('w:' + edge))
            if margin is None:
                margin = OxmlElement('w:' + edge)
                margins.append(margin)
            margin.set(qn('w:w'), '65')
            margin.set(qn('w:type'), 'dxa')
    # Keep first body line and the separator apart.
    for cell in table.rows[1].cells:
        tcpr = cell._tc.get_or_add_tcPr()
        margins = tcpr.find(qn('w:tcMar'))
        if margins is None:
            margins = OxmlElement('w:tcMar')
            tcpr.append(margins)
        top = margins.find(qn('w:top'))
        if top is None:
            top = OxmlElement('w:top')
            margins.append(top)
        top.set(qn('w:w'), '60')
        top.set(qn('w:type'), 'dxa')

# Add the missing closing rule beneath Table 4's last row.
for cell in doc.tables[3].rows[-1].cells:
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn('w:tcBorders'))
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        tcpr.append(borders)
    bottom = OxmlElement('w:bottom')
    for attr, value in [('val', 'single'), ('sz', '6'), ('color', '000000'), ('space', '0')]:
        bottom.set(qn('w:' + attr), value)
    borders.append(bottom)
    margins = OxmlElement('w:tcMar')
    margin = OxmlElement('w:bottom')
    margin.set(qn('w:w'), '65')
    margin.set(qn('w:type'), 'dxa')
    margins.append(margin)
    tcpr.append(margins)

# The OMML has the right symbols but LibreOffice displays the ceiling poorly.
# Replace only this inline object with an editable equivalent, unambiguous in both engines.
found = 0
for para in doc.paragraphs:
    for math in para._p.xpath('./m:oMath'):
        formula = ''.join(node.text or '' for node in math.iter(qn('m:t')))
        if formula == '⌈3n/5⌉':
            run = OxmlElement('w:r')
            text = OxmlElement('w:t')
            text.text = 'ceil(3n/5)'
            run.append(text)
            math.getparent().replace(math, run)
            found += 1
assert found == 1
# Courier New has visibly different lower-case l and digit 1.
doc.styles['Verbatim Char'].font.name = 'Courier New'
doc.save(dest)
print('Adjusted Tables 1, 2, 4; replaced one equation with editable equivalent; set code font')
