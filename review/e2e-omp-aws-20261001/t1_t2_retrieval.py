"""T1+T2: chat API x OMP engine — found-question hit and honest refusal."""
from __future__ import annotations

import sys
from e2e_lib import KB_CS, chat, refusal

# T1 — found: InstructDS (arXiv 2310.10981) lives in the CS base.
t1 = chat(
    "How does InstructDS generate high-quality query-based dialogue "
    "summaries? Answer only from the knowledge bases, and name the source "
    "document you used.",
    kb_ids=[KB_CS], tag="t1_omp_found")
a1 = t1.get("answer") or ""
t1_pass = (t1.get("http") == 200 and ("instructds" in a1.lower())
           and not refusal(a1))

# T2 — refusal: out-of-corpus physics question, pinned to the CS base.
t2 = chat(
    "How does the Herbert-Moulton collider benchmark quantify detector "
    "drift in particle physics experiments? Answer only from the knowledge "
    "bases.",
    kb_ids=[KB_CS], tag="t2_omp_refusal")
a2 = t2.get("answer") or ""
t2_pass = (t2.get("http") == 200 and refusal(a2)
           and "herbert-moulton" not in a2.lower().replace("herbert-moulton", "", 0))

print("T1 pass:", t1_pass, "| wall:", t1.get("wall_s"), "s | turns:",
      t1.get("num_turns"), "| cost:", t1.get("cost_usd"))
print("T1 answer head:", a1[:220].replace(chr(10), " "))
print("T2 pass:", t2_pass, "| wall:", t2.get("wall_s"), "s | turns:",
      t2.get("num_turns"))
print("T2 answer head:", a2[:220].replace(chr(10), " "))
verdict = {"t1_pass": t1_pass, "t2_pass": t2_pass}
import json
from pathlib import Path
Path(__file__).with_name("t1_t2_verdict.json").write_text(
    json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")
sys.exit(0 if (t1_pass and t2_pass) else 2)
