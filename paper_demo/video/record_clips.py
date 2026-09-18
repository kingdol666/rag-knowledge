#!/usr/bin/env python3
"""Record each demo clip as its own video file.

Playwright's screencast drops frames while the page is static, so a single long
recording cannot be mapped back to wall-clock time. Recording one browser
context per clip removes that ambiguity: each file is exactly one beat of the
demo, and build_video.py fits it to its narration length.

Output: rec/clips/<name>.webm  +  rec/clips.json (durations)
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER, PASS = "paperdemo", "PaperDemo2026"
HERE = Path(__file__).resolve().parent
REC = HERE / "rec"
CLIPS = REC / "clips"
SHOTS = REC / "shots"

W, H = 1920, 1080
QUERY_NISQ = "What defines NISQ technology and what is its central limitation?"
QUERY_FAKE = ("What did the paper 'Spectral Tuning for Low-Resource Odor "
              "Recognition' report about training epochs?")


def search_input(page):
    for sel in ("input[placeholder*='Enter search query']",
                "input[placeholder*='自然语言语义查询']"):
        loc = page.locator(sel)
        if loc.count():
            return loc.first
    raise RuntimeError("search input not found")


def wait_results(page, timeout_ms: int = 90000) -> bool:
    import re
    pat = re.compile(r"(?:Results|检索结果)\s*[:：]\s*(\d+)")
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        try:
            txt = page.inner_text("body")
        except Exception:  # noqa: BLE001
            txt = ""
        m = pat.search(txt)
        if m and int(m.group(1)) > 0:
            return True
        page.wait_for_timeout(1000)
    return False


class Beat:
    """Paced actions plus a background mouse drift so the recorder keeps sampling."""

    def __init__(self, page):
        self.p = page
        self._x, self._y = 960, 540

    def hold(self, ms: int, drift: bool = True) -> None:
        """Wait, moving the pointer a little so frames keep being emitted."""
        step = 90
        left = ms
        while left > 0:
            if drift:
                self._x += 3 if (left // step) % 2 else -3
                self.p.mouse.move(self._x, self._y)
            self.p.wait_for_timeout(min(step, left))
            left -= step

    def glide(self, px: int, steps: int = 24, pause: int = 30) -> None:
        for _ in range(steps):
            self.p.mouse.wheel(0, px / steps)
            self.p.wait_for_timeout(pause)

    def shot(self, name: str) -> None:
        self.p.screenshot(path=str(SHOTS / f"{name}.png"))


def login(page) -> None:
    r = page.request.post(f"{BASE}/api/auth/login",
                          data={"username": USER, "password": PASS})
    s = r.json()
    page.goto(BASE + "/login", wait_until="domcontentloaded")
    page.evaluate("""([t,u])=>{localStorage.setItem('kb_auth_token',t);
        localStorage.setItem('kb_auth_user',JSON.stringify(u));}""",
                  [s["token"], s.get("user") or {}])
    page.wait_for_timeout(600)


# ── the four recorded beats ──────────────────────────────────────────────────

def clip_org(page, b: Beat) -> None:
    page.goto(BASE + "/", wait_until="domcontentloaded")
    b.hold(4200); b.shot("01_home")
    b.glide(520); b.hold(1500)

    page.goto(BASE + "/file-system", wait_until="domcontentloaded")
    b.hold(4000); b.shot("02_filesystem")
    try:
        page.locator(".ant-tree-treenode").first.click(timeout=5000)
        b.hold(2200)
    except Exception:  # noqa: BLE001
        pass
    b.shot("03_tree_open")
    b.glide(240); b.hold(1500)

    page.goto(BASE + "/knowledge-base", wait_until="domcontentloaded")
    b.hold(4200); b.shot("04_kb_docs")
    b.glide(560); b.hold(2200)
    b.shot("05_kb_parts")
    b.glide(300); b.hold(1800)


def clip_search(page, b: Beat) -> None:
    page.goto(BASE + "/knowledge-search", wait_until="domcontentloaded")
    b.hold(3600); b.shot("06_search_empty")
    el = search_input(page)
    el.click()
    el.type(QUERY_NISQ, delay=40)
    b.hold(1200)
    page.locator("button.ant-btn-primary").first.click()
    wait_results(page)
    b.hold(3600); b.shot("07_search_results")
    b.glide(280); b.hold(2600)
    b.shot("08_search_hit")
    b.hold(2200)


def clip_notfound(page, b: Beat) -> None:
    page.goto(BASE + "/knowledge-search", wait_until="domcontentloaded")
    b.hold(3000)
    el = search_input(page)
    el.click()
    el.type(QUERY_FAKE, delay=34)
    b.hold(1200)
    page.locator("button.ant-btn-primary").first.click()
    wait_results(page)
    b.hold(4000); b.shot("09_notfound_results")
    b.glide(400); b.hold(3000)
    b.shot("10_notfound_scroll")
    b.hold(2000)


def clip_graph(page, b: Beat) -> None:
    page.goto(BASE + "/knowledge-graph", wait_until="domcontentloaded")
    b.hold(6000); b.shot("11_graph")
    page.mouse.move(940, 620)
    b.hold(1200)
    page.mouse.move(1040, 690, steps=24)
    b.hold(1200)
    page.mouse.click(1040, 690)
    b.hold(3000); b.shot("12_graph_node")
    b.glide(240); b.hold(2600)


BEATS = {"org": clip_org, "search": clip_search,
         "notfound": clip_notfound, "graph": clip_graph}


def main() -> int:
    from playwright.sync_api import sync_playwright

    only = sys.argv[1:] or list(BEATS)
    if REC.exists():
        shutil.rmtree(REC)
    CLIPS.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)

    meta: dict[str, dict] = {}
    with sync_playwright() as p:
        br = p.chromium.launch(
            channel="chrome",
            args=["--force-device-scale-factor=1", "--hide-scrollbars",
                  "--disable-features=Translate"],
        )
        for name in only:
            out_dir = CLIPS / name
            out_dir.mkdir(parents=True, exist_ok=True)
            ctx = br.new_context(
                viewport={"width": W, "height": H},
                record_video_dir=str(out_dir),
                record_video_size={"width": W, "height": H},
                locale="en-US",
            )
            page = ctx.new_page()
            login(page)
            b = Beat(page)
            t0 = time.time()
            print(f"[clip] {name} ...", flush=True)
            BEATS[name](page, b)
            wall = round(time.time() - t0, 2)
            page.close()
            ctx.close()
            vids = sorted(out_dir.glob("*.webm"))
            v = vids[0] if vids else None
            meta[name] = {"wall": wall, "video": str(v) if v else None}
            print(f"        wall={wall}s file={v.name if v else None}", flush=True)
        br.close()

    (REC / "clips.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print(f"\n-> {REC / 'clips.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
