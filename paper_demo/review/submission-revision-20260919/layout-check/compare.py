import fitz,pathlib,json,re,hashlib
r=pathlib.Path('rag-knowledge/paper_demo'); o=r/'review/submission-revision-20260919/layout-check'; m=json.loads((o/'machine-check.json').read_text()); a=fitz.open(r/'tex/main.pdf'); b=fitz.open(o/'isolated/tex/main.pdf')
print('Fresh rebuild pixels', [a[i].get_pixmap().samples==b[i].get_pixmap().samples for i in range(5)])
for i,p in enumerate(a):
 print('PAGE',i+1,'XOBJECTS',p.get_xobjects())
for f in m['figures']: print(f['name'],f['size'],f['min_native_font'])
print('LINKS',[(p['page'],p['links']) for p in m['pages']])
log=(o/'isolated/tex/main.log').read_text(); print('\n'.join(l for l in log.splitlines() if any(x in l for x in ['Overfull','Underfull','Warning','undefined','h-part','v-part','textwidth','textheight','columnsep'])))
print('FONT',[(f['name'],f['bytes']) for f in m['fonts']])
print('SOURCE OVERRIDES')
for f in (r/'tex').glob('*.tex'):
 for n,l in enumerate(f.read_text(encoding='utf-8').splitlines(),1):
  if re.search(r'geometry|fontsize|textwidth|textheight|vspace|hspace|baselinestretch|small|tiny|balance|TBD|TODO|placeholder|example\.com|secret|token|api.key',l,re.I):print(f.name,n,l)
print('UNCHANGED',all(hashlib.sha256((r/f).read_bytes()).hexdigest()==h for f,h in m['frozen_hashes'].items()))
