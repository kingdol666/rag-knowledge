import fitz,pathlib,json,re,hashlib
r=pathlib.Path('rag-knowledge/paper_demo');o=r/'review/submission-revision-20260919/layout-check';d=fitz.open(r/'tex/main.pdf');m=json.loads((o/'machine-check.json').read_text())
res={}
for i,f in enumerate(sorted((r/'figures/submission-20260919').glob('*.pdf')),1):
 s=fitz.open(f); x=d[i].get_xobjects()[0][0]; embedded=d.xref_stream(x); raw=b''.join(s.xref_stream(c) for c in s[0].get_contents());res[f.name]={'embedded_stream_matches_source':embedded==raw,'min_final_font_pdf_pt':round(m['figures'][i-1]['min_native_font']*506.295/1.00375/750,4)}
p=d[4]; spans=m['pages'][4]['spans'];body=[s for s in spans if 80<s['bbox'][1]<700];res['page5_text_bottom_pdf_pt']=max(s['bbox'][3] for s in body);res['page5_columns_bottom']=[max(s['bbox'][3] for s in body if (s['bbox'][0]<310)==left) for left in [True,False]]
res['frozen_files_unchanged']=all(hashlib.sha256((r/f).read_bytes()).hexdigest()==h for f,h in m['frozen_hashes'].items())
res['pixel_equivalent_fresh_build']=[d[i].get_pixmap().samples==fitz.open(o/'isolated/tex/main.pdf')[i].get_pixmap().samples for i in range(5)]
res['body_font_evidence']=[s for s in m['pages'][0]['spans'] if s['text'].startswith('Research administrators')]
(o/'comparison-results.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
