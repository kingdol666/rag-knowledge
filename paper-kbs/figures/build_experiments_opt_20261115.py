#!/usr/bin/env python3
"""Build the four HMRS evaluation figures for journal_opt_20261115.

All values are read from archived records and asserted before plotting:
  - frozen 72-question traces + s6 statistics
  - same-question follow-up traces (R3)
  - original and common-substrate 30-cell answer grades
  - 191 logged verifier scores and the 16-pool ordering archive

The figures use one Origin-style visual system: Arial, inward ticks on a closed
frame, light horizontal grids, colour-blind-safe navy/steel/ochre/brick/slate,
filled/open markers, and vector PDF output with embedded fonts. Origin itself is
not used; the PDFs are Matplotlib output.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from math import comb
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / 'paper-kbs/tex/journal_opt_20261115/figs'
DATA = ROOT / 'paper-kbs/figures/experiment_opt_20261115_data'
FROZEN = ROOT / 'review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json'
FROZEN_STATS = ROOT / 'review/experiment-redesign-20261101/artifacts/final_bench/s6_stats.json'
R3 = ROOT / 'review/experiment-redesign-20261101/artifacts/replication_bench_20261112/s4_traces_r3.json'
R3_STATS = ROOT / 'review/experiment-redesign-20261101/artifacts/replication_bench_20261112/s6_stats.json'
ORIG_GRADE = ROOT / 'benchmark-suite/results/exp_r2_grade_corrected.json'
REP_GRADE = ROOT / 'benchmark-suite/results/exp_rerun5_grade.json'
SCORES = ROOT / 'paper-kbs/experiments/results/exp1_retrieval.json'
ORDER = ROOT / 'paper-kbs/experiments/results/exp5_judge_filter.json'
FRESH = ROOT / 'review/_exp_rerun_20261114/answers_fresh_summary.json'
DESC_AUDIT = ROOT / 'review/_exp_rerun_20261114/desc_audit.json'
PROBE = ROOT / 'review/_exp_rerun_20261114/probe5_final.json'

# Palette: semantic roles stay fixed across every figure.
INK = '#23394F'
STEEL = '#35689A'
LSTEEL = '#8FB3C9'
MSTEEL = '#5B8DB3'
OCHRE = '#C58A2E'
LOCHRE = '#D9A45B'
BRICK = '#A9542F'
LBRICK = '#C9775A'
SLATE = '#8D98A4'
GRID = '#E3E8ED'
FILL = '#EDF2F6'
WHITE = '#FFFFFF'

ARM_COLOR = {
    'A0': LSTEEL, 'A0f': MSTEEL, 'A0h': STEEL,
    'PD': OCHRE, 'A1b': LOCHRE,
    'A2': BRICK, 'A3': LBRICK, 'A1-readall': SLATE,
}
ARM_LABEL = {
    'A0': 'A0', 'A0f': 'A0f', 'A0h': 'A0h', 'PD': 'PD',
    'A1b': 'A1b', 'A2': 'A2', 'A3': 'A3', 'A1-readall': 'Read-all',
}
TRACK = {'P': ('a2', STEEL), 'F': ('b', OCHRE), 'C': ('c', BRICK)}
ARM_ORDER = ['A0h', 'PD', 'A0f', 'A1b', 'A0', 'A3', 'A2']
FROZEN_COUNTS = {'A0': 37, 'A0f': 45, 'A0h': 52, 'PD': 46,
                 'A1b': 39, 'A2': 25, 'A3': 33, 'A1-readall': 72}
R3_COUNTS = {'A0': 39, 'A0f': 44, 'A0h': 51, 'PD': 45,
             'A1b': 39, 'A2': 25, 'A3': 25, 'A1-readall': 3}

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
    'font.size': 8.3, 'axes.labelsize': 8.5,
    'xtick.labelsize': 8.0, 'ytick.labelsize': 8.0, 'legend.fontsize': 8.0,
    'axes.linewidth': 0.8, 'axes.edgecolor': INK, 'text.color': INK,
    'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.major.width': 0.8, 'ytick.major.width': 0.8,
    'xtick.minor.width': 0.6, 'ytick.minor.width': 0.6,
    'pdf.fonttype': 42, 'ps.fonttype': 42,
    'savefig.facecolor': WHITE, 'figure.facecolor': WHITE,
    'axes.facecolor': WHITE, 'savefig.dpi': 300,
})


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(traces: dict, arm: str):
    selected = [r for r in traces[arm] if not r.get('is_refusal', False)]
    assert len(selected) == 72 and len({r['qid'] for r in selected}) == 72, arm
    return selected


def hits(selected, field: str = 'gold_hit') -> int:
    return sum(bool(r.get(field)) for r in selected)


def wilson(k: int, n: int, z: float = 1.959963984540054):
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar(a, b, field: str):
    a_by = {r['qid']: bool(r.get(field)) for r in a}
    b_by = {r['qid']: bool(r.get(field)) for r in b}
    assert a_by.keys() == b_by.keys()
    a_only = sum(a_by[q] and not b_by[q] for q in a_by)
    b_only = sum(b_by[q] and not a_by[q] for q in a_by)
    both = sum(a_by[q] and b_by[q] for q in a_by)
    neither = len(a_by) - a_only - b_only - both
    discordant = a_only + b_only
    tail = sum(comb(discordant, k) for k in range(min(a_only, b_only) + 1))
    p = min(1.0, 2 * tail / (2 ** discordant)) if discordant else 1.0
    return a_only, b_only, both, neither, p


def decorate(ax, grid_axis: str = 'y'):
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color(INK)
    ax.tick_params(axis='both', direction='in', length=3.0, width=0.8,
                   top=True, right=True, pad=3)
    ax.tick_params(which='minor', direction='in', length=1.6, width=0.6,
                   top=True, right=True)
    ax.set_axisbelow(True)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.5)


def panel(ax, label: str, x: float = 0.015, y: float = 0.985):
    ax.text(x, y, label, transform=ax.transAxes, fontsize=9.5,
            fontweight='bold', color=INK, ha='left', va='top')


def save(fig, name: str):
    FIG.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f'{name}.pdf', format='pdf', facecolor=WHITE)
    fig.savefig(FIG / f'{name}.png', dpi=300, facecolor=WHITE)
    plt.close(fig)


def csv_write(name: str, rows_: list[dict], fields: list[str]):
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_)


def route_figure(frozen, r3):
    a0 = rows(frozen, 'A0')
    a3 = rows(frozen, 'A3')
    ra = rows(frozen, 'A1-readall')
    assert hits(a0, 'route_correct') == 72 and hits(a3, 'route_correct') == 37
    assert hits(a0) == 37 and hits(a3) == 33 and hits(ra) == 72
    counts = {'A0': 37, 'A3': 33, 'A1-readall': 72}
    records = []

    fig = plt.figure(figsize=(7.15, 2.80))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.92, 1.02, 1.18],
                          left=0.075, right=0.985, top=0.86, bottom=0.19,
                          wspace=0.36)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    # (a) Gold-domain route selection.
    for i, (arm, label) in enumerate([('A0', 'A0'), ('A3', 'A3')]):
        data = a0 if arm == 'A0' else a3
        k = hits(data, 'route_correct')
        lo, hi = wilson(k, 72)
        y = 1 - i
        c = ARM_COLOR[arm]
        ax1.errorbar(k / 72 * 100, y,
                     xerr=[[(k / 72 - lo) * 100], [(hi - k / 72) * 100]],
                     fmt='o', ms=5.6, mfc=c, mec=c, ecolor=INK,
                     elinewidth=0.9, capsize=2.6, capthick=0.9,
                     linestyle='none', zorder=3)
        ax1.annotate(f'{k}/72', (k / 72 * 100, y), xytext=(0, 7),
                     textcoords='offset points', ha='center', va='bottom',
                     fontsize=8.0, color=INK)
        ax1.set_yticks([0, 1], ['A3', 'A0'])
        records.append({'panel': 'a', 'arm': arm, 'n': 72, 'hits': k,
                        'percent': k / 72 * 100, 'wilson_low': lo * 100,
                        'wilson_high': hi * 100})
    ax1.set_xlim(0, 115)
    ax1.set_xticks([0, 25, 50, 75, 100])
    ax1.set_xlabel('Gold-domain selection (%)')
    ax1.set_ylim(-0.65, 1.65)
    decorate(ax1, 'x')
    panel(ax1, '(a)')

    # (b) Gold-string containment.
    for i, arm in enumerate(['A0', 'A3', 'A1-readall']):
        data = {'A0': a0, 'A3': a3, 'A1-readall': ra}[arm]
        k = hits(data)
        lo, hi = wilson(k, 72)
        y = 2 - i
        c = ARM_COLOR[arm]
        ax2.errorbar(k / 72 * 100, y,
                     xerr=[[(k / 72 - lo) * 100], [(hi - k / 72) * 100]],
                     fmt='o', ms=5.6, mfc=c, mec=c, ecolor=INK,
                     elinewidth=0.9, capsize=2.6, capthick=0.9,
                     linestyle='none', zorder=3)
        ax2.annotate(f'{k}/72', (k / 72 * 100, y), xytext=(0, 7),
                     textcoords='offset points', ha='center', va='bottom',
                     fontsize=8.0, color=INK)
        records.append({'panel': 'b', 'arm': arm, 'n': 72, 'hits': k,
                        'percent': k / 72 * 100, 'wilson_low': lo * 100,
                        'wilson_high': hi * 100})
    ax2.set_yticks([0, 1, 2], ['A1\n(read-all)', 'A3', 'A0'])
    ax2.set_xlim(0, 115)
    ax2.set_xticks([0, 25, 50, 75, 100])
    ax2.set_xlabel('Gold-string containment (%)')
    ax2.set_ylim(-0.65, 2.65)
    decorate(ax2, 'x')
    panel(ax2, '(b)')

    # (c) Recorded text per question vs containment.
    means = {}
    for arm in FROZEN_COUNTS:
        data = rows(frozen, arm)
        means[arm] = float(np.mean([float(r['bytes_ingested']) for r in data])) / 1_000_000
    assert round(means['A0h'], 3) == 0.309 and round(means['A1-readall'], 1) == 24.3
    offsets = {
        'A0h': (7, 6), 'PD': (7, -4), 'A0f': (-7, 9), 'A1b': (7, 6),
        'A0': (7, -10), 'A3': (7, 5), 'A2': (7, 0), 'A1-readall': (-8, -14),
    }
    for arm in FROZEN_COUNTS:
        k = FROZEN_COUNTS[arm]
        x, y = means[arm], k / 72 * 100
        c = ARM_COLOR[arm]
        marker = 'o' if arm != 'A1-readall' else 'D'
        ax3.scatter(x, y, s=38, marker=marker, facecolor=c, edgecolor=INK,
                    linewidth=0.7, zorder=3)
        dx, dy = offsets[arm]
        ha = 'right' if dx < 0 else 'left'
        ax3.annotate(ARM_LABEL[arm], (x, y), xytext=(dx, dy),
                     textcoords='offset points', ha=ha,
                     va='center', fontsize=8.0, color=INK)
        records.append({'panel': 'c', 'arm': arm, 'n': 72, 'hits': k,
                        'percent': y, 'mean_mb': x})
    ax3.set_xscale('log')
    ax3.set_xlim(0.001, 80)
    ax3.set_xticks([0.001, 0.01, 0.1, 1, 10])
    ax3.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
    ax3.xaxis.set_minor_locator(NullLocator())
    ax3.set_ylim(0, 108)
    ax3.set_yticks([0, 25, 50, 75, 100])
    ax3.set_xlabel('Recorded text (MB/question, log)', fontsize=8.0)
    ax3.set_ylabel('Gold-string containment (%)')
    decorate(ax3, 'y')
    panel(ax3, '(c)')
    ax3.text(0.98, 0.04, 'read-all: mechanical\nstring scan, 24.3 MB',
             transform=ax3.transAxes, ha='right', va='bottom',
             fontsize=7.6, color=SLATE)

    csv_write('route_summary.csv', records,
              ['panel', 'arm', 'n', 'hits', 'percent', 'wilson_low',
               'wilson_high', 'mean_mb'])
    pairs = []
    for label, a, b, field in [
        ('A0 vs A3 route', a0, a3, 'route_correct'),
        ('A0 vs A3 pack', a0, a3, 'gold_hit'),
        ('read-all vs A0 pack', ra, a0, 'gold_hit'),
    ]:
        a_only, b_only, both, neither, p = mcnemar(a, b, field)
        pairs.append({'contrast': label, 'first_only': a_only,
                      'second_only': b_only, 'both': both, 'neither': neither,
                      'mcnemar_p': f'{p:.12g}'})
    csv_write('route_pairs.csv', pairs,
              ['contrast', 'first_only', 'second_only', 'both', 'neither',
               'mcnemar_p'])
    save(fig, 'fig_opt_route')


def content_figure(frozen, r3):
    frozen_rows = {arm: rows(frozen, arm) for arm in FROZEN_COUNTS}
    r3_rows = {arm: rows(r3, arm) for arm in FROZEN_COUNTS
               if arm != 'A1-readall'}
    assert {a: hits(r) for a, r in frozen_rows.items()} == FROZEN_COUNTS
    assert {a: hits(r) for a, r in r3_rows.items()} == {
        a: k for a, k in R3_COUNTS.items() if a != 'A1-readall'}
    assert hits(r3_rows['A3'], 'route_correct') == 49
    records = []

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(7.15, 3.20), gridspec_kw={'width_ratios': [1.12, 1.0]})
    fig.subplots_adjust(left=0.105, right=0.985, top=0.87, bottom=0.16,
                        wspace=0.42)

    # (a) Arm ranking: frozen filled circle + follow-up open triangle.
    ypos = {arm: i for i, arm in enumerate(reversed(ARM_ORDER))}
    ypos['A1-readall'] = 7
    ax.axhspan(ypos['A0h'] - 0.42, ypos['A0h'] + 0.42,
               color=FILL, zorder=0)
    base = hits(frozen_rows['A0']) / 72 * 100
    ax.axvline(base, color=SLATE, linewidth=0.8, linestyle=(0, (4, 3)),
               zorder=1)
    for arm in FROZEN_COUNTS:
        y = ypos[arm]
        k = FROZEN_COUNTS[arm]
        lo, hi = wilson(k, 72)
        c = ARM_COLOR[arm]
        ax.errorbar(k / 72 * 100, y - 0.13,
                    xerr=[[(k / 72 - lo) * 100], [(hi - k / 72) * 100]],
                    fmt='o', ms=5.4, mfc=c, mec=INK, ecolor=c,
                    elinewidth=0.9, capsize=2.4, capthick=0.8,
                    linestyle='none', zorder=3)
        k2 = R3_COUNTS[arm] if arm != 'A1-readall' else None
        count_text = f'{k} / –' if k2 is None else f'{k} / {k2}'
        ax.text(103, y, count_text, fontsize=7.6, color=INK,
                va='center', ha='center')
        records.append({'panel': 'a', 'arm': arm, 'run': 'frozen', 'n': 72,
                        'hits': k, 'percent': k / 72 * 100,
                        'wilson_low': lo * 100, 'wilson_high': hi * 100})
        if arm == 'A1-readall':
            continue
        c2 = OCHRE
        ax.scatter(k2 / 72 * 100, y + 0.13, s=27, marker='^',
                   facecolor=WHITE, edgecolor=c2, linewidth=0.9, zorder=4)
        records.append({'panel': 'a', 'arm': arm, 'run': 'follow-up', 'n': 72,
                        'hits': k2, 'percent': k2 / 72 * 100,
                        'wilson_low': '', 'wilson_high': ''})
    labels = ['A2', 'A3', 'A0', 'A1b', 'A0f', 'PD', 'A0h', 'Read-all']
    ax.set_yticks(range(8), labels)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel('Gold-string containment (%)')
    ax.set_ylim(-0.7, 7.7)
    decorate(ax, 'x')
    panel(ax, '(a)')
    ax.text(0.015, 0.02, 'frozen A0', transform=ax.transAxes, fontsize=7.5,
            color=SLATE, va='bottom')

    # (b) Paired discordance.  Each tuple is first-only / second-only / p.
    disc = []
    for label, a, b, field in [
        ('A0h vs A1b', 'A0h', 'A1b', 'gold_hit'),
        ('A0h vs PD', 'A0h', 'PD', 'gold_hit'),
        ('PD vs A1b', 'PD', 'A1b', 'gold_hit'),
        ('A0h vs A0', 'A0h', 'A0', 'gold_hit'),
        ('A0f vs A0', 'A0f', 'A0', 'gold_hit'),
        ('A2 vs A0', 'A2', 'A0', 'gold_hit'),
    ]:
        a_only, b_only, both, neither, p = mcnemar(
            frozen_rows[a], frozen_rows[b], field)
        disc.append((label, a_only, b_only, p))
    expected = [
        ('A0h vs A1b', 13, 0), ('A0h vs PD', 7, 1), ('PD vs A1b', 7, 0),
        ('A0h vs A0', 15, 0), ('A0f vs A0', 8, 0), ('A2 vs A0', 6, 18),
    ]
    assert [(x[0], x[1], x[2]) for x in disc] == expected
    yvals = list(range(len(disc)))[::-1]
    for y, (label, first, second, p) in zip(yvals, disc):
        ax_line = max(first, second)
        bx.hlines(y, 0, ax_line, color=GRID, linewidth=2.6, zorder=1)
        bx.scatter(first, y + 0.10, s=32, marker='o', facecolor=STEEL,
                   edgecolor=INK, linewidth=0.6, zorder=3)
        bx.scatter(second, y - 0.10, s=32, marker='^', facecolor=WHITE,
                   edgecolor=OCHRE, linewidth=0.9, zorder=3)
        bx.annotate(f'{first}', (first, y + 0.10), xytext=(4, 0),
                    textcoords='offset points', fontsize=7.6, color=STEEL,
                    va='center', ha='left')
        bx.annotate(f'{second}', (second, y - 0.10), xytext=(4, 0),
                    textcoords='offset points', fontsize=7.6, color=OCHRE,
                    va='center', ha='left')
        ptext = 'p<0.001' if p < 0.001 else f'p={p:.3g}'
        if p >= 0.01:
            ptext = f'p={p:.3f}'.rstrip('0').rstrip('.')
        bx.annotate(ptext, (27.5, y), fontsize=7.3, color=INK,
                    va='center', ha='right')
    bx.set_yticks(yvals, [d[0] for d in disc])
    bx.set_xlim(0, 28)
    bx.set_xticks([0, 5, 10, 15, 20])
    bx.set_xlabel('Discordant questions (n=72)')
    bx.set_ylim(-0.7, 5.7)
    decorate(bx, 'x')
    panel(bx, '(b)')
    bx.text(0.015, 0.02, 'first arm only  /  second arm only',
            transform=bx.transAxes, fontsize=7.4, color=INK, va='bottom')
    for d in disc:
        records.append({'panel': 'b', 'contrast': d[0], 'first_only': d[1],
                        'second_only': d[2], 'mcnemar_p': f'{d[3]:.12g}'})

    fig.legend(handles=[
        Line2D([0], [0], marker='o', color=STEEL, linestyle='none',
               markersize=5.2, label='Frozen (Wilson 95% CI)'),
        Line2D([0], [0], marker='^', markerfacecolor=WHITE,
               markeredgecolor=OCHRE, color=OCHRE, linestyle='none',
               markersize=5.6, label='Same-question follow-up'),
    ], loc='upper center', bbox_to_anchor=(0.5, 0.985), ncol=2,
        frameon=False, handletextpad=0.35, columnspacing=1.5)
    csv_write('content_summary.csv', records,
              ['panel', 'arm', 'run', 'n', 'hits', 'percent',
               'wilson_low', 'wilson_high', 'contrast', 'first_only',
               'second_only', 'mcnemar_p'])
    save(fig, 'fig_opt_content')


def answer_figure(orig, rep):
    qids = [f'BQ{i:02d}' for i in range(1, 11)]
    tracks = ['a2', 'b', 'c']
    colors = {'a2': STEEL, 'b': OCHRE, 'c': BRICK}
    labels = {'a2': 'P', 'b': 'F', 'c': 'C'}
    matrices = {}
    for source, name in [(orig, 'orig'), (rep, 'rep')]:
        for track in tracks:
            data = [r for r in source['rows'] if r['track'] == track]
            assert [r['qid'] for r in data] == qids
            matrices[(name, track)] = data
    for name, track, key, expected in [
        ('orig', 'a2', 'cited', 9), ('orig', 'b', 'cited', 7),
        ('orig', 'c', 'cited', 2),
        ('rep', 'a2', 'cited', 9), ('rep', 'b', 'cited', 9),
        ('rep', 'c', 'cited', 9),
        ('orig', 'a2', 'pass', 9), ('orig', 'b', 'pass', 9),
        ('orig', 'c', 'pass', 9),
        ('rep', 'a2', 'pass', 7), ('rep', 'b', 'pass', 7),
        ('rep', 'c', 'pass', 8),
        ('orig', 'a2', 'gold_hit', 10), ('orig', 'b', 'gold_hit', 10),
        ('orig', 'c', 'gold_hit', 10),
        ('rep', 'a2', 'gold_hit', 10), ('rep', 'b', 'gold_hit', 10),
        ('rep', 'c', 'gold_hit', 10),
        ('orig', 'a2', 'kw_alias_ok', 10), ('orig', 'b', 'kw_alias_ok', 10),
        ('orig', 'c', 'kw_alias_ok', 10),
        ('rep', 'a2', 'kw_alias_ok', 9), ('rep', 'b', 'kw_alias_ok', 9),
        ('rep', 'c', 'kw_alias_ok', 10),
    ]:
        assert sum(bool(r[key]) for r in matrices[(name, track)]) == expected, \
            (name, track, key)
    records = []
    for name, track in [(name, track) for name in ('orig', 'rep')
                        for track in tracks]:
        data = matrices[(name, track)]
        for r in data:
            records.append({'grid': name, 'arm': labels[track], 'qid': r['qid'],
                            'gold_hit': int(bool(r['gold_hit'])),
                            'strict': int(bool(r['pass'])),
                            'alias': int(bool(r['kw_alias_ok'])),
                            'marker': int(bool(r['cited']))})
    csv_write('answer_matrix.csv', records,
              ['grid', 'arm', 'qid', 'gold_hit', 'strict', 'alias', 'marker'])

    fig, axs = plt.subplots(1, 2, figsize=(7.15, 2.65), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.955, top=0.82, bottom=0.30,
                        wspace=0.16)
    for ax, name, title, subtitle in [
        (axs[0], 'orig', '(a) Original grid', 'different substrates'),
        (axs[1], 'rep', '(b) Common substrate', 'same five libraries'),
    ]:
        for j, track in enumerate(tracks):
            y = 2 - j
            c = colors[track]
            for i, r in enumerate(matrices[(name, track)]):
                hit = bool(r['cited'])
                ax.scatter(i, y, s=42, marker='s',
                           facecolor=c if hit else WHITE,
                           edgecolor=c, linewidth=0.9, zorder=3)
            k = sum(bool(r['cited']) for r in matrices[(name, track)])
            ax.annotate(f'{k}/10', (10.0, y), xytext=(0, 0),
                        textcoords='offset points', fontsize=8.4,
                        color=c, fontweight='bold', va='center', ha='left')
        ax.set_xlim(-0.6, 11.3)
        ax.set_ylim(2.6, -0.6)
        ax.set_xticks(range(10), qids)
        ax.set_yticks([2, 1, 0], ['P', 'F', 'C'])
        ax.tick_params(axis='x', labelsize=6.8, labelrotation=90)
        ax.tick_params(axis='y', labelsize=8.4)
        ax.set_xlabel('Question')
        decorate(ax, 'both')
        ax.text(0.015, 1.015, title, transform=ax.transAxes,
                fontsize=8.8, fontweight='bold', color=INK, va='bottom')
        ax.text(0.995, 1.015, subtitle, transform=ax.transAxes,
                fontsize=7.6, color=SLATE, va='bottom', ha='right')
        ax.text(0.995, 0.955, 'Gold-ID 10/10', transform=ax.transAxes,
                fontsize=7.2, color=INK, va='top', ha='right')
    fig.legend(handles=[
        Line2D([0], [0], marker='s', color=INK, markerfacecolor=STEEL,
               linestyle='none', markersize=5.8,
               label='Document-style marker present'),
        Line2D([0], [0], marker='s', color=INK, markerfacecolor=WHITE,
               linestyle='none', markersize=5.8,
               label='No marker'),
    ], loc='upper center', bbox_to_anchor=(0.5, 0.985), ncol=2,
        frameon=False, handletextpad=0.35, columnspacing=1.4)
    save(fig, 'fig_opt_answer')


def verifier_figure(scores, order):
    from kbcommon import QUESTIONS  # noqa: E402

    gold_doc = {q['qid']: q['gold_doc_substrings'] for q in QUESTIONS}
    records = []
    for row in scores['rows']:
        if row.get('method') not in ('qdcvr_hybrid', 'hmrs_hybrid'):
            continue
        if 'judge_scores' not in row:
            continue
        for path, value in row['judge_scores']['all'].items():
            gold = any(s.lower() in path.lower() for s in gold_doc[row['qid']])
            records.append({'qid': row['qid'], 'candidate': path,
                            'group': 'Gold' if gold else 'Non-gold',
                            'score': float(value)})
    gold = [r['score'] for r in records if r['group'] == 'Gold']
    non = [r['score'] for r in records if r['group'] == 'Non-gold']
    assert [len(gold), len(non)] == [17, 174]
    assert min(gold + non) > 0.5
    assert round(float(np.median(gold)), 2) == 0.88
    assert round(float(np.median(non)), 2) == 0.86
    assert len(order['rows']) == 16
    assert sum(bool(r['filter_only']['hit']) for r in order['rows']) == 15
    assert sum(bool(r['judged']['hit']) for r in order['rows']) == 7
    csv_write('verifier_scores.csv', records,
              ['qid', 'candidate', 'group', 'score'])

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(7.15, 2.55), gridspec_kw={'width_ratios': [1, 1.45]})
    fig.subplots_adjust(left=0.095, right=0.975, top=0.84, bottom=0.25,
                        wspace=0.48)
    rng = np.random.default_rng(523)
    for i, (values, colour, marker) in enumerate(
            [(gold, STEEL, 'o'), (non, SLATE, 's')]):
        jitter = rng.uniform(-0.16, 0.16, len(values)) + i
        ax.scatter(jitter, values, s=15, marker=marker, facecolor=colour,
                   edgecolor='none', alpha=0.55, zorder=2)
        ax.hlines(float(np.median(values)), i - 0.24, i + 0.24,
                  colors=INK, linewidth=1.5, zorder=3)
        ax.annotate(f'{np.median(values):.2f}', (i + 0.26, np.median(values)),
                    fontsize=7.8, color=INK, va='center', ha='left')
    ax.axhline(0.5, color=INK, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.text(0.02, 0.515, '0.5 threshold', transform=ax.get_yaxis_transform(),
            fontsize=7.4, color=INK, va='bottom')
    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(0.45, 1.03)
    ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xticks([0, 1], ['Gold\n(n=17)', 'Non-gold\n(n=174)'])
    ax.set_ylabel('Verifier score')
    decorate(ax, 'y')
    panel(ax, '(a)')

    run = sorted(order['rows'], key=lambda r: int(r['qid'][1:]))
    for y, (key, colour, marker) in enumerate(
            [('filter_only', STEEL, 's'), ('judged', BRICK, 'o')]):
        for j, r in enumerate(run):
            hit = bool(r[key]['hit'])
            bx.scatter(j, y, s=36, marker=marker,
                       facecolor=colour if hit else WHITE,
                       edgecolor=colour, linewidth=0.9, zorder=3)
        count = sum(bool(r[key]['hit']) for r in run)
        bx.annotate(f'{count}/16', (16.0, y), fontsize=8.5,
                    color=colour, fontweight='bold', va='center', ha='left')
    bx.set_xlim(-0.6, 18.0)
    bx.set_ylim(1.55, -0.55)
    bx.set_yticks([1, 0], ['Judge order', 'Fusion order'])
    bx.set_xticks([0, 3, 7, 11, 15], ['1', '4', '8', '12', '16'])
    bx.set_xlabel('Question number')
    decorate(bx, 'both')
    panel(bx, '(b)')
    bx.text(0.015, 0.02, 'same 16 pools; scores from a separate archive',
            transform=bx.transAxes, fontsize=7.4, color=INK, va='bottom')

    pair_rows = [{'qid': r['qid'], 'fusion_hit': int(bool(r['filter_only']['hit'])),
                  'judge_hit': int(bool(r['judged']['hit']))} for r in run]
    csv_write('verifier_order_pairs.csv', pair_rows,
              ['qid', 'fusion_hit', 'judge_hit'])
    save(fig, 'fig_opt_verifier')


def manifest():
    sources = [FROZEN, FROZEN_STATS, R3, R3_STATS, ORIG_GRADE, REP_GRADE,
               SCORES, ORDER, FRESH, DESC_AUDIT, PROBE]
    manifest_data = {
        'sources_sha256': {
            str(p.relative_to(ROOT)).replace('\\', '/'):
                hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
        },
        'figures': ['fig_opt_route', 'fig_opt_content', 'fig_opt_answer',
                    'fig_opt_verifier'],
        'note': ('Matplotlib, Origin-style presentation; the Origin application '
                 'was not used. All counts and intervals are recomputed from the '
                 'archived records before plotting.'),
        'route': 'frozen 72 in-domain questions; A0/A3 route and containment; '
                 'read-all mechanical scan.',
        'content': 'frozen and same-question follow-up, 72 in-domain questions; '
                   'follow-up read-all incomplete and not plotted.',
        'answer': 'original and common-substrate 30-cell grades; markers only; '
                  'strict and alias counts are annotated.',
        'verifier': '191 logged scores and a separate 16-pool ordering archive; '
                    'the score archive and ordering archive are not the same requests.',
        'matplotlib_version': matplotlib.__version__,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'manifest.json').write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    frozen, r3 = read(FROZEN), read(R3)
    orig, rep = read(ORIG_GRADE), read(REP_GRADE)
    scores, order = read(SCORES), read(ORDER)
    route_figure(frozen, r3)
    content_figure(frozen, r3)
    answer_figure(orig, rep)
    verifier_figure(scores, order)
    manifest()
    print(f'Wrote figures to {FIG}')
    print(f'Wrote data to {DATA}')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT / 'paper-kbs' / 'experiments'))
    main()
