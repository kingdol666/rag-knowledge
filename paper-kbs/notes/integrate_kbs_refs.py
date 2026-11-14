"""Integrate the verified KBS literature pack into the active submission's BibTeX.

Active manuscript: paper-kbs/tex/journal_20p/main_20p.tex
    \\bibliography{refs,refs_new_verified}

Rules enforced here (all evidence-driven, no guessing):
  1. Drop keys whose DOI already exists in the manuscript's two .bib files
     (yang2025comprehen / ghali2025enhancing are already cited under other keys).
  2. Drop every `note` field: the pack's notes contain local file paths and
     must not appear in a submission reference list.
  3. Transliterate non-ASCII author names into LaTeX accents so pdflatex +
     utf8 inputenc cannot break on U+2010 / dotless i / cedilla etc.
  4. Idempotent: refuse to append twice (marker line).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repository root
PACK = ROOT / "paper-kbs" / "reference" / "kbs" / "kbs_refs.bib"
TEX = ROOT / "paper-kbs" / "tex" / "journal_20p"
TARGET = TEX / "refs.bib"
MARKER = "%% KBS-2026-11-14: verified journal references (integrate_kbs_refs.py)"

ACCENTS = {
    "\u00e1": "{\\'a}", "\u00e9": "{\\'e}", "\u00ed": "{\\'i}",
    "\u00f3": "{\\'o}", "\u00fa": "{\\'u}",
    "\u00f1": "{\\~n}", "\u00e7": "{\\c{c}}", "\u015f": "{\\c{s}}",
    "\u00f6": "{\\\"o}", "\u00fc": "{\\\"u}", "\u00d6": "{\\\"O}",
    "\u0131": "{\\i}",
    "\u2010": "-", "\u2013": "--", "\u2014": "---", "\u2019": "'",
}


def keys_and_dois(paths: list[Path]) -> tuple[set[str], set[str]]:
    keys, dois = set(), set()
    for p in paths:
        s = p.read_text(encoding="utf-8")
        keys |= set(re.findall(r"^@\w+\{([^,]+),", s, re.M))
        dois |= {d.lower() for d in re.findall(r"\bdoi\s*=\s*\{([^}]+)\}", s)}
    return keys, dois


def split_entries(text: str) -> list[tuple[str, str]]:
    """Return (key, full entry text) for each @...{...} block."""
    starts = [m.start() for m in re.finditer(r"^@\w+\{", text, re.M)]
    out = []
    for i, st in enumerate(starts):
        en = starts[i + 1] if i + 1 < len(starts) else len(text)
        block = text[st:en].rstrip()
        key = re.match(r"^@\w+\{([^,]+),", block).group(1)
        out.append((key, block))
    return out


def clean(block: str) -> str:
    lines = [ln for ln in block.splitlines()
             if not re.match(r"^\s*note\s*=", ln, re.I)]
    s = "\n".join(lines)
    # trailing comma hygiene after removing the last field (note used to be last)
    s = re.sub(r",(\s*\n\s*\})", r"\1", s)
    return "".join(ACCENTS.get(ch, ch) for ch in s)


old_keys, old_dois = keys_and_dois([TEX / "refs.bib", TEX / "refs_new_verified.bib"])
if MARKER in TARGET.read_text(encoding="utf-8"):
    raise SystemExit("[skip] references already integrated; refusing to duplicate")

entries = split_entries(PACK.read_text(encoding="utf-8"))
kept, dropped = [], []
for key, block in entries:
    doi_m = re.search(r"\bdoi\s*=\s*\{([^}]+)\}", block)
    doi = doi_m.group(1).lower() if doi_m else ""
    if key in old_keys or (doi and doi in old_dois):
        dropped.append((key, doi, "already in submission bib"))
        continue
    kept.append((key, clean(block)))

non_ascii_left = sorted({c for k, b in kept for c in b if ord(c) > 127})
if non_ascii_left:
    raise SystemExit(f"[abort] unmapped non-ASCII characters: {non_ascii_left}")

body = TARGET.read_text(encoding="utf-8").rstrip()
body += "\n\n" + MARKER + "\n%% " + str(len(kept)) + " entries; two DOI duplicates removed; notes stripped.\n\n"
body += "\n\n".join(b for _, b in kept) + "\n"
TARGET.write_text(body, encoding="utf-8")

report = {
    "target": str(TARGET.relative_to(ROOT)).replace("\\", "/"),
    "source": str(PACK.relative_to(ROOT)).replace("\\", "/"),
    "before_total_defined": len(old_keys),
    "integrated": [k for k, _ in kept],
    "dropped": [{"key": k, "doi": d, "reason": r} for k, d, r in dropped],
    "after_total_defined": len(old_keys) + len(kept),
}
(Path(__file__).resolve().parent / "kbs_integration_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"[bib] integrated {len(kept)} entries into {TARGET.name}")
print(f"[bib] dropped {len(dropped)} DOI duplicates: {[d[0] for d in dropped]}")
print(f"[bib] defined keys now: {report['after_total_defined']}")
print("[bib] note fields stripped; non-ASCII mapped to LaTeX accents")
