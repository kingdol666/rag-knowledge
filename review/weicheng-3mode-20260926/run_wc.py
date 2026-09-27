# -*- coding: utf-8 -*-
"""Weicheng 3-mode runner: 2 questions x 3 modes via chat API (SSE).

Usage: python run_wc.py [tag ...]   (default: all six, sequential)
Artifacts: <tag>.transcript.txt / <tag>.answer.md / <tag>.status.json
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "three-mode-chat-20260926"))
import run_chat as rc  # noqa: E402
from wc_prompts import PROMPTS  # noqa: E402

rc.OUT = HERE  # artifacts land beside THIS script

if __name__ == "__main__":
    tags = sys.argv[1:] or ["wc-A1", "wc-A2", "wc-B1", "wc-B2", "wc-C1", "wc-C2"]
    for tag in tags:
        print(f"=== RUN {tag} start ===", flush=True)
        try:
            rc.run_chat(PROMPTS[tag], tag, engine="claude",
                        permission_mode="bypassPermissions",
                        max_turns=80, timeout_ms=900_000)
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"RUN_ERROR {tag}: {type(exc).__name__}: {exc}", flush=True)
        print(f"=== RUN {tag} end ===", flush=True)
