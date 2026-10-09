#!/usr/bin/env python3
"""Absent-tier probes through the agent layer (hybrid arm, unpinned)."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp8_graded_probes as e8

def main() -> int:
    out = []
    for probe in e8.PROBES:
        if probe["tier"] != "absent":
            continue
        a = e8.agent_layer(probe)
        out.append(a)
        print(f"[agent-absent] {a['qid']}: {a.get('wall_s')}s "
              f"head={(a.get('answer_head') or a.get('error',''))[:120]}", flush=True)
    p = e8.RESULTS / "exp8b_absent_agent.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", p)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
