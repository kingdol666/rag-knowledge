from pathlib import Path
import fitz,json,difflib
r=Path('rag-knowledge/paper_demo');v=r/'review/submission-revision-20260919';o=v/'layout-check';p=o/'final-metadata-refresh.json';j=json.loads(p.read_text());d=fitz.open(r/'tex/main.pdf');old=json.loads((o/'machine-check.json').read_text())
j['span_geometry_and_text_equal_except_date']=[]
for n,page in enumerate(d):
 spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
 before=old['pages'][n]['spans']; changes=[]
 for k,(a,b) in enumerate(zip(before,spans)):
  if a!=b:changes.append({'old_text':a['text'],'new_text':b['text'],'old_bbox':a['bbox'],'new_bbox':b['bbox']})
 j['span_geometry_and_text_equal_except_date'].append({'page':n+1,'span_count_equal':len(before)==len(spans),'changes':changes})
j['source_diff']=list(difflib.unified_diff((o/'isolated/tex/main.tex').read_text().splitlines(),(r/'tex/main.tex').read_text().splitlines()))
p.write_text(json.dumps(j,indent=2),encoding='utf-8');print(json.dumps(j['span_geometry_and_text_equal_except_date'],indent=2));print('\n'.join(j['source_diff']))
