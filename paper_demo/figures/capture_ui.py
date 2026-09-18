#!/usr/bin/env python3
"""Capture real UI screenshots from the running RAG Knowledge platform.

Logs in through the real auth API, injects the session into localStorage, then
visits each page and saves:
  - a full-page shot at 2x device scale (crisp for print)
  - the viewport shot
Output: paper_demo/figures/shots/<name>.png  (+ shots.json manifest)

Usage:  python capture_ui.py [--only name1,name2] [--width 1680] [--height 1050]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER = "paperdemo"
PASS = "PaperDemo2026"
HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

# name -> (path, wait_ms, needs_auth)
PAGES: dict[str, tuple[str, int, bool]] = {
    "login":          ("/login",            1200, False),
    "home":           ("/",                 4000, True),
    "file-system":    ("/file-system",      6000, True),
    "knowledge-base": ("/knowledge-base",   6000, True),
    "knowledge-search": ("/knowledge-search", 5000, True),
    "knowledge-graph": ("/knowledge-graph", 9000, True),
    "settings":       ("/settings",         4000, True),
    "tokens":         ("/tokens",           3500, True),
}


def login(page, base: str) -> dict:
    """Authenticate via the app's own API and persist the session."""
    resp = page.request.post(f"{base}/api/auth/login",
                             data={"username": USER, "password": PASS})
    if not resp.ok:
        raise SystemExit(f"login failed: {resp.status} {resp.text()[:200]}")
    data = resp.json()
    page.goto(base + "/login", wait_until="domcontentloaded")
    page.evaluate(
        """([tok, usr]) => {
             localStorage.setItem('kb_auth_token', tok);
             localStorage.setItem('kb_auth_user', JSON.stringify(usr));
           }""",
        [data["token"], data.get("user") or {}],
    )
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--width", type=int, default=1680)
    ap.add_argument("--height", type=int, default=1050)
    ap.add_argument("--scale", type=float, default=2.0)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    want = [s for s in args.only.split(",") if s] or list(PAGES)
    manifest: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            args=["--force-device-scale-factor=2", "--hide-scrollbars"],
        )
        ctx = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=args.scale,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))

        info = login(page, BASE)
        print(f"[auth] logged in as {info.get('user', {}).get('username')} "
              f"role={info.get('user', {}).get('role')}", flush=True)

        for name in want:
            if name not in PAGES:
                print(f"[skip] unknown page {name}")
                continue
            path, wait, _ = PAGES[name]
            url = BASE + path
            print(f"[shot] {name} -> {url}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(wait)
                # let lazy content settle
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(800)
                vp = SHOTS / f"{name}__viewport.png"
                page.screenshot(path=str(vp), full_page=False)
                fp = SHOTS / f"{name}__full.png"
                page.screenshot(path=str(fp), full_page=True)
                dims = page.evaluate(
                    "() => ({w: document.documentElement.scrollWidth,"
                    " h: document.documentElement.scrollHeight,"
                    " title: document.title})")
                manifest[name] = {"url": url, "viewport": str(vp.name),
                                  "full": str(fp.name), "page": dims}
                print(f"        {dims['w']}x{dims['h']}  title={dims['title'][:60]}",
                      flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"        FAILED: {str(e)[:180]}", flush=True)
                manifest[name] = {"url": url, "error": str(e)[:200]}

        (HERE / "shots.json").write_text(
            json.dumps({"base": BASE, "user": USER, "pages": manifest,
                        "js_errors": errors}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        browser.close()

    print(f"\n-> {HERE / 'shots.json'}")
    if errors:
        print(f"[warn] {len(errors)} JS errors, first: {errors[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
