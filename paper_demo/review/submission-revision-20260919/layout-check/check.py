import fitz,json,hashlib,pathlib,collections,re
root=pathlib.Path('rag-knowledge/paper_demo'); out=root/'review/submission-revision-20260919/layout-check'
pdf=root/'tex/main.pdf'; d=fitz.open(pdf)
result={'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':[],'fonts':[],'figures':[]}
for i,p in enumerate(d):
 p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(out/f'page-{i+1}.png')
 spans=[s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
 (out/f'page-{i+1}.txt').write_text(p.get_text(),encoding='utf-8')
 result['pages'].append({'page':i+1,'size':list(p.rect),'images':len(p.get_images()),'drawings':len(p.get_drawings()),'sizes':dict(collections.Counter(round(s['size'],3) for s in spans)),'outside_page':[s for s in spans if not p.rect.contains(fitz.Rect(s['bbox']))],'links':[l.get('uri') for l in p.get_links() if l.get('uri')],'spans':spans})
for x in sorted(set(f[0] for p in d for f in p.get_fonts(full=True))):
 name,ext,typ,data=d.extract_font(x);result['fonts'].append({'xref':x,'name':name,'type':typ,'ext':ext,'bytes':len(data)})
for f in sorted((root/'figures/submission-20260919').glob('*.pdf')):
 fd=fitz.open(f); p=fd[0]; spans=[s for b in p.get_text('dict')['blocks'] if 'lines'in b for l in b['lines'] for s in l['spans']]
 result['figures'].append({'name':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'size':list(p.rect),'images':len(p.get_images()),'drawings':len(p.get_drawings()),'text':p.get_text(),'min_native_font':min(s['size'] for s in spans)})
result['frozen_hashes']={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in list((root/'tex').glob('*.tex'))+[root/'tex/refs.bib',pdf]+list((root/'figures/submission-20260919').glob('*.pdf'))}
(out/'machine-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Rendered',len(d),'pages; embedded fonts',len(result['fonts']),'all embedded',all(f['bytes'] for f in result['fonts']))
for p in result['pages']: print(p['page'],p['size'],'raster',p['images'],'outside',len(p['outside_page']),'sizes',p['sizes'])
