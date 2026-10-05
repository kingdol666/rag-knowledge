#!/usr/bin/env python3
"""Capture the agent's REAL answer (after kb_* retrieval) from the console's
Claude Chat page, for the paper's Figure 2 screenshot strip.

Flow: login -> kb-lang=en -> /claude-chat -> ask the BQ04 Gene-Ontology
question (the same question as the paper's Scenario 2) -> wait for the stream
to finish -> save viewport + full-page + the last assistant bubble.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER, PASS = "paperdemo", "PaperDemo2026"
SHOTS = Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
Q = "Which three independent ontologies subdivide the Gene Ontology?"


def main() -> int:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
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

        pg.goto(BASE + "/claude-chat", wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        pg.screenshot(path=str(SHOTS / "fig2ui__chat_before.png"))

        ta = pg.locator("textarea").first
        ta.click()
        ta.fill(Q)
        pg.wait_for_timeout(400)
        pg.locator("button:has(.anticon-send)").first.click()
        print("[chat] submitted", flush=True)

        # wait for streaming to start, then finish (stop button lifecycle)
        try:
            pg.locator("button.ant-btn-dangerous").first.wait_for(
                state="visible", timeout=60000)
            print("[chat] streaming started", flush=True)
        except Exception:  # noqa: BLE001
            print("[chat] no stop button seen; polling messages", flush=True)
        for i in range(90):  # up to ~4.5 min
            pg.wait_for_timeout(3000)
            busy = False
            try:
                busy = pg.locator("button.ant-btn-dangerous").first.is_visible()
            except Exception:  # noqa: BLE001
                pass
            n = pg.locator(".msg.assistant").count()
            if not busy and n >= 1 and i >= 2:
                print(f"[chat] done after ~{(i+1)*3}s; assistants={n}", flush=True)
                break
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(SHOTS / "fig2ui__chat__viewport.png"))
        pg.screenshot(path=str(SHOTS / "fig2ui__chat__full.png"), full_page=True)
        try:
            last = pg.locator(".msg.assistant").last
            last.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            last.screenshot(path=str(SHOTS / "fig2ui__chat__answer.png"))
            txt = last.inner_text()
            (SHOTS / "fig2ui__chat__answer.txt").write_text(txt, encoding="utf-8")
            print("[chat] answer chars:", len(txt), flush=True)
            print("---- head ----")
            print(txt[:600], flush=True)
        except Exception as e:  # noqa: BLE001
            print("[warn] answer element capture failed:", str(e)[:150], flush=True)
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
