"""Browser end-to-end test for the QDCVR benchmark dashboard.

Drives a real Chromium against the running Nuxt front end (default
http://127.0.0.1:3001) and the FastAPI backend behind it, exercising what a
user actually does: open the page, upload files, tune a per-algorithm
parameter, run a comparison, read the results.

Usage
-----
    python e2e_ui_test.py                       # headless
    python e2e_ui_test.py --headed --slow 400   # watch it happen
    python e2e_ui_test.py --ui http://127.0.0.1:3001 --api http://127.0.0.1:8800
    python e2e_ui_test.py --screenshot out.png

Exit code 0 means every check passed.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.request
import uuid

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright  # noqa: E402

_checks: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _checks.append((ok, name, detail))
    print(f"  {'\u2713' if ok else '\u2717'} {name}" + (f"  — {detail}" if detail else ""))
    return ok


def seed_via_api(api: str, docs: list[dict]) -> None:
    """Put a known corpus in place through the API (not the UI)."""
    urllib.request.urlopen(urllib.request.Request(
        f"{api}/api/documents", method="DELETE"), timeout=30).read()
    body = json.dumps(docs).encode()
    urllib.request.urlopen(urllib.request.Request(
        f"{api}/api/documents/batch", data=body, method="POST",
        headers={"Content-Type": "application/json"}), timeout=60).read()


SEED = [
    {"id": "battery-thermal", "title": "Battery Thermal Management with PCM",
     "domain": "Energy-Batteries",
     "content": "Phase change materials absorb latent heat while melting and hold a "
                "battery pack near their melting point. Paraffin wax with a 40 to 50 "
                "Celsius melting point is used for lithium-ion battery thermal "
                "management. Hybrid designs combine PCM with liquid cooling channels."},
    {"id": "battery-soc", "title": "GNN for Battery State of Charge Estimation",
     "domain": "Energy-Batteries",
     "content": "Graph neural networks estimate battery state of charge from voltage, "
                "current and temperature sequences. Cells are modelled as graph nodes "
                "and a spatio-temporal GNN captures cell-to-cell variation. Mean "
                "absolute error stays under 1.5 percent."},
    {"id": "pneumonia-cnn", "title": "CNN for Chest X-Ray Pneumonia Detection",
     "domain": "Biomedical-Engineering",
     "content": "Convolutional networks detect pneumonia in chest radiographs. "
                "DenseNet-121 pretrained on ImageNet is fine-tuned on ChestX-ray14 "
                "and reaches an AUROC of 0.85, matching radiologist performance."},
]

UPLOAD = [
    ("quantum-notes.md",
     b"# Quantum error correction\n\nSurface codes encode a logical qubit across a "
     b"lattice of physical qubits and correct errors by measuring stabilisers "
     b"without collapsing the encoded state.\n"),
    ("perovskite.txt",
     b"Perovskite solar cells use a hybrid organic-inorganic lead halide absorber. "
     b"Power conversion efficiency rose from 3.8 percent in 2009 past 25 percent, "
     b"limited by moisture instability.\n"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", default="http://127.0.0.1:3001")
    parser.add_argument("--api", default="http://127.0.0.1:8800")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow", type=int, default=0, help="slow-motion ms per action")
    parser.add_argument("--screenshot", default="")
    args = parser.parse_args()

    print("=" * 78)
    print(f"QDCVR dashboard — browser end-to-end test  ({args.ui} -> {args.api})")
    print("=" * 78)

    print("\n[0] Seed a known corpus through the API")
    try:
        seed_via_api(args.api, SEED)
        check("corpus seeded", True, f"{len(SEED)} documents")
    except Exception as exc:
        check("corpus seeded", False, f"{type(exc).__name__}: {exc}")
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed,
                                             slow_mo=args.slow or None)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text)
                if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        # ── 1. load ─────────────────────────────────────────────────────────
        print("\n[1] Load the dashboard")
        page.goto(args.ui, wait_until="networkidle", timeout=90_000)
        check("page loads", page.title() != "", page.title())

        page.wait_for_selector(".method-checkbox label", timeout=60_000)
        method_labels = page.locator(".method-checkbox label")
        count = method_labels.count()
        check("algorithm registry reached the browser", count >= 8,
              f"{count} algorithms rendered")

        page.wait_for_function(
            "() => document.querySelectorAll('.kpi-value')[0]?.textContent?.trim() !== '--'",
            timeout=60_000)
        doc_kpi = page.locator(".kpi-value").first.inner_text().strip()
        check("KPI shows the seeded document count", doc_kpi == str(len(SEED)),
              f"documents={doc_kpi}")

        status_text = page.locator(".kpi-card.qdcvr .kpi-value").inner_text()
        check("backend status reads Up", "Up" in status_text, status_text.strip())

        # ── 2. parameter panel ──────────────────────────────────────────────
        print("\n[2] Per-algorithm parameter panel")
        panels = page.locator(".param-group")
        check("a parameter panel exists per selected algorithm", panels.count() >= 3,
              f"{panels.count()} panels")
        # BM25 must expose k1 and b as editable number inputs.
        bm25 = page.locator(".param-group", has=page.locator("text=BM25")).first
        check("BM25 exposes numeric parameters (k1, b)",
              bm25.locator("input[type=number]").count() >= 3,
              f"{bm25.locator('input[type=number]').count()} numeric inputs")
        check("BM25 declares k1 and b by name",
              page.locator("#bm25-k1").count() == 1 and page.locator("#bm25-b").count() == 1)
        page.fill("#bm25-k1", "0.2")
        page.wait_for_timeout(200)
        changed = page.locator(".param-field.param-changed").count()
        check("editing a parameter marks it as changed", changed >= 1,
              f"{changed} changed field(s)")
        check("a reset control appears once a parameter is changed",
              bm25.locator("button", has_text="reset").count() >= 1)

        # Out-of-range input must be flagged, and clamped on commit — the API
        # would otherwise reject that method with a named error.
        page.fill("#bm25-k1", "99")
        page.wait_for_timeout(200)
        check("an out-of-range value is flagged in the UI",
              page.locator(".param-field.param-invalid").count() >= 1)
        check("an out-of-range value raises a warning banner",
              page.locator(".alert-warn").count() >= 1)
        page.locator("#bm25-b").focus()          # blur commits the clamp
        page.wait_for_timeout(300)
        clamped = page.input_value("#bm25-k1")
        check("the value is clamped into range on commit", float(clamped) <= 3.0,
              f"k1={clamped}")
        page.fill("#bm25-k1", "1.2")
        page.locator("#bm25-b").focus()
        page.wait_for_timeout(200)

        # ── 3. upload through the UI ────────────────────────────────────────
        print("\n[3] Upload files through the UI")
        page.click("button.tab:has-text('Corpus')")
        page.wait_for_selector(".dropzone", timeout=30_000)
        pages_input = page.locator("input[type=file]")
        pages_input.set_input_files([
            {"name": name, "mimeType": "text/plain", "buffer": data}
            for name, data in UPLOAD
        ])
        page.wait_for_selector(".alert-ok, .alert-warn", timeout=120_000)
        report = page.locator(".alert-ok, .alert-warn").first.inner_text().strip()
        check("upload reports success for every file", "2 file(s) indexed" in report, report)
        rows = page.locator(".doc-row")
        check("uploaded files appear in the corpus list", rows.count() >= len(UPLOAD),
              f"{rows.count()} rows")

        page.click("button.tab:has-text('Benchmark')")
        page.wait_for_selector(".method-checkbox label", timeout=30_000)

        # ── 4. run a comparison ─────────────────────────────────────────────
        print("\n[4] Run a comparison from the browser")
        page.fill("textarea", "battery thermal management phase change material")
        total_methods = page.locator(".method-checkbox label").count()
        # Keep BM25 + Dense only. Anchored so "Hybrid (BM25+Dense)" is not matched.
        keep = ("BM25", "Dense")
        for label in page.locator(".method-checkbox label").all():
            text = (label.inner_text() or "").strip()
            want = any(text.startswith(name) for name in keep)
            is_on = "checked" in (label.get_attribute("class") or "")
            if want != is_on:
                label.click()
        page.wait_for_timeout(300)
        selected_now = page.locator(".method-checkbox label.checked").count()
        check("the user can narrow the method selection", 0 < selected_now < total_methods,
              f"{selected_now} of {total_methods} selected")

        page.click("button:has-text('Compare + metrics')")
        page.wait_for_selector(".comparison-table tbody tr", timeout=180_000)
        table_rows = page.locator(".comparison-table tbody tr")
        check("comparison table renders a row per method", table_rows.count() >= 2,
              f"{table_rows.count()} rows")
        check("the comparison covers exactly the selected methods",
              table_rows.count() == selected_now,
              f"{table_rows.count()} rows vs {selected_now} selected")
        first_row = table_rows.first.inner_text()
        check("comparison row carries latency and score columns",
              len(first_row.split()) >= 4, first_row.replace("\n", " ")[:110])
        errored = [row.inner_text() for row in table_rows.all()
                   if "error" in row.inner_text().lower()]
        check("no method reported an error in the comparison", not errored,
              " | ".join(e.replace("\n", " ")[:70] for e in errored[:2]))

        cards = page.locator(".result-card")
        check("a result card renders per algorithm", cards.count() >= 2,
              f"{cards.count()} cards")
        snippets = page.locator(".result-snippet")
        check("result cards show retrieved passages", snippets.count() >= 1,
              f"{snippets.count()} snippets")
        if snippets.count():
            top = snippets.first.inner_text().lower()
            check("the top passage is on-topic for the query",
                  any(word in top for word in ("phase change", "thermal", "battery", "pcm")),
                  top[:90])

        overline = page.locator(".metric-pill").all_inner_texts()
        check("result metadata pills render (score / params / provenance)",
              any("score" in t for t in overline) and
              any("REAL-CODE" in t or "PROJECT" in t for t in overline),
              f"{len(overline)} pills")

        check("no console errors during the run",
              not console_errors, "; ".join(console_errors[:2])[:160])

        # ── 5. ground truth -> real metrics ─────────────────────────────────
        print("\n[5] Ground truth switches on real IR metrics")
        page.fill("input[placeholder*='comma-separated']", "battery-thermal")
        page.click("button:has-text('Compare + metrics')")
        page.wait_for_timeout(1500)
        headers = (page.locator(".comparison-table thead").inner_text() or "").upper()
        check("metric columns appear once ground truth is supplied",
              "NDCG@10" in headers and "MRR" in headers and "P@5" in headers,
              headers.replace("\n", " ")[:110])
        page.wait_for_selector(".alert-ok", timeout=30_000)
        note = page.locator(".alert-ok").first.inner_text()
        check("the UI states that metrics were computed against ground truth",
              "ground truth" in note.lower(), note.strip()[:110])

        # ── 6. API tab ──────────────────────────────────────────────────────
        print("\n[6] API tab documents the surface")
        page.click("button.tab:has-text('API')")
        page.wait_for_selector(".comparison-table", timeout=30_000)
        api_rows = page.locator(".comparison-table tbody tr")
        check("API tab lists the endpoints", api_rows.count() >= 12,
              f"{api_rows.count()} endpoints")
        curl = page.locator(".result-snippet").first.inner_text()
        check("API tab shows a runnable per-algorithm curl example",
              "params" in curl and "bm25" in curl)

        if args.screenshot:
            page.click("button.tab:has-text('Benchmark')")
            page.wait_for_timeout(600)
            page.screenshot(path=args.screenshot, full_page=True)
            print(f"\n  screenshot -> {args.screenshot}")

        browser.close()

    passed = sum(1 for ok, _, _ in _checks if ok)
    failed = len(_checks) - passed
    print("\n" + "=" * 78)
    print(f"RESULT: {passed} passed, {failed} failed, {len(_checks)} checks")
    if failed:
        print("\nFailures:")
        for ok, name, detail in _checks:
            if not ok:
                print(f"  \u2717 {name}" + (f"  — {detail}" if detail else ""))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
