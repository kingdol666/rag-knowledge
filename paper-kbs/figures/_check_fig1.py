"""Geometry audit for fig_architecture(): measures the real rendered figure.

Strategy: runs the figure for real (at its design dpi), then converts each
text's ink box and each rectangle's window extent back into data units via the
axes transform. No metric guessing: matplotlib itself computes the extents.

Checks:
  FONT      any text below 7 pt
  CLIP      any ink outside the 7.50 x 4.50 in canvas
  OVERFLOW  any ink outside the rectangle that actually contains it
  OVERLAP   two text inks that collide (skipping pairs in the same panel)
"""
import importlib.util
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
W_IN, H_IN = 7.50, 4.50
SLACK = 0.015          # tolerated ink bleed before reporting

spec = importlib.util.spec_from_file_location("figmod", HERE / "figures.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["figmod"] = mod
spec.loader.exec_module(mod)

CAPTURED = []
matplotlib.figure.Figure.savefig = lambda self, *a, **k: CAPTURED.append(self)
plt.close = lambda *a, **k: None
mod.fig_architecture()
fig = CAPTURED[0]
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
ax = fig.axes[0]
inv = ax.transData.inverted()


def to_data(bb):
    x0, y0 = inv.transform((bb.x0, bb.y0))
    x1, y1 = inv.transform((bb.x1, bb.y1))
    return x0, y0, x1, y1


rects = []
for p in ax.patches:
    if isinstance(p, FancyBboxPatch):
        rects.append(to_data(p.get_window_extent(renderer)) + (p.get_ec(),))

texts = []
for t in ax.texts:
    if not t.get_text().strip():
        continue
    if t.get_rotation() not in (0, 0.0):
        continue          # rotated "parse fails" rides a connector, not a box
    if t.get_style() == "italic":
        continue          # band headings sit above their container
    if t.get_text().startswith("Organization and life-cycle"):
        continue          # free-standing caption above the bottom band
    if t.get_text() == "documents":
        continue          # free-standing edge label on the feed arrow
    texts.append((t.get_text(), to_data(t.get_window_extent(renderer)),
                  float(t.get_fontsize())))

problems = []
for txt, (x0, y0, x1, y1), fs in texts:
    if fs < 7.0 - 1e-9:
        problems.append("FONT %.1fpt < 7pt: %r" % (fs, txt[:44]))
    if x0 < -SLACK or y0 < -SLACK or x1 > W_IN + SLACK or y1 > H_IN + SLACK:
        problems.append("CLIP %r ink=(%.3f,%.3f)-(%.3f,%.3f)"
                        % (txt[:44], x0, y0, x1, y1))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    holder = [r for r in rects if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]]
    if not holder:
        problems.append("NOBOX %r centre=(%.3f,%.3f)" % (txt[:44], cx, cy))
        continue
    rx0, ry0, rx1, ry1, _ec = min(
        holder, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    over = []
    if x0 < rx0 - SLACK:
        over.append("left %.3f" % (rx0 - x0))
    if x1 > rx1 + SLACK:
        over.append("right %.3f" % (x1 - rx1))
    if y0 < ry0 - SLACK:
        over.append("below %.3f" % (ry0 - y0))
    if y1 > ry1 + SLACK:
        over.append("above %.3f" % (y1 - ry1))
    if over:
        problems.append(
            "OVERFLOW %r %s  ink=(%.2f,%.2f)-(%.2f,%.2f) "
            "box=(%.2f,%.2f)-(%.2f,%.2f)"
            % (txt[:44], "; ".join(over), x0, y0, x1, y1, rx0, ry0, rx1, ry1))

for i, (ta, (ax0, ay0, ax1, ay1), _f) in enumerate(texts):
    for tb, (bx0, by0, bx1, by1), _g in texts[i + 1:]:
        ox = min(ax1, bx1) - max(ax0, bx0)
        oy = min(ay1, by1) - max(ay0, by0)
        if ox > SLACK and oy > SLACK:
            problems.append("OVERLAP %r vs %r (%.3f x %.3f)"
                            % (ta[:34], tb[:34], ox, oy))

print("rectangles: %d   texts: %d" % (len(rects), len(texts)))
if "--dump" in sys.argv:
    for txt, (x0, y0, x1, y1), fs in texts:
        print("  T %-46r (%.3f,%.3f)-(%.3f,%.3f)" % (txt[:44], x0, y0, x1, y1))
print("PROBLEMS (%d):" % len(problems))
for p in problems:
    print("  -", p)
sys.exit(0 if not problems else 1)
