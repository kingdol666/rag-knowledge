"""Re-source build_fig3_dual.py to the fresh monitored run (2026-09-30).

Panels re-derived from run-20260930T150453Z-3ec2174 traces; every quote is a
normalized substring of the saved answers (builder asserts this), and every
timeline line's xN exactly partitions the trace's tool_use events.
"""
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "paper_demo" / "figures" / "submission-20260920" / "build_fig3_dual.py"
s = P.read_text(encoding="utf-8")

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, f"anchor x{s.count(old)} (want {n}): {old[:80]!r}"
    s = s.replace(old, new)

# 1. run path
rep("RUN = ROOT / 'benchmark-suite' / 'results' / 'experiment_chat_20260922-211000'",
    "RUN = (ROOT / 'benchmark-suite' / 'results' / 'runs' /\n"
    "       'run-20260930T150453Z-3ec2174')\n"
    "TRACK_OF = {'a': 'a2', 'b': 'b', 'c': 'c'}  # platform arm file prefix")

# 2. panel 1 quotes
rep("""        'a': [
            '1. Molecular Function (MF) 2. Biological Process (BP) 3. Cellular Component (CC)',
            'The Gene Ontology is a controlled vocabulary of terms to represent biology in a structured way.',
        ],
        'b': [
            'Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).',
        ],
        'c': [
            'the GO is "a controlled vocabulary of terms to represent biology in a structured way,"',
        ],""",
    """        'a': [
            'Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).',
            'These share a common space of identifiers and a well-specified syntax.',
        ],
        'b': [
            "the Gene Ontology's terms are subdivided into three distinct, "
            'non-redundant ontologies representing different biological '
            'aspects: Molecular Function (MF), Biological Process (BP), and '
            'Cellular Component (CC).',
        ],
        'c': [
            "the Gene Ontology's terms are subdivided into three distinct "
            'ontologies representing different biological aspects: Molecular '
            'Function (MF), Biological Process (BP), and Cellular Component (CC).',
        ],""")

# 3. panel 1 process
rep("""        'a': ['ToolSearch ×2 · link kb-mcp',
              'kb_search_vector ×2 — top 0.75',
              'kb_search_two_stage ×1 — confirm'],
        'b': ['Glob ×1 — 100 exported papers',
              'Grep ×1 — targeted search',
              'Read ×2 — the paper file'],
        'c': ['ToolSearch ×1 · link kb-mcp',
              'kb_search_vector ×1 — chunk recall'],""",
    """        'a': ['Agent ×1 — subagent probe',
              'kb_search_vector ×1 — recall',
              'kb_search ×1 — cross-check',
              'kb_doc_read ×2 — chunk + part'],
        'b': ['Glob ×1 — file list',
              'Grep ×2 — locate the primer',
              'Read ×1 — the paper file'],
        'c': ['EndConversation ×1 — harness call',
              'kb_search_vector ×1 — chunk recall'],""")

# 4. panel 1 sources
rep("""        'a': ['Sources: life-sciences base · 1602.01876',
              'part 1 of 2 · §2 verbatim quote'],
        'b': ['Source: …1602.01876__primer-',
              'on-the-gene-ontology.md (§2)'],
        'c': ['Chunks: …gene-ontology__k00.md',
              '(Corpus-Chunks800 index)'],""",
    """        'a': ['Sources: life-sciences base · 1602.01876',
              'part 1 of 2 · §2 verbatim quote'],
        'b': ['Source: …1602.01876__primer-',
              'on-the-gene-ontology.md'],
        'c': ['Source: chunk copy …primer-',
              'on-the-gene-ontology__k00.md'],""")

# 5. panel 2 quotes
rep("""        'a': [
            'The temperature of the climate (mean surface temperature) is the primary physical factor',
            'roughly, whether the mean surface temperature is above or below ~295 K',
        ],
        'c': [
            'The retrieved chunks do not directly name a single physical factor as the primary control.',
        ],""",
    """        'a': [
            'if changes in dynamics and precipitation efficiency are '
            'negligible, precipitation extremes increase with warming '
            'because of increases in the saturation vapor pressure of water',
            'the thermodynamic contribution is robust and well understood',
        ],
        'c': [
            'The evidence points to the thermodynamic contribution',
            'the retrieved text does not say one factor',
        ],""")

# 6. panel 2 process
rep("""        'a': ['ToolSearch ×3 · link kb-mcp',
              'kb_search_vector ×5 — recall',
              'kb_doc_read ×2 — verify re-read'],
        'c': ['ToolSearch ×1 · link kb-mcp',
              'kb_search_vector ×1 — chunk recall'],""",
    """        'a': ['kb_search_vector ×4 — widen, then pin',
              'kb_list ×1 — shelf check',
              'kb_laya_judge ×1 — segment grading',
              'EndConversation ×1 — harness call'],
        'c': ['Agent ×1 — subagent probe',
              'kb_search_vector ×5 — chunk recall'],""")

# 7. panel 2 sources + verdicts
rep("""        'a': ['Sources: climate-science base · 1503.07557',
              'keyword-verified ✓ (precipitation efficiency)'],
        'c': ['Closest chunk: …1503.07557__k00.md',
              '"Several physical contributions govern…" — no single factor'],
    },
    'verdicts': {
        'a': 'grounded ✓ · keyword-verified answer',
        'c': 'MEASURED ABSTENTION — insufficient retrieved evidence',
    },""",
    """        'a': ['Sources: climate base · 1503.07557 (O\\u2019Gorman 2015)',
              'keyword-verified ✓ · engine-graded reading'],
        'c': ['Chunks: …1503.07557__k*.md (Chunks800)',
              'same factor, chunk recall, no grading step'],
    },
    'verdicts': {
        'a': 'grounded ✓ · graded reading · keyword-verified',
        'c': 'grounded ✓ · chunk recall, ungraded',
    },""")

# 8. load_track + metrics strip: map display track -> file prefix
rep("""def load_track(trk: str, qid: str) -> dict:
    d = json.loads((RUN / f'track_{trk}_{qid}.json').read_text(encoding='utf-8'))""",
    """def load_track(trk: str, qid: str) -> dict:
    d = json.loads((RUN / f'track_{TRACK_OF[trk]}_{qid}.json').read_text(encoding='utf-8'))""")

rep("""    gr = grade['grades']
    rows = [
        ('Grounded* (cites designated paper)', [str(gr[t]['gold_hit']) + '/10' for t in 'abc']),
        ('Keyword-verified (>=60% gold key facts)', [str(gr[t]['kw_ok']) + '/10' for t in 'abc']),""",
    """    gr = grade['grades']
    rows = [
        ('Grounded* (cites designated paper)', [str(gr[TRACK_OF[t]]['gold_hit']) + '/10' for t in 'abc']),
        ('Keyword-verified (>=60% gold key facts)', [str(gr[TRACK_OF[t]]['kw_ok']) + '/10' for t in 'abc']),""")

rep("""    cites = {}
    for t in 'abc':
        n = 0
        for f in sorted(RUN.glob(f'track_{t}_*.json')):
            d = json.loads(f.read_text(encoding='utf-8'))
            blob = str(d.get('answer') or '') + '\\n' + '\\n'.join(d.get('texts_full') or [])
            if pat.search(blob):
                n += 1
        cites[t] = n""",
    """    cites = {}
    for t in 'abc':
        n = 0
        for f in sorted(RUN.glob(f'track_{TRACK_OF[t]}_*.json')):
            d = json.loads(f.read_text(encoding='utf-8'))
            blob = str(d.get('answer') or '')
            if pat.search(blob):
                n += 1
        cites[t] = n""")

rep("""    assert rows[0][1] == ['9/10', '10/10', '9/10'], rows[0]
    assert rows[1][1] == ['9/10', '6/10', '6/10'], rows[1]
    assert rows[2][1] == ['7/10', '4/10', '1/10'], rows[2]
    for t in 'abc':
        assert gr[t]['avg_latency_s'] == aud['per_track'][t]['avg_latency_s']
        assert abs(gr[t]['avg_cost_usd'] - aud['per_track'][t]['cost_usd_total'] / 10) < 0.001""",
    """    assert rows[0][1] == ['10/10', '10/10', '8/10'], rows[0]
    assert rows[1][1] == ['10/10', '8/10', '6/10'], rows[1]
    assert rows[2][1] == ['9/10', '6/10', '1/10'], rows[2]
    for t in 'abc':
        assert gr[TRACK_OF[t]]['avg_latency_s'] == aud['per_track'][TRACK_OF[t]]['avg_latency_s']
        assert abs(gr[TRACK_OF[t]]['avg_cost_usd'] - aud['per_track'][TRACK_OF[t]]['cost_usd_total'] / 10) < 0.001""")

rep("report = {'source': f'{RUN.name} traces (BQ04 a/b/c + BQ06 a/c)',",
    "report = {'source': f'{RUN.name} traces (BQ04 a2/b/c + BQ06 a2/c)',")

P.write_text(s, encoding="utf-8")
print("fig3 builder re-sourced")
