#!/usr/bin/env python3
"""生成演示用 PDF(wind-energy.pdf) — matplotlib 文字排版, 内容与 wind-energy.md 独立成篇."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.pyplot import figure, close

OUT = Path(__file__).resolve().parent / "en" / "wind-energy.pdf"

PAGE1 = """Wind Energy: From Kinetic Energy to the Grid

Wind turbines convert the kinetic energy of moving air into electricity.
The theoretical maximum efficiency of any wind turbine is 59.3 percent,
a limit derived by Albert Betz in 1919 and known as the Betz limit.
Modern commercial turbines achieve roughly 45 to 50 percent efficiency.

Because available power grows with the cube of wind speed, doubling the
average wind speed increases the energy yield about eightfold. Careful
siting is therefore the single most important decision in a wind project.

Utility-scale onshore turbines today typically rate 3 to 6 megawatts with
rotor diameters of 120 to 150 metres. The largest offshore machines reach
15 megawatts, with rotor diameters of 236 metres."""

PAGE2 = """Global Capacity and Offshore Growth

Global installed wind capacity reached about 1 terawatt in 2023, with
China, the United States, Germany and India the largest markets.

Offshore wind is growing fastest because marine winds are steadier and
stronger. The United Kingdom's Dogger Bank project, planned at
3.6 gigawatts and expected to complete around 2026, will be the world's
largest offshore wind farm.

Turbines begin producing at cut-in wind speeds near 3 metres per second
and shut down for safety near 25 metres per second. Capacity factors
average 35 to 45 percent onshore and exceed 50 percent at the best
offshore sites."""


def main() -> None:
    with PdfPages(OUT) as pdf:
        for i, text in enumerate((PAGE1, PAGE2), start=1):
            fig = figure(figsize=(8.27, 11.69), dpi=100)
            fig.text(0.1, 0.95, f"Wind Energy Basics  ({i}/2)", fontsize=14,
                     weight="bold")
            fig.text(0.1, 0.9, text, fontsize=11, va="top", wrap=True)
            pdf.savefig(fig)
            close(fig)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
