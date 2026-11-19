"""Repair supplementary table layout only; leave the input and all content intact."""
from pathlib import Path
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Twips
from docx.text.paragraph import Paragraph

# Twips, within the 9360-twip text area of the Letter-sized supplement.
WIDTHS = {
    9: (1710, 2410, 4100, 850),
    11: (1550, 2490, 2400, 2630),
    12: (1610, 970, 1100, 1580, 1160, 1460, 1190),
    17: (1670, 2230, 2200, 2970),
}


def element(parent, name, successors=()):
    node = parent.find(qn('w:' + name))
    if node is None:
        node = OxmlElement('w:' + name)
        tags = {qn('w:' + tag) for tag in successors}
        successor = next((child for child in parent if child.tag in tags), None)
        if successor is None:
            parent.append(node)
        else:
            successor.addprevious(node)
    return node


def set_attrs(node, **attrs):
    for name, value in attrs.items():
        node.set(qn('w:' + name), str(value))


def set_margins(properties, vertical, horizontal):
    margins = element(properties, 'tblCellMar', ('tblLook', 'tblCaption', 'tblDescription'))
    for edge, width in (('top', vertical), ('left', horizontal), ('bottom', vertical), ('right', horizontal)):
        set_attrs(element(margins, edge), w=width, type='dxa')


def set_row_rules(properties):
    borders = element(properties, 'tblBorders', ('shd', 'tblLayout', 'tblCellMar', 'tblLook', 'tblCaption'))
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        item = element(borders, edge)
        if edge in ('top', 'bottom'):
            set_attrs(item, val='single', sz=5, space=0, color='777777')
        elif edge == 'insideH':
            set_attrs(item, val='single', sz=4, space=0, color='C0C0C0')
        else:
            set_attrs(item, val='nil')


def text_payload(doc):
    # Include inline math, hyperlinks, text and their original order; formatting
    # elements do not participate. Do not introduce line breaks or edit any runs.
    paths = './/w:t | .//m:t | .//w:br | .//w:tab | .//a:blip'
    return [(node.tag, node.text, tuple(node.attrib.items())) for node in doc.element.xpath(paths)]


def fix(source: Path, destination: Path) -> None:
    doc = Document(source)
    content = text_payload(doc)
    assert len(doc.tables) == 9 and len(doc.inline_shapes) == 5
    for section in doc.sections:
        # Pandoc omitted page geometry; set the effective Letter/1 inch values
        # explicitly so both Word and LibreOffice honor the same width budget.
        for prop, width in (('page_width', 12240), ('page_height', 15840),
                            ('left_margin', 1440), ('right_margin', 1440),
                            ('top_margin', 1440), ('bottom_margin', 1440)):
            if getattr(section, prop) is None:
                setattr(section, prop, Twips(width))
        assert section.page_width.twips - section.left_margin.twips - section.right_margin.twips >= max(map(sum, WIDTHS.values()))
    seen = set()
    for table in doc.tables:
        table_id = table._tbl.tblPr.find(qn('w:tblCaption')).get(qn('w:val'))
        match = re.match(r'^Table S(\d+)\.', table_id)
        assert match, table_id
        number = int(match[1])
        if number not in WIDTHS:
            continue
        seen.add(number)
        widths = WIDTHS[number]
        assert len(table.columns) == len(widths), (number, len(table.columns))
        props = table._tbl.tblPr
        set_attrs(props.find(qn('w:tblW')), type='dxa', w=sum(widths))
        table.autofit = False
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        for col, width in zip(table.columns, widths):
            col.width = Twips(width)
        separated = number in (11, 17)
        set_margins(props, vertical=55 if separated else 26, horizontal=85)
        if separated:
            set_row_rules(props)
        caption = Paragraph(table._tbl.getprevious(), doc._body)
        assert caption.text.startswith(f'Table S{number}.'), caption.text
        caption.paragraph_format.keep_with_next = True
        caption.paragraph_format.keep_together = True
        if number == 17:
            caption.paragraph_format.page_break_before = True
        for row_idx, row in enumerate(table.rows):
            assert len(row.cells) == len(widths)
            pr = row._tr.get_or_add_trPr()
            element(pr, 'cantSplit', ('tblHeader', 'tblCellSpacing', 'jc', 'hidden'))
            if row_idx == 0:
                element(pr, 'tblHeader', ('tblCellSpacing', 'jc', 'hidden'))
            for cell, width in zip(row.cells, widths):
                cell.width = Twips(width)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                if separated and row_idx == 0:
                    cell_pr = cell._tc.get_or_add_tcPr()
                    borders = element(cell_pr, 'tcBorders', ('shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign'))
                    set_attrs(element(borders, 'bottom'), val='single', sz=5, space=0, color='777777')
                if number == 17:
                    for para in cell.paragraphs:
                        para.paragraph_format.keep_with_next = row_idx < len(table.rows) - 1
    assert seen == set(WIDTHS)
    assert text_payload(doc) == content
    with destination.open('xb') as out:
        doc.save(out)
    saved = Document(destination)
    assert text_payload(saved) == content
    print('Repaired S9, S11, S12 and S17; text, math, image references and their order unchanged.')


if __name__ == '__main__':
    fix(*map(Path, sys.argv[1:3]))
