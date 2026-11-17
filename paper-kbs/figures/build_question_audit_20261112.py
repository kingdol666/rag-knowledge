"""Export non-text per-question audit records for the frozen and later runs."""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
folder = root / 'review/experiment-redesign-20261101/artifacts/final_bench'
frozen = json.loads((folder/'s4_traces_final.json').read_text(encoding='utf-8'))
later = json.loads((root/'paper-kbs/figures/fig_ladder_20261112_snapshot.json').read_text(encoding='utf-8'))
attribution = json.loads((folder/'attribution_a0_misses.json').read_text(encoding='utf-8'))
def records(source, arm):
    return {r['qid']: r for r in source[arm] if not r['is_refusal']}
base={a:records(frozen,a) for a in ['A0','A0f','A0h','PD','A3']}
rep=records(later,'A3')
assert all(v.keys()==base['A0'].keys() for v in base.values())
assert rep.keys()==base['A0'].keys()
classes={r['qid']:r['cls'] for r in attribution['rows']}
misses=[q for q,r in base['A0'].items() if not r['gold_hit']]
assert len(misses)==35 and set(misses)==set(classes)
out=Path(__file__).with_name('experiment_question_audit_20261112.csv')
with out.open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f)
    w.writerow(['qid','a0_hit','a0f_hit','a0h_hit','pd_hit','first_match_heuristic_label',
                'a3_frozen_hit','a3_followup_hit'])
    for q in sorted(base['A0']):
        w.writerow([q,*[int(bool(base[a][q]['gold_hit'])) for a in ['A0','A0f','A0h','PD']],
                    classes.get(q,''), int(bool(base['A3'][q]['gold_hit'])),int(bool(rep[q]['gold_hit']))])
flips=[q for q in rep if bool(rep[q]['gold_hit']) != bool(base['A3'][q]['gold_hit'])]
assert len(flips)==18
print(f'{out}: 72 question IDs; {len(misses)} A0 misses; {len(flips)} A3 status flips')
