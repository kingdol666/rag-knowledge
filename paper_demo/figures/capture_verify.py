#!/usr/bin/env python3
"""Capture the content-verification panel of a live search session.

After submitting the BQ02 query, click the "内容验证" tab and screenshot the
adjudication panel (per-candidate read + score), which is the UI face of the
0--8 content gate.
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
                               args=["--force-device-scale-factor=2",
                                     "--hide-scrollbars"])
        ctx = br.new_context(viewport={"width": 1680, "height": 1050},
                             device_scale_factor=2.0, locale="zh-CN")
        pg = ctx.new_page()
        r = pg.request.post(f"{BASE}/api/auth/login",
                            data={"username": USER, "password": PASS})
        s = r.json()
        pg.goto(BASE + "/login", wait_until="domcontentloaded")
        pg.evaluate("""([t,u])=>{localStorage.setItem('kb_auth_token',t);
            localStorage.setItem('kb_auth_user',JSON.stringify(u));}""",
                    [s["token"], s.get("user") or {}])
        pg.goto(BASE + "/knowledge-search", wait_until="domcontentloaded")
        pg.wait_for_timeout(4500)
        pg.locator("input[placeholder*='自然语言语义查询']").first.fill(Q)
        pg.locator("button.ant-btn-primary").first.click()
        print("[search] submitted", flush=True)
        pg.wait_for_timeout(28000)

        # click the 内容验证 tab
        clicked = False
        for sel in ("text=内容验证", "[class*='verify']", "text=关闭验证"):
            try:
                pg.locator(sel).first.click(timeout=6000)
                clicked = True
                print(f"[tab] clicked {sel!r}", flush=True)
                break
            except Exception:  # noqa: BLE001
                continue
        if not clicked:
            print("[warn] 内容验证 tab not found; dumping tab-like elements")
            for i in range(pg.locator("div[class*='tab'], span[class*='tab']").count()):
                t = pg.locator("div[class*='tab'], span[class*='tab']").nth(i).inner_text()[:40]
                if t.strip():
                    print(f"   tab[{i}] {t!r}")

        pg.wait_for_timeout(9000)
        try:
            pg.wait_for_load_state("networkidle", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        pg.wait_for_timeout(2000)
        pg.screenshot(path=str(SHOTS / "search__verify__viewport.png"))
        pg.screenshot(path=str(SHOTS / "search__verify__full.png"),
                      full_page=True)
        (SHOTS / "search__verify__text.txt").write_text(
            pg.inner_text("body"), encoding="utf-8")
        print("[done]", flush=True)
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
