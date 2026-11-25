# translation-en/ -- English reading overlay for the answer transcript

The HMRS agent and the native DeepRead pipeline ran their own multi-turn
procedures and produced their answers in Chinese. The raw records in
`answers-v3.jsonl` preserve those answers verbatim and are never modified.
Because this audit PDF is rendered with ASCII-safe escaping, the Chinese
text would otherwise appear as unreadable `\uXXXX` escape sequences.

This directory is a **display-only overlay** consumed by
`build_external_baselines_qa.py`:

- `<arm>-<qid>.txt` -- a complete English translation of that record's
  `answer` field, used in place of the raw text when the file exists.
  The translation is faithful: every verbatim English quotation, number,
  formula and provenance note of the original answer is preserved; only
  the narrative Chinese prose was translated by the authors. KB directory
  names inside paths are rendered with their English equivalents.
- `strings-en.json` -- fragment-level glosses applied to every rendered
  string (evidence-index paths, judge rationales, protocol texts), e.g.
  the Chinese top-level KB directory names of the corpus.

Judged scores in `judgments-unified.jsonl` apply to the **original**
answers; the translation is a reading aid and does not alter any judged
material. Anything not covered by this overlay is rendered exactly as
recorded (with ASCII escapes where necessary).

Translated records (nine of 80): hmrs-agent BQ01-BQ05 and BQ08-BQ10,
deepread-native BQ05. hmrs-agent BQ06/BQ07 need no translation (their
original answers are English apart from KB path prefixes, which
`strings-en.json` covers).
