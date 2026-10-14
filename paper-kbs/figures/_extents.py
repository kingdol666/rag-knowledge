import matplotlib
matplotlib.use("Agg")
import importlib.util
spec = importlib.util.spec_from_file_location("f", r"paper-kbs\figures\figures.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import matplotlib.pyplot as plt

rep = []
def spy(fig, name, tight=True):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.get_size_inches()
    items = []
    for a in fig.findobj():
        try:
            tb = a.get_tightbbox(r)
        except Exception:
            continue
        if tb is None or tb.width <= 0 or tb.height <= 0:
            continue
        items.append((tb.x0, tb.x1, tb.y0, tb.y1))
    x0 = min(i[0] for i in items)/fig.dpi; x1 = max(i[1] for i in items)/fig.dpi
    y0 = min(i[2] for i in items)/fig.dpi; y1 = max(i[3] for i in items)/fig.dpi
    rep.append((name, W, H, x0, x1, y0, y1))
    plt.close(fig)
m.save = spy
for fn in (m.fig_architecture, m.fig_lanes, m.fig_retrieval, m.fig_inflation,
           m.fig_e2e, m.fig_margin_variants, m.fig_ood_kbs, m.fig_anatomy,
           m.fig_robustness):
    fn()
print(f"{'name':24s} {'figW':>6s} {'x0':>7s} {'x1':>7s} {'overW':>7s}  | {'figH':>6s} {'y0':>7s} {'y1':>7s} {'overH':>7s}")
for name, W, H, x0, x1, y0, y1 in rep:
    print(f"{name:24s} {W:6.2f} {x0:7.3f} {x1:7.3f} {x1-W:7.3f}  | {H:6.2f} {y0:7.3f} {y1:7.3f} {y1-H:7.3f}")
