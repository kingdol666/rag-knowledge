#!/usr/bin/env python3
"""Capture an interactive retrieval session on the KB Search page.

Runs the real benchmark question BQ02 ("What defines NISQ technology and what is
its central limitation?") through the live web console and screenshots the
result panel, so the paper's figures show an actual retrieval session rather
than a static page.

Output: paper_demo/figures/shots/search__<tag>.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE = "http://127.0.0.1:6789"
USER, PASS = "paperdemo", "PaperDemo2026"
HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

QUERIES = {
    "nisq": "What defines NISQ technology and what is its central limitation?",
    "nisq-zh": "NISQ 量子技术的定义与核心局限是什么？",
    "transformer": "How does the Transformer compute attention, and why does it "
                   "replace recurrence and convolution?",
    "notfound": "How does the Herbert-Moulton collider benchmark quantify "
                "detector drift in particle physics experiments?",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="nisq", choices=list(QUERIES))
    ap.add_argument("--strategy", default="", help="两阶段 / 向量语义 / 关键词")
    ap.add_argument("--wait", type=int, default=25000)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    q = QUERIES[args.tag]
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome",
                               args=["--force-device-scale-factor=2",
                                     "--hide-scrollbars"])
        ctx = br.new_context(viewport={"width": 1680, "height": 1050},
                             device_scale_factor=2.0, locale="zh-CN")
        page = ctx.new_page()

        r = page.request.post(f"{BASE}/api/auth/login",
                              data={"username": USER, "password": PASS})
        sess = r.json()
        page.goto(BASE + "/login", wait_until="domcontentloaded")
        page.evaluate("""([t,u]) => { localStorage.setItem('kb_auth_token',t);
            localStorage.setItem('kb_auth_user', JSON.stringify(u)); }""",
                      [sess["token"], sess.get("user") or {}])

        page.goto(BASE + "/knowledge-search", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # strategy radio (Ant Design renders the label with a space between CJK
        # glyphs, so match on the radio group rather than exact text)
        if args.strategy:
            try:
                page.locator("label.ant-radio-button-wrapper",
                             has_text=args.strategy).first.click(timeout=8000)
                page.wait_for_timeout(600)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] strategy click failed: {str(e)[:100]}")

        # fill the query box
        box = page.locator(
            "input[placeholder*='自然语言语义查询'], input[placeholder*='检索']"
        ).first
        box.click()
        box.fill(q)
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / f"search__{args.tag}__typed.png"))

        # submit (primary Ant button; its label renders as "检 索")
        page.locator("button.ant-btn-primary").first.click()
        print(f"[search] submitted: {q!r}", flush=True)

        # wait for results to settle
        page.wait_for_timeout(args.wait)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(1500)

        # scroll the results region into view
        for sel in ("text=检索结果", "text=结果", "text=相似度", "text=score"):
            try:
                page.locator(sel).first.scroll_into_view_if_needed(timeout=4000)
                break
            except Exception:  # noqa: BLE001
                continue

        page.screenshot(path=str(SHOTS / f"search__{args.tag}__viewport.png"))
        page.screenshot(path=str(SHOTS / f"search__{args.tag}__full.png"),
                        full_page=True)
        body = page.inner_text("body")
        (SHOTS / f"search__{args.tag}__text.txt").write_text(body, encoding="utf-8")
        print(f"[done] captured {args.tag}; page text {len(body)} chars", flush=True)
        print("---- first 900 chars of result text ----")
        print(body[:900])
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
