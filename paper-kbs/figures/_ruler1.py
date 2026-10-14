"""One-off: apply the final vertical ruler to fig_architecture()."""
import pathlib

p = pathlib.Path(__file__).with_name("figures.py")
s = p.read_text(encoding="utf-8")

subs = [
    ("    H = 7.43", "    H = 7.29"),
    ('cband(6.81, 0.62, "Client and agent layer")',
     'cband(6.63, 0.66, "Client and agent layer")'),
    ('panel(x, 6.99, W3, 0.34, t, d, fc="#EDF3FA", ec=C["blue"])',
     'panel(x, 6.73, W3, 0.34, t, d, fc="#EDF3FA", ec=C["blue"])'),
    ('cband(4.83, 1.85, "Tool layer")', 'cband(4.54, 1.96, "Tool layer")'),
    ('        (0.36, 6.30), W_FULL - 0.54, 0.22, boxstyle="square,pad=0.0",',
     '        (0.36, 6.06), W_FULL - 0.54, 0.22, boxstyle="square,pad=0.0",'),
    ("    a = ax.text(W_FULL / 2, 6.41,", "    a = ax.text(W_FULL / 2, 6.17,"),
    ("    _guard(ax, a, 0.36, 6.30, W_FULL - 0.54, 0.22)",
     "    _guard(ax, a, 0.36, 6.06, W_FULL - 0.54, 0.22)"),
    ("        panel(X4[c], 5.80 - r * 0.48, W4, 0.36, t, d,",
     "        panel(X4[c], 5.56 - r * 0.48, W4, 0.36, t, d,"),
    ('    panel(X4[0], 4.92, W4, 0.28, "Lane policy", "server-side filter",',
     '    panel(X4[0], 4.64, W4, 0.28, "Lane policy", "server-side filter",'),
    ('    panel(X4[2], 4.92, W4, 0.28, "Long-running work", "pollable tasks",',
     '    panel(X4[2], 4.64, W4, 0.28, "Long-running work", "pollable tasks",'),
    ("        arrow(ax, x, 6.99, x, 6.70, lw=0.8)",
     "        arrow(ax, x, 6.73, x, 6.52, lw=0.8)"),
    ('cband(3.45, 1.25, "Domain service layer")',
     'cband(3.23, 1.18, "Domain service layer")'),
    ("        panel(X4[c], 4.17 - r * 0.52, W4, 0.36, t, d,",
     "        panel(X4[c], 3.83 - r * 0.50, W4, 0.36, t, d,"),
    ('cband(2.54, 0.78, "Storage layer")', 'cband(2.42, 0.68, "Storage layer")'),
    ('        panel(x, 2.81, W4, 0.36, t, d, fc="#F2F2F2", ec=C["dgrey"])',
     '        panel(x, 2.52, W4, 0.36, t, d, fc="#F2F2F2", ec=C["dgrey"])'),
    ("    for y1, y2 in ((4.83, 4.81), (3.45, 3.42)):",
     "    for y1, y2 in ((4.54, 4.52), (3.23, 3.20)):"),
    ('cband(1.03, 1.38, "Acquisition pipeline")',
     'cband(1.03, 1.26, "Acquisition pipeline")'),
    ("    y1, y2 = 1.91, 1.19                          # top row, wrap-around row",
     "    y1, y2 = 1.73, 1.13                          # top row, wrap-around row"),
    ("    arrow(ax, X4[3] + W4 / 2, y1, X4[3] + W4 / 2, 1.71, lw=0.8)\n"
     "    arrow(ax, X4[3] + W4 / 2, 1.71, X4[0] + W4 / 2, 1.71, lw=0.8)\n"
     "    arrow(ax, X4[0] + W4 / 2, 1.71, X4[0] + W4 / 2, y2, lw=0.8)",
     "    arrow(ax, X4[3] + W4 / 2, y1, X4[3] + W4 / 2, 1.60, lw=0.8)\n"
     "    arrow(ax, X4[3] + W4 / 2, 1.60, X4[0] + W4 / 2, 1.60, lw=0.8)\n"
     "    arrow(ax, X4[0] + W4 / 2, 1.60, X4[0] + W4 / 2, y2, lw=0.8)"),
    ('    ax.text(0.10, 1.60, "documents", fontsize=_FS, color=C["grey"],',
     '    ax.text(0.10, 1.62, "documents", fontsize=_FS, color=C["grey"],'),
    ('    arrow(ax, 0.20, 1.44, 0.20, 2.99, lw=0.8, color=C["grey"])',
     '    arrow(ax, 0.20, 1.46, 0.20, 2.70, lw=0.8, color=C["grey"])'),
    ("    # 5.38 x 7.43 in canvas", "    # 5.38 x 7.29 in canvas"),
]

missing = [a for a, _ in subs if a not in s]
if missing:
    raise SystemExit("NOT FOUND:\n" + "\n".join(missing))
for a, b in subs:
    s = s.replace(a, b, 1)
p.write_text(s, encoding="utf-8")
print("patched", len(subs), "sites")
