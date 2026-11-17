"""Recalculate reported follow-up containment and costs from preserved records."""
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / 'paper-kbs/tex/journal_20p/supp_traces_followup.csv'
CAPTURE = ROOT / 'review/experiment-redesign-20261101/artifacts/replication_bench_20261112/s4_responses_031646.json'
ARMS = ('A0', 'A0f', 'A0h', 'PD', 'A1b', 'A2')
EXPECTED = {'A0': 39, 'A0f': 44, 'A0h': 51, 'PD': 45, 'A1b': 39, 'A2': 25}
with CSV.open(encoding='utf-8', newline='') as f:
    rows = list(csv.DictReader(f))
raw = json.loads(CAPTURE.read_text(encoding='utf-8'))
by_arm = {}
for arm in ARMS:
    items = [r for r in rows if r['arm'] == arm and r['qid'] not in ('R1', 'R2', 'R3', 'R4')]
    assert len(items) == 72 and len({r['qid'] for r in items}) == 72, arm
    assert all(r['gold_hit'] in ('True', 'False') for r in items), arm
    by_arm[arm] = {r['qid']: r for r in items}
    hits = sum(r['gold_hit'] == 'True' for r in items)
    assert hits == EXPECTED[arm], (arm, hits)
    seconds = [float(r['tool_seconds']) for r in items]
    kb = statistics.mean(float(r['bytes_ingested']) for r in items) / 1000
    checked = 0
    if arm in raw:
        for row in items:
            c = raw[arm][row['qid']]
            ev = c.get('gold_evidence') or ''
            assert ev and (ev in (c.get('response_text') or '')) == (row['gold_hit'] == 'True'), (arm, row['qid'])
            checked += 1
    print(f'{arm}: {hits}/72, {kb:.2f} KB/q, time mean={statistics.mean(seconds):.2f} s, median={statistics.median(seconds):.1f} s, max={max(seconds):.1f} s, original evidence checks={checked}')
for other in ('A0', 'A0f', 'PD'):
    a, b = by_arm['A0h'], by_arm[other]
    assert set(a) == set(b)
    x = sum(a[q]['gold_hit'] == 'True' and b[q]['gold_hit'] == 'False' for q in a)
    y = sum(a[q]['gold_hit'] == 'False' and b[q]['gold_hit'] == 'True' for q in a)
    n = x + y
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / (2 ** n)) if n else 1.0
    print(f'A0h vs {other}: A0h-only={x}, other-only={y}, exact McNemar p={p:.6f} (unadjusted)')
print('PASS: captured response_text denotes retrieved evidence, not generated answers; A1b/A2 have no capture in this file.')
