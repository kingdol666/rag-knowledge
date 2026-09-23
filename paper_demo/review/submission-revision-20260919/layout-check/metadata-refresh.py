from pathlib import Path
import fitz,hashlib,json,re,datetime
r=Path('rag-knowledge/paper_demo'); review=r/'review/submission-revision-20260919'; o=review/'layout-check'; p=r/'tex/main.pdf'; d=fitz.open(p); old=json.loads((o/'machine-check.json').read_text()); text=[x.get_text() for x in d]
result={'checked_at':datetime.datetime.now().isoformat(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'pages':len(d),'geometry':[list(x.rect) for x in d],'links':[[l.get('uri') for l in x.get_links() if l.get('uri')] for x in d],'date_lines':[[l for l in t.splitlines() if 'November' in l] for t in text],'page4_tail':text[3][-2400:],'page5_text':text[4],'changed_frozen_inputs':[]}
for name,h in old['frozen_hashes'].items():
 if hashlib.sha256((r/name).read_bytes()).hexdigest()!=h:result['changed_frozen_inputs'].append(name)
log=(r/'tex/main.log').read_text(); result['log_messages']=[l for l in log.splitlines() if re.search(r'Overfull|Underfull|Warning|undefined|Output written',l)];result['metadata_source']=[l for l in (r/'tex/main.tex').read_text().splitlines() if 'acmConference' in l or 'acmBooktitle' in l]
result['expected_hash_match']=result['sha256']=='05309a06454887a461a75245c57342f4df567f62ea0c15dbf4ed9943f3516182'
result['source_hashes']={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in old['frozen_hashes']}
(o/'final-metadata-refresh.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({k:v for k,v in result.items() if k not in ['source_hashes']},indent=2))
