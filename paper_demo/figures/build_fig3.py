#!/usr/bin/env python3
"""Build Fig. 3 — one question, three answering tracks, real recorded answers.

Left column is the QDCVR protocol, middle the bare agent, right the dense
baseline. The answer text in each column is quoted verbatim from
benchmark-suite/results/ (skill_track_answers.json + track_bc.json); only
elisions are marked. Nothing is paraphrased or invented.

Output: paper_demo/figures/fig3_threeway.png (+ .html)
"""
from __future__ import annotations

import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fig3_threeway.png"
W = 2000

ACCENT = "#b4441f"
INK = "#17171a"
MUTED = "#5c5c66"
OK = "#1d6b45"
NO = "#9b2c1c"

# ── real recorded content ────────────────────────────────────────────────────
QUESTION = ("How does the Transformer compute attention, and why does it "
            "replace recurrence and convolution?")

TRACKS = [
    dict(
        agg=[                 ('questions answered', '10 / 10'),
                 ('gold ranked first', '10 / 10'),
                 ('gate scores', '6-8 / 8'),
                 ('librarian rescues', '2 / 10'),
                 ('mean latency', '2.4 s retrieval'),
                 ('provenance', 'base > doc > part > section'),
                 ('judge score', 'self-adjudicated')],
        key="A", name="QDCVR protocol", tag="this system",
        accent=True,
        metrics=[("content gate", "7/8 \u00b7 fast exit"),
                 ("retrieval", "2.4 s"),
                 ("contract", "gate + not-found")],
        verdict="answered", verdict_kind="ok",
        verdict_note="cited to base \u00b7 document \u00b7 part \u00b7 section",
        body=[
            ("Answer",
             "The Transformer computes attention with multi-head attention: the model "
             "\u201cuses multi-head attention in three different ways\u201d \u2014 in "
             "\u201cencoder-decoder attention\u201d layers the queries come from the previous "
             "decoder layer while the memory keys and values come from the encoder outputs; "
             "the decoder contains self-attention layers where queries, keys and values all "
             "come from the previous decoder layer, with masking so that positions cannot "
             "attend to subsequent positions \u2026 attention replaces recurrence because it "
             "draws global dependencies between any two positions in a single step rather "
             "than through O(n) sequential recurrent operations."),
            ("Citation",
             "[P0] artificial-intelligence__1706.03762 (part 2/2, sec 7 Conclusion; "
             "part 1/2, sec 3.2.3 Applications of Attention) @ \u8ba1\u7b97\u673a\u4e0e"
             "\u4eba\u5de5\u667a\u80fd"),
            ("Blind spots",
             "The precise attention(Q,K,V) formula and d\u2096 scaling were not in the "
             "chunk/head excerpts read; quote them only after re-opening sec 3.2.1."),
        ],
    ),
    dict(
        agg=[                 ('questions answered', '10 / 10'),
                 ('gold cited', '10 / 10 (file level)'),
                 ('gate scores', 'n/a'),
                 ('librarian rescues', 'n/a'),
                 ('mean latency', '78.8 s (35.5-165.3)'),
                 ('provenance', 'file name only'),
                 ('judge score', 'n/a')],
        key="B", name="Bare agent", tag="no index, reads whole files",
        accent=False,
        metrics=[("end-to-end", "48.8 s"), ("tool calls", "1"),
                 ("contract", "free-form")],
        verdict="answered", verdict_kind="ok",
        verdict_note="most detailed, but provenance is a file list only",
        body=[
            ("Answer",
             "The Transformer computes attention by mapping a query and a set of key-value "
             "pairs to an output \u2026 in its \u201cScaled Dot-Product Attention\u201d this is "
             "computed on packed matrices as softmax(QK\u1d40 / sqrt(d\u2096))V, with h parallel "
             "heads (Multi-Head Attention) \u2026 It replaces recurrence and convolution because "
             "recurrent layers require O(n) sequential operations \u2026 while self-attention "
             "connects all positions with a constant number of sequentially executed operations "
             "and a maximum path length of O(1)."),
            ("Citation",
             "files_used: artificial-intelligence__1706.03762__attention-is-all-you-need.md "
             "\u2014 file level, no paragraph or section reference"),
            ("Cost",
             "48.8 s wall clock, one model call; the agent read the whole document itself."),
        ],
    ),
    dict(
        agg=[                 ('questions answered', '8 / 10 (2 abstain)'),
                 ('gold cited', 'not recorded'),
                 ('gate scores', 'n/a'),
                 ('librarian rescues', 'n/a'),
                 ('mean latency', '12.2 s (5.8-28.6)'),
                 ('provenance', 'none (evidence_docs empty)'),
                 ('judge score', 'n/a')],
        key="C", name="Dense baseline", tag="800-char fixed chunks, top-2",
        accent=False,
        metrics=[("retrieval", "0.8 s"), ("answer", "11.8 s"),
                 ("contract", "none")],
        verdict="abstained", verdict_kind="no",
        verdict_note="the evidence pack never contained the answer",
        body=[
            ("Answer",
             "\u201cThe provided evidence is insufficient to answer this question. The "
             "excerpts only discuss English constituency parsing results \u2014 comparing the "
             "Transformer\u2019s performance on WSJ/Penn Treebank against RNN sequence-to-sequence "
             "models and other parsers \u2014 without describing how attention is computed or "
             "explaining why recurrence and convolution are replaced.\u201d"),
            ("Why",
             "2 chunks / 2,854 characters were retrieved, from the parsing-results section: "
             "the 800-character fixed window cut the method section away from the answer "
             "sentence. The abstention is honest \u2014 but nothing in the record shows which "
             "document those chunks came from."),
            ("Provenance",
             "evidence_docs is empty for all ten questions in this track, so the answer "
             "cannot be traced to a source at all."),
        ],
    ),
]


def html_doc() -> str:
    def col(t: dict) -> str:
        acc = ACCENT if t["accent"] else "#8a8a94"
        vcol = OK if t["verdict_kind"] == "ok" else NO
        vmark = "\u2713" if t["verdict_kind"] == "ok" else "\u2717"
        metrics = "".join(
            f'<div class="m"><span class="mk">{k}</span>'
            f'<span class="mv">{v}</span></div>' for k, v in t["metrics"])
        rows = "".join(
            f'<div class="row"><div class="rk">{k}</div>'
            f'<div class="rv">{v}</div></div>' for k, v in t["body"])
        star = ' <span class="star">&#9733;</span>' if t["accent"] else ""
        return f"""
      <section class="col{' acc' if t['accent'] else ''}">
        <header style="border-top-color:{acc}">
          <div class="hrow">
            <div class="kbadge" style="background:{acc}">{t['key']}</div>
            <div>
              <div class="tname">{html.escape(t['name'])}{star}</div>
              <div class="ttag">{html.escape(t['tag'])}</div>
            </div>
          </div>
          <div class="metrics">{metrics}</div>
          <div class="verdict" style="border-color:{vcol};color:{vcol}">
            <span class="vmark">{vmark}</span>{html.escape(t['verdict'])}
          </div>
          <div class="vnote">{html.escape(t['verdict_note'])}</div>
        </header>
        <div class="body">{rows}</div>
      </section>"""

    cols = "".join(col(t) for t in TRACKS)

    # Aggregate strip: the 10-question summary, one block per track, so the
    # figure carries the benchmark numbers that would otherwise need a table.
    agg_cols = ""
    for t in TRACKS:
        rows = "".join(
            f'<div class="ar"><span class="ak">{k}</span>'
            f'<span class="av">{v}</span></div>' for k, v in t["agg"])
        agg_cols += (f'<div class="acol{" acc" if t["accent"] else ""}">'
                     f'<div class="aname">{t["key"]} \u00b7 '
                     f'{html.escape(t["name"])}</div>{rows}</div>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{width:{W}px;background:#fff;color:{INK};
    font-family:"Segoe UI",Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}}
  .head{{border-bottom:2.6px solid {ACCENT};padding-bottom:12px;margin-bottom:16px}}
  .head h1{{font-size:31px;font-weight:700;letter-spacing:-.2px}}
  .head .q{{font-size:20px;color:{MUTED};margin-top:8px;line-height:1.36}}
  .head .q b{{color:{INK}}}
  .head .note{{font-size:16px;color:{MUTED};margin-top:9px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px}}
  .col{{border:1.4px solid #d8d5cd;border-radius:9px;overflow:hidden;
    background:#fff;display:flex;flex-direction:column}}
  .col.acc{{border-color:{ACCENT};box-shadow:0 0 0 2px #f6e2da inset}}
  header{{padding:13px 15px 12px;border-top:5px solid;background:#fbfaf7}}
  .hrow{{display:flex;gap:11px;align-items:center}}
  .kbadge{{width:30px;height:30px;border-radius:7px;color:#fff;font-weight:800;
    font-size:17px;line-height:30px;text-align:center;flex:0 0 auto}}
  .tname{{font-size:20px;font-weight:700}}
  .star{{color:{ACCENT}}}
  .ttag{{font-size:14px;color:{MUTED};margin-top:1px}}
  .metrics{{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px}}
  .m{{display:flex;flex-direction:column}}
  .mk{{font-size:11.5px;letter-spacing:.8px;text-transform:uppercase;color:#8a8a94}}
  .mv{{font-size:16px;font-weight:600;margin-top:1px}}
  .verdict{{margin-top:10px;display:inline-block;border:1.8px solid;
    border-radius:999px;padding:4px 13px;font-size:16px;font-weight:700}}
  .vmark{{margin-right:6px}}
  .vnote{{font-size:13.5px;color:{MUTED};margin-top:6px;line-height:1.3}}
  .body{{padding:6px 15px 14px}}
  .row{{display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #eeebe4}}
  .row:last-child{{border-bottom:none}}
  .rk{{flex:0 0 74px;font-size:13.5px;font-weight:700;color:{ACCENT};
    padding-top:2px}}
  .rv{{font-size:15.5px;line-height:1.44;color:#2b2b31}}
  .agg{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin-top:15px}}
  .acol{{border:1.4px dashed #cfccc4;border-radius:9px;padding:11px 14px;
    background:#fbfaf7}}
  .acol.acc{{border-color:{ACCENT};border-style:solid;background:#fdf1ec}}
  .aname{{font-size:14px;font-weight:700;color:{MUTED};margin-bottom:7px;
    text-transform:uppercase;letter-spacing:.7px}}
  .ar{{display:flex;font-size:15px;line-height:1.55}}
  .ak{{flex:0 0 168px;color:{MUTED}}}
  .av{{font-weight:600}}
  .foot{{margin-top:15px;border-top:1.4px solid #e6e3dc;padding-top:10px;
    display:flex;font-size:14.5px;color:{MUTED}}}
  .foot .r{{margin-left:auto}}
</style></head><body>
  <div class="head">
    <h1>One question, three answering tracks &mdash; recorded answers, quoted verbatim</h1>
    <div class="q"><b>Q.</b> {html.escape(QUESTION)}
      &nbsp;<span style="color:#8a8a94">(BQ01, gold: <i>Attention Is All You Need</i>)</span></div>
    <div class="note">Track&nbsp;A is the QDCVR protocol; Track&nbsp;B a bare agent with no
      index that reads whole files; Track&nbsp;C a dense baseline over 800-character fixed
      chunks. Answer text is reproduced from
      <span style="font-family:Consolas,monospace">benchmark-suite/results/</span> with
      elisions marked &ldquo;&hellip;&rdquo;.</div>
  </div>
  <div class="grid">{cols}</div>
  <div class="agg">{agg_cols}</div>
  <div class="foot">
    <span>The fast track is not the accurate one: the fastest system abstained, and the
      cheapest correct answer carried no citation.</span>
    <span class="r">10-question spot check &middot; per-question traces in the repository</span>
  </div>
</body></html>"""


def main() -> int:
    from playwright.sync_api import sync_playwright
    src = HERE / "fig3_threeway.html"
    src.write_text(html_doc(), encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--hide-scrollbars"])
        pg = b.new_page(viewport={"width": W + 52, "height": 1200},
                        device_scale_factor=2)
        pg.goto(src.as_uri(), wait_until="load")
        pg.wait_for_timeout(900)
        pg.locator("body").screenshot(path=str(OUT))
        h = pg.evaluate("() => document.body.scrollHeight")
        b.close()
    print(f"-> {OUT}  (body {W}x{h} css px @2x)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
