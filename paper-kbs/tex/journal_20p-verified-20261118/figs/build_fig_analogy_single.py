from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import pymupdf
p=Path(__file__).parent
im=Image.open(p/'fig_analogy_cropped.png').convert('RGB').crop((0,0,760,800))
d=ImageDraw.Draw(im)
for x0,y0,x1,y1 in [(680,124,760,136),(610,658,760,670)]:
    for y in range(y0,y1):
        d.line((x0,y,x1,y),fill=im.getpixel((20,y)))
# Replace the illustrative report identifier with a generic, legible label.
d.rectangle((502,702,645,768),fill=im.getpixel((506,700)))
font=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf',30)
d.text((527,714),'Source',font=font,fill='#182f47')
im.save(p/'fig_analogy_single_source.png')
W=244; image_h=W*800/760
c=canvas.Canvas(str(p/'fig_analogy_single.pdf'),pagesize=(W,image_h+50))
c.setFillColor(HexColor('#f8f6f2'));c.rect(0,0,W,image_h+50,fill=1,stroke=0)
c.drawImage(str(p/'fig_analogy_single_source.png'),0,50,width=W,height=image_h)
c.setFillColor(HexColor('#182f47'));c.setFont('Helvetica',9)
for text,y in [('Catalogue  -  Collection',34),('Shelf  -  Document',21),('Page  -  Segment',8)]:
    c.drawCentredString(W/2,y,text)
c.save()
pdf=pymupdf.open(p/'fig_analogy_single.pdf')
pdf[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(p/'fig_analogy_single.png')
