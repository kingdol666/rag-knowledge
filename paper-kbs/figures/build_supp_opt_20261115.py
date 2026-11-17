#!/usr/bin/env python3
"""Build the two reworked supplementary figures for journal_opt_20261115.

  fig_opt_s_answer  -- original 30-cell grid: gold-ID, strict keywords, markers
                       for P/F/C, with the old "Dense" label removed.
  fig_opt_s_margin  -- cut-margin replay (gold kept) and three verdict roles
                       (fusion order, verdict order, verdict filter); the old
                       RRF role is not plotted.

All counts are asserted against the archived grades/summary before plotting.
Style matches the main evaluation figures: Arial, closed frame, inward ticks,
light horizontal grid, steel/ochre/brick/slate palette, vector PDF.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / 'paper-kbs/tex/journal_opt_20261115/figs'
DATA = ROOT / 'paper-kbs/figures/experiment_opt_20261115_data'
GRADE = ROOT / 'benchmark-suite/results/exp_r2_grade_corrected.json'
ABSTAIN = ROOT / 'paper-kbs/experiments/results/exp3_abstention.json'
ORDER = ROOT / 'paper-kbs/experiments/results/exp5_judge_filter.json'

INK = '#23394F'
STEEL = '#35689A'
LSTEEL = '#8FB3C9'
BRICK = '#A9542F'
SLATE = '#8D98A4'
GRID = '#E3E8ED'
WHITE = '#FFFFFF'

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
    'font.size': 8.3, 'axes.labelsize': 8.5,
    'xtick.labelsize': 8.0, 'ytick.labelsize': 8.0, 'legend.fontsize': 8.0,
    'axes.linewidth': 0.8, 'axes.edgecolor': INK, 'text.color': INK,
    'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.major.width': 0.8, 'ytick.major.width': 0.8,
    'pdf.fonttype': 42, 'ps.fonttype': 42,
    'savefig.facecolor': WHITE, 'figure.facecolor': WHITE,
    'axes.facecolor': WHITE, 'savefig.dpi': 300,
})


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def decorate(ax, grid_axis: str = 'y'):
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color(INK)
    ax.tick_params(axis='both', direction='in', length=3.0, width=0.8,
                   top=True, right=True, pad=3)
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


def write_csv(name, rows_, fields):
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_)


def answer_summary():
    g = read(GRADE)['grades']
    assert [g[t]['gold_hit'] for t in ('a2', 'b', 'c')] == [10, 10, 10]
    assert [g[t]['kw_ok'] for t in ('a2', 'b', 'c')] == [9, 9, 9]
    assert [g[t]['cited'] for t in ('a2', 'b', 'c')] == [9, 7, 2]
    metrics = [('Gold-ID', 'gold_hit', STEEL), ('Strict keywords', 'kw_ok', LSTEEL),
               ('Citation markers', 'cited', BRICK)]
    arms = [('P', 'a2'), ('F', 'b'), ('C', 'c')]
    records = []
    fig, ax = plt.subplots(figsize=(3.45, 2.45))
    fig.subplots_adjust(left=0.15, right=0.985, top=0.72, bottom=0.22)
    width = 0.24
    for k, (name, key, colour) in enumerate(metrics):
        for i, (label, track) in enumerate(arms):
            v = g[track][key]
            x = i + (k - 1) * width
            ax.bar(x, v, width=width, color=colour, edgecolor=WHITE,
                   linewidth=0.4, zorder=3)
            ax.text(x, v + 0.18, str(v), ha='center', va='bottom',
                    fontsize=7.8, color=INK)
            records.append({'arm': label, 'metric': name, 'n': 10,
                            'value': v})
    ax.axhline(10, color=SLATE, linewidth=0.6, linestyle=(0, (4, 3)), zorder=1)
    ax.set_xticks(range(3), [a[0] for a in arms])
    ax.set_ylim(0, 12.6)
    ax.set_yticks([0, 2, 4, 6, 8, 10])
    ax.set_ylabel('Questions (of 10)')
    ax.set_xlabel('Answer grid arm')
    decorate(ax, 'y')
    ax.legend(handles=[Line2D([0], [0], color=c, marker='s', linestyle='none',
                              markersize=5.0, label=n)
                       for n, _, c in metrics],
              loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3,
              fontsize=7.3, frameon=False, handletextpad=0.3,
              columnspacing=0.8, borderaxespad=0.0)
    write_csv('supp_s_answer.csv', records, ['arm', 'metric', 'n', 'value'])
    save(fig, 'fig_opt_s_answer')


def margin_and_roles():
    cut = read(ABSTAIN)['cut_replay']
    keys = ['0.05', '0.1', '0.15', '0.2', '0.25', '0.3', '0.35']
    margins = [float(k) for k in keys]
    gold = [int(cut[k]['gold_kept']) for k in keys]
    mean_kept = [float(cut[k]['mean_kept']) for k in keys]
    assert gold == [8, 14, 16, 17, 17, 17, 17]
    assert mean_kept == [6.4, 8.9, 10.4, 11.1, 11.4, 11.7, 11.9]
    summary = read(ORDER)['summary']
    roles = [('Fusion', summary['filter_only']['hit@5'], STEEL),
             ('Verdict order', summary['judged']['hit@5'], BRICK),
             ('Verdict filter', summary['filter_only']['hit@5'], STEEL)]
    assert round(roles[0][1], 4) == 0.9375
    assert round(roles[1][1], 4) == 0.4375
    assert round(roles[2][1], 4) == 0.9375
    records = []
    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(7.15, 2.55), gridspec_kw={'width_ratios': [1.0, 1.05]})
    fig.subplots_adjust(left=0.085, right=0.985, top=0.86, bottom=0.22,
                        wspace=0.32)
    ax.plot(margins, gold, color=STEEL, marker='o', markersize=4.6,
            linewidth=1.0, zorder=3)
    for x in (0.15, 0.20):
        ax.axvline(x, color=STEEL if x == 0.20 else SLATE,
                   linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    ax.annotate('16/17', (0.15, 16.2), xytext=(-4, 6), textcoords='offset points',
                fontsize=7.6, color=INK, ha='right')
    ax.annotate('17/17', (0.20, 16.8), xytext=(4, 6), textcoords='offset points',
                fontsize=7.6, color=INK, ha='left')
    ax.text(0.355, 1.0, 'mean kept 6.4 → 11.9 of 12', fontsize=7.2,
            color=SLATE, va='bottom', ha='right')
    ax.set_xlim(0.035, 0.365)
    ax.set_ylim(0, 18.5)
    ax.set_xticks([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35])
    ax.set_yticks([0, 4, 8, 12, 16])
    ax.set_xlabel('Relative margin $m$ (best $-$ $m$)')
    ax.set_ylabel('Gold instances kept (of 17)')
    decorate(ax, 'y')
    panel(ax, '(a)')

    for i, (label, value, colour) in enumerate(roles):
        bx.bar(i, value, width=0.55, color=colour, edgecolor=WHITE,
               linewidth=0.4, zorder=3)
        bx.text(i, value + 0.015, f'{value:.2f}', ha='center', va='bottom',
                fontsize=8.0, color=INK)
        records.append({'panel': 'b', 'role': label, 'hit@5': value})
    bx.set_xticks(range(3), [r[0] for r in roles])
    bx.set_ylim(0, 1.10)
    bx.set_yticks([0, 0.5, 1.0])
    bx.set_ylabel('Hit@5')
    bx.set_xlabel('Verdict role (same pools)')
    decorate(bx, 'y')
    panel(bx, '(b)')
    for m, g, mk in zip(margins, gold, mean_kept):
        records.append({'panel': 'a', 'margin': m, 'gold_kept': g,
                        'mean_kept': mk})
    write_csv('supp_s_margin.csv', records,
              ['panel', 'margin', 'gold_kept', 'mean_kept', 'role', 'hit@5'])
    save(fig, 'fig_opt_s_margin')


def main():
    answer_summary()
    margin_and_roles()
    print(f'Wrote supplementary figures to {FIG}')


if __name__ == '__main__':
    main()
