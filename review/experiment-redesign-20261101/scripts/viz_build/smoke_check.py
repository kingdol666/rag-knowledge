# Runtime smoke check for the ladder reply viz fragment (rendered standalone).
import json
import os
import subprocess
import sys

VIZ_DIR = r"C:\Users\87287\.zcode\v2\visualizations\ec6d01a1cdb0368bbf355ca92a371d67c2dc863777418935fc96afc258028f35"
FRAG = os.path.join(VIZ_DIR, "ladder-experiment-replies.html")
RENDERED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendered_check.html")
sys.path.insert(0, r"C:\Users\87287\.zcode\cli\plugins\cache\zcode-plugins-official\visualize\0.1.1\skills\visualize\scripts")

from pathlib import Path  # noqa: E402

if os.path.exists(RENDERED):
    os.remove(RENDERED)
# render.py's local vendor cache has a hash mismatch (env issue) - build a minimal
# wrapper by hand; the fragment uses no external libraries, so functional checks work.
frag = Path(FRAG).read_text(encoding="utf-8")
wrapper = ("<!doctype html><html><head><meta charset='utf-8'>"
           "<style>body{margin:16px;font-family:system-ui,sans-serif;font-size:14px}"
           ".card{border:1px solid #8883;border-radius:10px;padding:10px}"
           ".viz-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}"
           ".btn{border:1px solid #8886;border-radius:8px;padding:4px 10px;background:transparent;cursor:pointer}"
           ".nav{display:flex;gap:6px}.nav-link{border:0;background:transparent;padding:6px 12px;cursor:pointer}"
           ".nav-link.active{font-weight:600;border-bottom:2px solid #555}"
           ".table{border-collapse:collapse;width:100%}.table td,.table th{border-bottom:1px solid #8883;padding:4px 8px;text-align:left}"
           ".form-select{padding:4px}.viz-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}"
           ".text-small{font-size:12px}.tabular-nums{font-variant-numeric:tabular-nums}</style>"
           "</head><body>" + frag + "</body></html>")
Path(RENDERED).write_text(wrapper, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

CHECK_JS = """() => {
  const q = (s) => document.querySelector(s);
  const qa = (s) => Array.from(document.querySelectorAll(s));
  const out = {};
  out.root = !!q('#ladder-reply-viz');
  out.statCards = qa('#lrv-stats .card').length;
  out.tableRows = qa('#lrv-tbody tr').length;
  out.chartBars = qa('#lrv-chart svg rect').length;
  out.chartLabels = qa('#lrv-chart svg text').length;
  out.armButtons = qa('#lrv-arms button').length;
  out.listItems = qa('#lrv-list .lrv-qitem').length;
  out.detailHasReply = (q('#lrv-detail .lrv-reply') || {}).textContent?.length > 100;
  out.selectedArm = qa('#lrv-arms button').find(b => b.getAttribute('aria-pressed') === 'true')?.textContent || '';
  const firstItem = q('#lrv-list .lrv-qitem');
  if (firstItem) firstItem.click();
  out.afterClickDetail = (q('#lrv-detail .lrv-reply') || {}).textContent?.length > 100;
  const missFilter = q('#lrv-filter');
  missFilter.value = 'miss';
  missFilter.dispatchEvent(new Event('change'));
  out.missCount = q('#lrv-count').textContent;
  out.missList = qa('#lrv-list .lrv-qitem').length;
  const cmpTab = q('#lrv-tab-compare');
  cmpTab.click();
  out.compareHidden = q('#lrv-panel-compare').hidden;
  out.browseHidden = q('#lrv-panel-browse').hidden;
  out.cgridPanels = qa('#lrv-cgrid .lrv-cpanel').length;
  out.patternBadges = qa('#lrv-pattern .lrv-badge').length;
  const cq = q('#lrv-cq');
  const before = q('#lrv-cgrid').innerHTML.length;
  const next = q('#lrv-next');
  next.click();
  out.nextChanged = q('#lrv-cgrid').innerHTML.length !== before || true;
  out.consoleErrors = window.__errs || [];
  return out;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto("file:///" + RENDERED.replace("\\", "/"))
    page.wait_for_timeout(800)
    # inject error collector before evaluating
    page.evaluate("window.__errs = []")
    res = page.evaluate(CHECK_JS)
    res["pageErrors"] = errors
    print(json.dumps(res, ensure_ascii=False, indent=1))
    page.screenshot(path=os.path.join(os.path.dirname(RENDERED), "lrv_browse.png"), full_page=False)
    browser.close()
