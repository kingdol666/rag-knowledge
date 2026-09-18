#!/usr/bin/env python3
"""Build the QDCVR demonstration video (CIKM Demo, ~3 minutes, 1920x1080).

Pipeline
  1. edge-tts renders one English narration clip per segment (neural voice).
  2. Each segment's visual is rendered to a 1920x1080 video piece:
       clip:<name>  -> the recorded console footage, trimmed to the narration
       card:<name>  -> an artifact card carrying real benchmark text
       title        -> opening / closing card
  3. A lower-third caption is composited onto every piece.
  4. Pieces are concatenated, the narration track is concatenated to match, and
     both are muxed into demo.mp4 (H.264 + AAC, faststart).

Run:  python build_video.py            # full build
      python build_video.py --audio    # only regenerate narration
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from narration import (CAPTIONS, CARD_ANSWER, CARD_NOTFOUND,  # noqa: E402
                       PAUSE_AFTER_MS, RATE, SEGMENTS, VOICE)

REC = HERE / "rec"
CLIPS = REC / "clips"
OUT = HERE / "build"
AUDIO = OUT / "audio"
VIS = OUT / "visual"
PIECES = OUT / "pieces"
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_SB = "C:/Windows/Fonts/seguisb.ttf"
W, H, FPS = 1920, 1080, 30

ACCENT = "#b4441f"
INK = "#17171a"
MUTED = "#5c5c66"


# ── helpers ──────────────────────────────────────────────────────────────────
def run(cmd: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        print("FFMPEG FAIL:", " ".join(cmd)[:400])
        print((r.stderr or "")[-1500:])
        raise SystemExit(1)
    if not quiet:
        print((r.stderr or "")[-400:])
    return r


def dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def esc(t: str) -> str:
    """Escape text for ffmpeg drawtext."""
    return (t.replace("\\", "\\\\").replace(":", "\\:")
             .replace("'", "\u2019").replace("%", "\\%"))


# ── 1. narration audio ───────────────────────────────────────────────────────
async def _tts(text: str, dest: Path, voice: str, rate: str) -> None:
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate)
    await c.save(str(dest))


def tts_with_retry(text: str, dest: Path, tries: int = 6) -> None:
    """edge-tts intermittently returns an empty stream; retry with backoff."""
    import time as _t
    last: Exception | None = None
    for i in range(tries):
        try:
            if dest.exists():
                dest.unlink()
            asyncio.run(_tts(text, dest, VOICE, RATE))
            if dest.exists() and dest.stat().st_size > 2000:
                return
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"      retry {i+1}/{tries} ({str(last)[:60]})")
        _t.sleep(2.5 * (i + 1))
    raise SystemExit(f"tts failed for {dest.name}: {last}")


def make_audio() -> dict[str, float]:
    AUDIO.mkdir(parents=True, exist_ok=True)
    durs: dict[str, float] = {}
    for s in SEGMENTS:
        mp3 = AUDIO / f"{s['id']}.mp3"
        if not mp3.exists() or mp3.stat().st_size < 2000:
            tts_with_retry(s["text"], mp3)
        d = dur(mp3)
        durs[s["id"]] = d
        print(f"  [tts] {s['id']:<16} {d:6.2f}s")
    (OUT / "audio_durations.json").write_text(
        json.dumps(durs, indent=1), encoding="utf-8")
    return durs


# ── 2. card / title rendering ────────────────────────────────────────────────
CARD_CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;font-family:"Segoe UI",Arial,sans-serif;
  background:#fbfaf7;color:{INK};display:flex;flex-direction:column;
  padding:76px 100px;
  background-image:radial-gradient(circle at 88% 6%,#f6e7e0 0%,transparent 46%)}}
.kicker{{font-size:22px;letter-spacing:2.6px;text-transform:uppercase;
  color:{ACCENT};font-weight:600;margin-bottom:20px}}
h1{{font-size:46px;line-height:1.22;font-weight:700;max-width:1500px;
  margin-bottom:14px}}
.badge{{display:inline-block;margin:10px 0 30px;padding:11px 26px;
  border-radius:999px;background:#fdf1ec;border:2px solid {ACCENT};
  color:#8f3315;font-size:26px;font-weight:600}}
.rows{{display:flex;flex-direction:column;gap:19px;margin-top:6px}}
.row{{display:flex;gap:22px;align-items:flex-start;
  border-left:6px solid {ACCENT};padding-left:22px}}
.row .k{{flex:0 0 258px;font-size:25px;font-weight:700;color:#8f3315}}
.row .v{{font-size:25px;line-height:1.42;color:#26262c}}
.foot{{margin-top:auto;font-size:20px;color:{MUTED};
  border-top:2px solid #e6e3dc;padding-top:18px}}
.title-wrap{{flex:1;display:flex;flex-direction:column;justify-content:center;
  align-items:flex-start}}
.title-wrap .big{{font-size:118px;font-weight:800;letter-spacing:-3px;
  color:{ACCENT};line-height:1}}
.title-wrap .sub{{font-size:40px;color:#2b2b31;margin-top:26px;font-weight:600}}
.title-wrap .sub2{{font-size:29px;color:{MUTED};margin-top:18px;max-width:1250px;
  line-height:1.45}}
.title-wrap .meta{{font-size:23px;color:{MUTED};margin-top:44px;
  border-top:2px solid #e6e3dc;padding-top:20px;max-width:1250px}}
"""


def card_html(kind: str) -> str:
    if kind == "title":
        body = f"""<div class="title-wrap">
          <div class="big">QDCVR</div>
          <div class="sub">A deployable knowledge-base management platform</div>
          <div class="sub2">Documents are organized by what they say, and every
          retrieval is verified by reading it &mdash; with an explicit not-found
          contract when the evidence is not there.</div>
          <div class="meta">CIKM Demo &nbsp;&middot;&nbsp; system demonstration
          &nbsp;&middot;&nbsp; 50 real papers &middot; 5 category bases &middot;
          165 indexed documents</div>
        </div>"""
    elif kind == "title_end":
        body = f"""<div class="title-wrap">
          <div class="big">QDCVR</div>
          <div class="sub">Content decides where documents live.<br>
          Reading decides what answers.</div>
          <div class="sub2">Code and run artifacts:
          github.com/kingdol/rag-knowledge<br>
          Demonstration video &amp; benchmark artifacts ship with the repository.</div>
          <div class="meta">Visit the booth: bring a PDF, watch it classified, ask
          a question, inspect the score and the citation &mdash; then try to make
          it lie.</div>
        </div>"""
    else:
        c = CARD_ANSWER if kind == "answer" else CARD_NOTFOUND
        rows = "".join(
            f'<div class="row"><div class="k">{k}</div>'
            f'<div class="v">{v}</div></div>' for k, v in c["body"])
        body = (f'<div class="kicker">{c["kicker"]}</div>'
                f'<h1>{c["title"]}</h1>'
                f'<div class="badge">{c["badge"]}</div>'
                f'<div class="rows">{rows}</div>'
                f'<div class="foot">Text reproduced verbatim from the recorded '
                f'benchmark artifact in benchmark-suite/results/.</div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{CARD_CSS}</style></head><body>{body}</body></html>')


def render_still(kind: str, dest: Path) -> None:
    from playwright.sync_api import sync_playwright
    html = OUT / f"card_{kind}.html"
    html.write_text(card_html(kind), encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
        pg = b.new_page(viewport={"width": W, "height": H},
                        device_scale_factor=1)
        pg.goto(html.as_uri(), wait_until="load")
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(dest))
        b.close()
    print(f"  [still] {kind:<12} -> {dest.name}")


# ── 3. caption overlay ───────────────────────────────────────────────────────
def caption_png(text: str, dest: Path) -> None:
    css = f"""
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:{W}px;height:{H}px;background:transparent;
      font-family:"Segoe UI",Arial,sans-serif}}
    .bar{{position:absolute;left:0;right:0;bottom:0;height:104px;
      background:rgba(20,18,17,.80);display:flex;align-items:center;
      padding:0 96px}}
    .dot{{width:13px;height:13px;border-radius:50%;background:{ACCENT};
      margin-right:24px;flex:0 0 auto}}
    .t{{color:#fff;font-size:33px;font-weight:600;letter-spacing:.2px;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    """
    d = OUT / "caption.html"
    d.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{css}'
                 f'</style></head><body><div class="bar"><div class="dot"></div>'
                 f'<div class="t">{text}</div></div></body></html>',
                 encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(d.as_uri(), wait_until="load")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(dest), omit_background=True)
        b.close()


# ── 4. per-segment pieces ────────────────────────────────────────────────────
def clip_path(name: str) -> Path:
    d = CLIPS / name
    v = sorted(d.glob("*.webm"))
    if not v:
        raise SystemExit(f"missing recorded clip: {name}")
    return v[0]


def build_piece(seg: dict, seconds: float, cap: Path | None) -> Path:
    dest = PIECES / f"{seg['id']}.mp4"
    vis = seg["visual"]

    if vis.startswith("clip:"):
        name = vis.split(":", 1)[1]
        src = clip_path(name)
        have = dur(src)
        spare = max(0.0, have - seconds)
        # skip a little of the page-load at the head, keep the interaction whole
        ss = min(1.6, spare * 0.35)
        take = min(seconds, max(0.5, have - ss))
        vf = (f"[0:v]trim=start={ss:.2f}:duration={take:.2f},"
              f"setpts=PTS-STARTPTS,fps={FPS},"
              f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#f4f1ea[v0];"
              f"[v0][1:v]overlay=0:0:format=auto[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(cap),
               "-filter_complex", vf, "-map", "[v]",
               "-t", f"{seconds:.3f}", "-r", str(FPS),
               "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-pix_fmt", "yuv420p", str(dest)]
        run(cmd)
        print(f"  [piece] {seg['id']:<16} clip {name:<9} "
              f"{have:5.1f}s -> {seconds:5.1f}s (ss={ss:.2f})")
    else:
        kind = "title" if vis == "title" else (
            "title_end" if vis == "title_end" else vis.split(":", 1)[1])
        still = VIS / f"{kind}.png"
        if not still.exists():
            render_still(kind, still)
        # very slow push-in so a still frame still feels alive
        vf = (f"scale={int(W*1.06)}:{int(H*1.06)},"
              f"zoompan=z='min(1.0,1.0+0.00035*on)':d=1:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"s={W}x{H}:fps={FPS}[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(still),
               "-filter_complex", vf, "-map", "[v]",
               "-t", f"{seconds:.3f}", "-r", str(FPS),
               "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-pix_fmt", "yuv420p", str(dest)]
        run(cmd)
        print(f"  [piece] {seg['id']:<16} still {kind:<9} {seconds:5.1f}s")
    return dest


# ── main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    for d in (AUDIO, VIS, PIECES):
        d.mkdir(parents=True, exist_ok=True)

    print("[1/5] narration")
    durs = make_audio()
    if args.audio:
        return 0

    print("[2/5] card visuals")
    for k in ("title", "title_end", "answer", "notfound"):
        render_still(k, VIS / f"{k}.png")

    print("[3/5] captions")
    caps: dict[str, Path | None] = {}
    for s in SEGMENTS:
        if s["visual"].startswith("clip:"):
            c = OUT / f"cap_{s['id']}.png"
            caption_png(CAPTIONS.get(s["id"], ""), c)
            caps[s["id"]] = c
        else:
            caps[s["id"]] = None

    print("[4/5] pieces")
    plan = []
    for s in SEGMENTS:
        secs = max(s["min_seconds"], durs[s["id"]] + PAUSE_AFTER_MS / 1000.0)
        plan.append((s, round(secs, 2)))
    total = sum(p[1] for p in plan)
    for s, secs in plan:
        build_piece(s, secs, caps[s["id"]])
    print(f"        total video = {total:.1f}s")

    print("[5/5] mux")
    # video: concat pieces
    lst = OUT / "pieces.txt"
    lst.write_text("".join(f"file '{PIECES / (s['id'] + '.mp4')}'\n"
                           for s, _ in plan), encoding="utf-8")
    silent = OUT / "video_silent.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(silent)])

    # audio: pad each narration to its segment length, then concat
    aparts = []
    for s, secs in plan:
        a = AUDIO / f"{s['id']}.mp3"
        p = AUDIO / f"pad_{s['id']}.m4a"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(a),
             "-af", f"apad,atrim=0:{secs:.3f},asetpts=N/SR/TB",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             str(p)])
        aparts.append(p)
    alist = OUT / "audio.txt"
    alist.write_text("".join(f"file '{p}'\n" for p in aparts), encoding="utf-8")
    full_audio = OUT / "narration.m4a"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(alist), "-c", "copy", str(full_audio)])

    final = HERE / "qdcvr-demo.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i",
         str(full_audio), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", str(final)])

    print(f"\n-> {final}")
    print(f"   duration {dur(final):.1f}s   size {final.stat().st_size/1e6:.1f} MB")
    (OUT / "build_manifest.json").write_text(json.dumps(
        {"segments": [{"id": s["id"], "visual": s["visual"],
                       "narration_s": round(durs[s["id"]], 2),
                       "piece_s": secs} for s, secs in plan],
         "total_s": round(total, 2), "voice": VOICE, "rate": RATE},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
