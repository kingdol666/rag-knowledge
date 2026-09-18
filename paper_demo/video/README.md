# QDCVR demonstration video — CIKM Demo track

**Deliverable: [`qdcvr-demo.mp4`](qdcvr-demo.mp4)** — 1920×1080, H.264 + AAC,
**3:00**, 27 MB, English narration (neural TTS), lower-third captions.

## What the video shows

| # | In | Out | Visual | Narration beat |
|---|---|---|---|---|
| 1 | 0:00 | 0:15 | Title card | The problem: nobody can tell whether a retrieved passage answers the question. |
| 2 | 0:15 | 0:47 | **Live console** — Home → File System → Knowledge Base | 50 real papers, 3.8M characters, 5 content-classified bases; 3 filename overrides; parts keep section headers; tags propagate. |
| 3 | 0:47 | 1:09 | **Live console** — KB Search, NISQ query | BM25 + vector recall over all five bases; gold paper ranks first; hit card names base, document, part; scores broken out by channel. |
| 4 | 1:09 | 1:36 | Artifact card | The 0–8 content gate scores it **7/8**, fast exit; the answer is five sections with sources, confidence and blind spots. |
| 5 | 1:36 | 1:54 | **Live console** — fabricated-paper query | The trap: the top candidate is the BERT paper and it really does contain training-epoch strings. |
| 6 | 1:54 | 2:19 | Artifact card | Gate **1/8** → not-found report; the librarian shelf scan; three probes at 1/8, 1/8, 0/8. |
| 7 | 2:19 | 2:46 | **Live console** — Graph Explorer | 41 MCP tools; gold ranked first 10/10 at 1.6 s; the dense baseline cannot trace its sources; every decision is persisted. |
| 8 | 2:46 | 3:00 | Closing card | Visit the booth; content decides where documents live, reading decides what answers. |

Footage segments are real screen recordings of the running deployment — the NISQ
query returns `quantum-physics__1801.00862` (part 1 of 3, COMBINED 62%), and the
fabricated-paper query returns the BERT paper containing the literal epoch strings
the narration describes. Nothing on screen is mocked.

Card segments reproduce text **verbatim** from
`benchmark-suite/results/skill_track_answers.json` (BQ02) and
`honest_failure_probe.json` (probe P2).

## Pipeline

```bash
cd paper_demo/video

python record_clips.py        # 1. record 4 real browser clips (1920x1080 webm)
python build_video.py --audio # 2. (optional) regenerate narration only
python build_video.py         # 3. cards + captions + pieces + mux -> qdcvr-demo.mp4
```

**Why one file per clip.** Playwright's screencast drops frames while the page is
static, so a single long recording cannot be mapped back to wall-clock time.
Recording one browser context per beat removes that ambiguity — each file is
exactly one segment, and the builder fits it to its narration length.

| File | Role |
|---|---|
| `narration.py` | The script: 8 segments, voice, rate, caption lines, and the verbatim card text. Single source of truth. |
| `record_clips.py` | Logs in, drives the console with paced actions and a background mouse drift (so the recorder keeps sampling), writes `rec/clips/<name>/<hash>.webm` plus still frames. |
| `build_video.py` | TTS per segment → card/title stills → captions → per-segment 1080p pieces → concat → mux. |
| `rec/clips.json` | Wall-clock length of each recorded clip. |
| `build/build_manifest.json` | Per-segment narration length, piece length, voice and rate. |

The still cards are HTML rendered by Playwright, so their styling matches the
paper's figures (same terracotta accent `#b4441f`).

## Verification performed

| Check | Result |
|---|---|
| Duration | **180.7 s (3:00)** — CIKM asks for 3 minutes |
| Resolution / codec | 1920×1080, H.264 + AAC 48 kHz stereo, faststart |
| Decode integrity | full `-f null -` decode: **no errors** |
| Audio level | loudnorm to −16 LUFS → mean **−19.2 dB**, peak **−1.5 dB** |
| Garbled text | none; the one Chinese string on the answer card renders correctly |
| Narration ↔ visual | every segment checked frame-by-frame at its boundary |
| Factual grounding | every number spoken traces to a `benchmark-suite/results/` artifact; BQ02 gate is **7/8** and its vector recall **1.51 s**, matching `skill_track_evidence.json` |

## Before submission

1. Upload `qdcvr-demo.mp4` and replace the placeholder URL
   `https://example.org/qdcvr-demo` in `tex/sec0_abstract.tex`,
   `tex/sec3_demo.tex` and `tex/sec4_backmatter.tex`.
2. The video shows a demo user (`paperdemo`) on the local deployment; if you
   re-record against a different corpus, re-run `record_clips.py` **and**
   `build_video.py` so the on-screen counts keep matching the paper.
3. Card text is generated from the artifacts at build time only for the numbers
   inside the prose — if `skill_track_answers.json` changes, update the
   `CARD_ANSWER` block in `narration.py` to match.
