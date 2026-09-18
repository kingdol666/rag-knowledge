#!/usr/bin/env python3
"""Record a real KB-enhanced question in the Claude Chat console.

Turns on KB-enhanced mode (which instructs the agent to run the
/knowledgebase-search QDCVR pipeline), asks one question, and records the whole
agent turn: skill invocation, retrieval steps, and the cited answer.

Output: paper_demo/video/rec/chat/*.webm + shots + the transcript text.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER, PASS = "paperdemo", "PaperDemo2026"
HERE = Path(__file__).resolve().parent
REC = HERE / "rec" / "clips" / "chat"
SHOTS = REC / "shots"
W, H = 1920, 1080

QUESTION = ("What defines NISQ technology and what is its central limitation?")
QUESTION2 = ("Which three independent ontologies subdivide the Gene Ontology, "
             "and what does each cover?")


class Beat:
    def __init__(self, page):
        self.p = page
        self._x, self._y = 960, 540

    def hold(self, ms: int, drift: bool = True) -> None:
        left, step = ms, 90
        while left > 0:
            if drift:
                self._x += 3 if (left // step) % 2 else -3
                self.p.mouse.move(self._x, self._y)
            self.p.wait_for_timeout(min(step, left))
            left -= step

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--engine", default="", help="claude | omp (default: leave as-is)")
    ap.add_argument("--tag", default="nisq")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    if REC.exists():
        shutil.rmtree(REC)  # only the chat clip dir
    SHOTS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome",
                               args=["--force-device-scale-factor=1",
                                     "--hide-scrollbars"])
        ctx = br.new_context(viewport={"width": W, "height": H},
                             record_video_dir=str(REC),
                             record_video_size={"width": W, "height": H},
                             locale="en-US")
        page = ctx.new_page()
        login(page)
        b = Beat(page)

        page.goto(BASE + "/claude-chat", wait_until="domcontentloaded")
        b.hold(7000)
        b.shot("01_chat_idle")

        # engine switch (optional)
        if args.engine:
            try:
                page.locator(".ant-select").first.click()
                b.hold(1200)
                page.locator(
                    f".ant-select-item-option:has-text('{args.engine}')").first.click()
                b.hold(1500)
                print(f"[engine] switched to {args.engine}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] engine switch: {str(e)[:90]}")

        # KB-enhanced toggle
        kb_btn = page.locator("button.kb-btn:not(.soul-btn)").first
        kb_btn.click()
        b.hold(2200)
        b.shot("02_kb_enhanced_on")
        on = kb_btn.get_attribute("class") or ""
        print(f"[kb] toggle class now: {on!r}  active={'active' in on}", flush=True)

        # type the question
        box = page.locator("textarea[placeholder*='Ask Claude'], "
                           "input[placeholder*='Ask Claude']").first
        box.click()
        for ch in args.question:
            box.type(ch, delay=18)
        b.hold(900)
        b.shot("03_question_typed")

        # send
        box.press("Enter")
        print("[chat] sent", flush=True)
        t0 = time.time()
        deadline = t0 + args.timeout
        last_len, stable, shot_at = 0, 0, 0
        while time.time() < deadline:
            page.wait_for_timeout(6000)
            try:
                txt = page.inner_text("body")
            except Exception:  # noqa: BLE001
                continue
            n = len(txt)
            el = int(time.time() - t0)
            if el // 60 != shot_at:
                shot_at = el // 60
                b.shot(f"prog_{el:04d}s")
                print(f"    t={el}s  chars={n}", flush=True)
            if n == last_len:
                stable += 1
            else:
                stable = 0
            last_len = n
            # finished when the transcript stops growing and shows a result
            if stable >= 4 and n > 1500:
                break
        b.hold(2500)
        b.shot("09_answer")

        body = page.inner_text("body")
        (REC / "transcript.txt").write_text(body, encoding="utf-8")
        try:
            page.screenshot(path=str(REC / "chat_full.png"), full_page=True)
        except Exception:  # noqa: BLE001
            pass
        print(f"\n[done] transcript {len(body)} chars, "
              f"{int(time.time()-t0)}s", flush=True)
        page.close()
        ctx.close()
        br.close()

    vids = sorted(REC.glob("*.webm"), key=lambda f: f.stat().st_mtime)
    print("video:", vids[-1].name if vids else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
