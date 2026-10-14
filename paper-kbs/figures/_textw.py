import matplotlib
matplotlib.use("Agg")
import importlib.util, io
spec = importlib.util.spec_from_file_location("f", r"paper-kbs\figures\figures.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import matplotlib.pyplot as plt
from matplotlib.text import Text

rows=[]
def spy(fig, name, tight=True):
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    W,H = fig.get_size_inches()
    for a in fig.findobj(Text):
        t = a.get_text()
        if not t.strip(): continue
        tb = a.get_window_extent(r)
        rows.append((name, t, a.get_fontsize(), tb.width/fig.dpi, tb.height/fig.dpi))
    plt.close(fig)
m.save = spy

def one(fn):
    global rows
    try: fn()
    except Exception as e:
        pass
for fn in (m.fig_architecture, m.fig_lanes, m.fig_retrieval, m.fig_inflation, m.fig_e2e,
           m.fig_margin_variants, m.fig_ood_kbs, m.fig_anatomy, m.fig_robustness):
    one(fn)

# print fig1 and fig2 rows only
import collections
for nm in ("fig1_architecture","fig2_lanes"):
    print(f"##### {nm}")
    for r in rows:
        if r[0]!=nm: continue
        print(f"  fs={r[2]:.2f} w={r[3]:6.3f} h={r[4]:5.3f}  {r[1]!r}")
