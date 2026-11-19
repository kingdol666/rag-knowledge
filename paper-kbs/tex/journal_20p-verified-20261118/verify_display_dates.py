#!/usr/bin/env python3
"""Audit rendered article, supplements, and charts for experiment dates."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE = re.compile(
    rf"\b{MONTH}\.?\s+\d{{1,2}}\b|\b\d{{1,2}}\s+{MONTH}\b|"
    r"(?<!\d)20\d{2}[-_/](?:0[1-9]|1[0-2])[-_/](?:0[1-9]|[12]\d|3[01])(?!\d)|"
    r"(?<!\d)20\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?!\d)",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path, help='PDFs; use the PDF render for a Word document')
    args = parser.parse_args()
    failed = False
    for path in args.files:
        text = subprocess.check_output(
            ['pdftotext', '-layout', '-enc', 'UTF-8', str(path.resolve()), '-']
        ).decode('utf-8')
        # The terminal reference list contains publication and access dates,
        # not experimental dates. Check all preceding article text and figures.
        if path.stem in {'main_20p', 'main_20p_review', 'main'}:
            end = re.search(r'^\s*References(?:\s{2,}[^\r\n]*)?\s*$', text, re.MULTILINE)
            if not end:
                raise ValueError(f'Missing References heading: {path}')
            text = text[:end.start()]
        hits = list(DATE.finditer(text))
        for hit in hits:
            near = ' '.join(text[max(0, hit.start() - 35):hit.end() + 35].split())
            print(f'{path.name}: {near}')
        if hits:
            failed = True
        else:
            print(f'{path.name}: no experimental date labels detected')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
