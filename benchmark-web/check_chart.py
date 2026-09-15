"""Focused check: does the latency <canvas> actually paint pixels?

A full-page screenshot can show a blank canvas even when Chart.js rendered, so
this samples the canvas bitmap directly via ``toDataURL`` and counts distinct
colours. Run against the live dashboard.
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

UI = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3001"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(UI, wait_until="networkidle", timeout=90_000)
    page.wait_for_selector(".method-checkbox label", timeout=60_000)

    page.fill("textarea", "battery thermal management phase change material")
    page.click("button:has-text('Compare + metrics')")
    page.wait_for_selector(".comparison-table tbody tr", timeout=180_000)
    page.wait_for_selector(".chart-container canvas", timeout=60_000)
    page.wait_for_timeout(2500)  # let Chart.js finish its animation

    stats = page.evaluate(
        """() => {
            const c = document.querySelector('.chart-container canvas');
            if (!c) return { ok: false, reason: 'no canvas' };
            const ctx = c.getContext('2d');
            const { width: w, height: h } = c;
            const data = ctx.getImageData(0, 0, w, h).data;
            const colours = new Set();
            let opaque = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i + 3] > 0) {
                    opaque += 1;
                    colours.add(`${data[i]},${data[i + 1]},${data[i + 2]}`);
                }
            }
            return { ok: true, w, h, opaque, colours: colours.size };
        }"""
    )
    print(f"canvas: {stats}")
    painted = stats.get("ok") and stats.get("opaque", 0) > 500 and stats.get("colours", 0) >= 3
    print("RESULT:", "PASS - the latency chart painted real pixels" if painted
          else "FAIL - the canvas is blank")
    page.locator(".chart-container").screenshot(path="chart-check.png")
    print("chart screenshot -> chart-check.png")
    browser.close()

sys.exit(0 if painted else 1)
