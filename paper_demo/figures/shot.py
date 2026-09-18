#!/usr/bin/env python3
"""HTML -> PNG 截图工具 (playwright, 高DPI). 供配图 Agent 自检循环使用.
用法: python shot.py <in.html> <out.png> [width] [height] [scale]
默认 2400x1200 @2x, 等待 1200ms 字体/布局稳定后截图。"""
import sys
from playwright.sync_api import sync_playwright

def main() -> int:
    html, png = sys.argv[1], sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 1200
    scale = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h},
                        device_scale_factor=scale)
        pg.goto("file:///" + html.replace("\\", "/").lstrip("/"))
        pg.wait_for_timeout(1200)
        pg.screenshot(path=png, full_page=True)
        b.close()
    print("saved", png)
    return 0

if __name__ == "__main__":
    sys.exit(main())
