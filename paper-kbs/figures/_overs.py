import matplotlib
matplotlib.use("Agg")
import importlib.util
spec = importlib.util.spec_from_file_location("f", r"paper-kbs\figures\figures.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib.legend import Legend

def probe(fn):
    holder = {}
    def spy(fig, name, tight=True):
        fig.canvas.draw(); r = fig.canvas.get_renderer()
        W, H = fig.get_size_inches()
        rows = []
        for a in fig.findobj():
            try: tb = a.get_tightbbox(r)
            except Exception: continue
            if tb is None: continue
            if isinstance(a, Text) and a.get_text().strip():
                rows.append(("TEXT", a.get_text()[:34].replace("\n","|"),
                             tb.x0/fig.dpi, tb.x1/fig.dpi, tb.y0/fig.dpi, tb.y1/fig.dpi))
            elif isinstance(a, Legend):
                rows.append(("LEGEND", str(a.get_loc())[:20],
                             tb.x0/fig.dpi, tb.x1/fig.dpi, tb.y0/fig.dpi, tb.y1/fig.dpi))
        bad = [x for x in rows if x[2] < -0.02 or x[3] > W+0.02 or x[4] < -0.02 or x[5] > H+0.02]
        print(f"=== {name}  canvas {W:.2f}x{H:.2f}  offenders {len(bad)}/{len(rows)}")
        for k, txt, x0, x1, y0, y1 in bad:
            print(f"   {k:6s} x[{x0:7.3f},{x1:7.3f}] y[{y0:7.3f},{y1:7.3f}]  {txt!r}")
        plt.close(fig)
    m.save = spy
    fn()

for fn in (m.fig_architecture, m.fig_lanes, m.fig_retrieval, m.fig_e2e, m.fig_anatomy, m.fig_robustness):
    probe(fn)
