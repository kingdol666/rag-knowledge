#!/usr/bin/env python3
"""Capture English-UI console screenshots for the paper's Figure 2 UI strip.

Logs in, forces the English locale (kb-lang=en), then captures the three
panels that mirror the demo flow:
  1. kb-browser   : /knowledge-base — the collection as an administrator sees it
  2. search       : BQ02 evidence lookup — result cards with scores and addresses
  3. verify       : the Content Verify tab — per-candidate 0-8 gate readings

Output: paper_demo/figures/shots/fig2ui__<name>__viewport.png (1680x1050 @2x)
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER, PASS = "paperdemo", "PaperDemo2026"
HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
Q = "What defines NISQ technology and what is its central limitation?"


def main() -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome",
                               args=["--hide-scrollbars"])
        ctx = br.new_context(viewport={"width": 1680, "height": 1050},
                             device_scale_factor=2.0, locale="en-US")
        pg = ctx.new_page()

        r = pg.request.post(f"{BASE}/api/auth/login",
                            data={"username": USER, "password": PASS})
        sess = r.json()
        pg.goto(BASE + "/login", wait_until="domcontentloaded")
        pg.evaluate("""([t,u]) => { localStorage.setItem('kb_auth_token',t);
            localStorage.setItem('kb_auth_user', JSON.stringify(u));
            localStorage.setItem('kb-lang','en'); }""",
                   [sess["token"], sess.get("user") or {}])

        # 1. knowledge-base browser
        pg.goto(BASE + "/knowledge-base", wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        pg.screenshot(path=str(SHOTS / "fig2ui__kb__viewport.png"))
        print("[ok] kb-browser", flush=True)

        # 2. search results (BQ02)
        pg.goto(BASE + "/knowledge-search", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        box = pg.locator(
            "input[placeholder*='natural language'], input[placeholder*='semantic'], "
            "input[placeholder*='query'], input[placeholder*='Search']"
        ).first
        box.click()
        box.fill(Q)
        pg.wait_for_timeout(400)
        pg.locator("button.ant-btn-primary").first.click()
        print("[search] submitted", flush=True)
        pg.wait_for_timeout(25000)
        try:
            pg.wait_for_load_state("networkidle", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        pg.wait_for_timeout(1500)
        for sel in ("text=Results", "text=Results", "text=Score", "text=score"):
            try:
                pg.locator(sel).first.scroll_into_view_if_needed(timeout=4000)
                break
            except Exception:  # noqa: BLE001
                continue
        pg.screenshot(path=str(SHOTS / "fig2ui__search__viewport.png"))
        print("[ok] search", flush=True)

        # 3. content verify tab
        try:
            pg.locator("text=Content Verify").first.click(timeout=8000)
            pg.wait_for_timeout(4000)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] verify tab click failed: {str(e)[:120]}")
        pg.screenshot(path=str(SHOTS / "fig2ui__verify__viewport.png"))
        body = pg.inner_text("body")
        (SHOTS / "fig2ui__verify__text.txt").write_text(body, encoding="utf-8")
        print("[ok] verify; page text", len(body), "chars", flush=True)
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
