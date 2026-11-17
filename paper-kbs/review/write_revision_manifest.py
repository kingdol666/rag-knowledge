"""Record current artefact hashes; the old freeze remains a historical record."""
from pathlib import Path
import hashlib

base = Path(__file__).resolve().parents[1]
src = base / 'tex' / 'journal_20p'
root = base.parent
paths = [*sorted(src.glob('n*.tex')), src / 'main_20p.tex', src / 'supplementary.tex', src / 'supplementary-arm-tables.tex',
         src / 'refs.bib', src / 'refs_new_verified.bib', src / 'hmrs_kbs.pdf', src / 'supplementary.pdf',
         src / 'supplementary-inventory.pdf', base / 'supplementary/supplementary-material.md',
         *[src / 'figs' / (n + '.pdf') for n in ('fig_management_model','fig1_architecture_native',
           'fig2_workflow_native','fig3_routing','fig_ladder_optimization','fig_retrieval_comparison','fig4_inflation','fig_miss_overlap')],
         *[base / 'figures' / n for n in ('fig_ladder_20261112_snapshot.json','build_fig3_origin.py',
           'build_fig_ladder_optimization.py','build_fig_retrieval_comparison.py','build_fig_miss_overlap.py',
           'build_experiment_tables_20261112.py','fig_miss_overlap_data.csv','experiment_arm_summary_20261112.csv',
           'build_question_audit_20261112.py','experiment_question_audit_20261112.csv')],
         *[root / 'review/experiment-redesign-20261101/artifacts/final_bench' / n for n in ('s4_traces_final.json','s6_stats.json')],
         root / 'review/experiment-redesign-20261101/scripts/s4_run_ablation.py',
         root / 'benchmark-suite/data/papers/qa_questions_e5_corrected.json',
         root / 'benchmark-suite/data/papers/qa_questions.json',
         root / 'benchmark-suite/scripts/107_exp_grade.py']
lines=[]
import os
for path in paths:
    if not path.is_file(): raise SystemExit(f'Missing: {path}')
    rel=os.path.relpath(path,src).replace('\\','/')
    lines.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}')
out=src / 'revision-20261112.sha256'
out.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
print(f'{out}: {len(lines)} hashes')
