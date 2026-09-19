# Figure 1 — CIKM Demo paper: dense RAG vs. QDCVR protocol (methodology contrast)

Publication-quality flat 2D vector scientific comparison diagram for an ACM CIKM
conference paper (information retrieval / RAG systems). Exact layout spec follows;
ALL text strings must be rendered EXACTLY as written, letter-perfect, in a clean
sans-serif (Helvetica/Arial-like) font. White background #FFFFFF. Flat design, no
photographic elements, no 3D, no drop shadows except none, no gradients, crisp
1.5-2pt strokes. Color code: slate grey #64748B/#CBD5E1 = conventional baseline;
deep teal #0F766E = the QDCVR proposed system; soft red #B4441F = warnings;
dark navy #101826 = bottom results strip. Right-side system outlined in teal as
"the proposed system"; left side visually neutral grey.

## Global layout (landscape 3:2, 1536x1024)

Three horizontal zones: (top, 78% height) two side-by-side process panels with a
small "VS" roundel between them; (bottom, 22% height) one full-width dark results
strip. Generous white margins.

## TOP-LEFT PANEL — "Conventional Dense RAG" (grey theme)

Header bar: light grey fill #EEF2F7, title text "Conventional Dense RAG" in dark
slate, small rounded tag beside it reading "fixed chunks · single pass".
Below, a vertical 3-step pipeline connected by downward grey arrows:
- Step 1 card: numbered grey circle "1", bold title "Fixed 800-character chunking",
  small grey caption "sentences and sections cut mid-thought"
- Step 2 card: circle "2", bold "Single dense retrieval pass", caption "one
  embedding index, top-k chunks"
- Step 3 card: circle "3", bold "4,000-character evidence pack → LLM", caption
  "whatever the top-k chunks contain becomes the context"
Under step 3, three small soft-red warning chips, each with a small ✗ mark:
"answers split across chunks", "no source paths", "no retry on miss".
A grey metric line inside the header area reads: "8 / 10 answered · 2 abstentions".

## TOP-RIGHT PANEL — "QDCVR Knowledge-Base Protocol" (teal theme, the proposed system)

Header bar: teal gradient fill #0F766E→#0D9488, white title "QDCVR Knowledge-Base
Protocol", small translucent white tag "gated · cited · self-checking".
Below, a vertical 5-step pipeline connected by downward teal arrows:
- Step 1: teal circle "1", bold "Content-routed category KBs", caption
  "50 papers → 5 KBs, chunking respects sections"
- Step 2: circle "2", bold "Query rewrite → vector-first recall", caption
  "cross-KB balanced, ~1.6 s"
- Step 3: circle "3", bold "0–8 content gate reads the text", caption
  "pass ≥ 6 exits early"
- Step 4: circle "4", bold "Librarian fallback", caption "runs when gate < 6"
- Step 5: circle "5", bold "Five-section cited answer", caption
  "base / doc / part / § + blind spots"
Small teal gain chips with ✓ marks beside the pipeline: "10 / 10 gold documents",
"0 abstentions", "2/2 gate-fails rescued (this run)".

## CENTER — between the two panels

A small white circle with thick red-brown #B4441F border containing the bold text
"VS", and beneath it a two-line caption "same corpus, same questions — the
protocol stops guessing" in dark red-brown, italic.

## BOTTOM FULL-WIDTH STRIP — dark navy #101826 rounded rectangle, white text

Left cap label in bold white: "BENCHMARK RUN" with small grey sub-line
"50 real papers · 10 questions".
Then four metric groups side by side, each with: bold white metric name on top,
a grey small scope note, a pair of values (grey for dense, bright teal #5EEAD4
for KB), and a thin horizontal bar underneath:
1. "Answered on target" — scope "same 10 questions" — values "dense 8 / 10" vs
   "KB protocol 10 / 10", grey bar 80% vs teal bar 100%.
2. "Unanswered questions" — scope "dense: 2 abstentions · KB: 2 gate-fails
   rescued" — values "dense 2 / 10" vs "KB 0 / 10", grey full bar vs tiny teal bar.
3. "Latency — scopes differ" — scope "dense: end-to-end · KB: retrieval + reads"
   — values "dense 12.2 s" vs "KB 2.4 s", grey full bar vs short teal bar.
4. "Citation granularity" — scope "what a citation resolves to" — values
   "chunk, no path" vs "base/doc/part/§", short grey bar vs full teal bar.

## Text rendering constraints

Every label spelled EXACTLY as quoted above; numbers rendered as digits ("8 / 10",
"12.2 s", "2.4 s", "0–8"); use the section symbol § exactly once in
"base/doc/part/§". No other text, no watermark, no title at the top of the
figure, no legend box. Keep at least 30% whitespace overall; align all cards to a
clean grid; all corners slightly rounded (8-14px radius); consistent 2px card
borders.
