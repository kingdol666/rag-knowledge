#!/usr/bin/env python3
"""Build the 1280x720 YouTube thumbnail from real footage.

Left: title block. Right: an untouched crop of the live retrieval session
(the NISQ hit card with its fused score and owning base), so the thumbnail shows
the actual product rather than an illustration.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIDEO = HERE / "qdcvr-demo.mp4"
WORK = HERE / "build"
FRAME = WORK / "thumb_frame.png"
OUT = HERE / "thumbnail.png"
W, H = 1280, 720

ACCENT = "#b4441f"


def extract_frame() -> None:
    """Grab the instant the NISQ result card is on screen."""
    WORK.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "62",
                    "-i", str(VIDEO), "-frames:v", "1", str(FRAME)],
                   check=True)
    # crop the result card region, scaled up for the thumbnail
    # include the query line and the whole first hit card, at 16:9
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(FRAME),
                    "-vf", "crop=1330:748:540:186,scale=972:-1",
                    str(WORK / "thumb_crop.png")], check=True)


def build_html() -> Path:
    css = f"""
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:{W}px;height:{H}px;font-family:"Segoe UI",Arial,sans-serif;
      background:#fbfaf7;overflow:hidden;position:relative;
      background-image:radial-gradient(circle at 8% 4%,#f7e6df 0%,transparent 44%)}}
    .rule{{position:absolute;left:0;top:0;width:9px;height:{H}px;
      background:{ACCENT}}}
    .left{{position:absolute;left:52px;top:74px;width:470px}}
    .brand{{font-size:96px;font-weight:800;letter-spacing:-4px;color:{ACCENT};
      line-height:.94}}
    .sub{{font-size:27px;font-weight:700;color:#1c1c1e;margin-top:20px;
      line-height:1.26}}
    .pts{{margin-top:24px;font-size:19px;color:#4a4a52;line-height:1.62}}
    .pts b{{color:{ACCENT}}}
    .badge{{position:absolute;left:52px;bottom:66px;display:flex;gap:10px}}
    .chip{{border:2px solid #cfccc4;border-radius:999px;padding:8px 19px;
      font-size:19px;font-weight:600;color:#3d3d44;background:#fff}}
    .chip.acc{{border-color:{ACCENT};color:#8f3315;background:#fdf1ec}}
    .shotwrap{{position:absolute;right:30px;top:118px;width:684px;
      border:2px solid #ddd9d0;border-radius:12px;overflow:hidden;
      background:#fff;box-shadow:0 14px 34px rgba(40,24,18,.17)}}
    .shotwrap img{{width:100%;display:block}}
    .shotlabel{{position:absolute;right:30px;top:78px;font-size:17px;
      letter-spacing:1.6px;text-transform:uppercase;color:#8a8a94;
      font-weight:600}}
    """
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style>
    </head><body>
      <div class="rule"></div>
      <div class="left">
        <div class="brand">QDCVR</div>
        <div class="sub">Content decides where documents live.<br>
        Reading decides what answers.</div>
        <div class="pts">
          50 real papers &middot; 5 category bases<br>
          <b>0&ndash;8 content gate</b> on the text actually read<br>
          gold document ranked first <b>10/10</b><br>
          honest <b>not-found</b> instead of fabrication
        </div>
      </div>
      <div class="shotlabel">live retrieval session</div>
      <div class="shotwrap"><img src="thumb_crop.png"></div>
      <div class="badge">
        <div class="chip acc">CIKM Demo</div>
        <div class="chip">3:00</div>
        <div class="chip">English</div>
      </div>
    </body></html>"""
    p = WORK / "thumbnail.html"
    p.write_text(html, encoding="utf-8")
    return p


def render(src: Path) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
        pg = b.new_page(viewport={"width": W, "height": H},
                        device_scale_factor=1)
        pg.goto(src.as_uri(), wait_until="load")
        pg.wait_for_timeout(900)
        pg.screenshot(path=str(OUT))
        b.close()


def main() -> int:
    if not VIDEO.exists():
        raise SystemExit(f"missing {VIDEO}")
    print("[1/3] extracting frame at 0:62")
    extract_frame()
    print("[2/3] composing")
    html = build_html()
    print("[3/3] rendering")
    render(html)
    size = OUT.stat().st_size / 1024
    print(f"-> {OUT}  ({size:.0f} KB)")
    if size > 2000:
        print("   NOTE: YouTube caps thumbnails at 2 MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
