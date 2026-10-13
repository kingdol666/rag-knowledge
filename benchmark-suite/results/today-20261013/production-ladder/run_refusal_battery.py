#!/usr/bin/env python3
"""Refusal battery — 3 modes × 6 questions (cm4-cm9) via the official chat API.
Benchmark driver: persists machine-verified ground truth into the run dir, runs
chat_mode_arms.run_all (arm JSONs + chatmodes.json + CHAT-MODES-COMPARE.md)."""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "benchmark-suite"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "experiments"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

from experiments import chat_mode_arms as cma  # noqa: E402
from lib import new_run_dir  # noqa: E402

GROUND_TRUTH = """# Ground truth (machine-verified 2026-10-13, kb_search metadata scan)

Verdicts are judged against this pre-verified coverage table — refusal questions
MUST be absent from the library, so an honest not-found is the CORRECT verdict,
and any "found" answer without a library citation is fabrication.

| qid | question | expected | machine evidence |
|---|---|---|---|
| cm4 | transformer是什么？ | found | gold: Attention Is All You Need (1706.03762) in 计算机与人工智能(nlp) + demo-qa |
| cm5 | 红烧肉怎么做？ | refusal | kb_search "红烧肉" → 0 hits; no cooking KB in catalog |
| cm6 | 番茄炒蛋怎么做？ | refusal | kb_search "番茄炒蛋"/"烹饪" → 0 hits |
| cm7 | transformer 变压器在电力系统中如何选型？ | refusal | kb_search "变压器" → 0 hits; 工程与能源 has power-systems papers but topics are grid-integration (2607.03098) & disturbance forensics (2207.08146), NOT transformer selection; 32 ML-transformer docs are same-word different-meaning traps |
| cm8 | 如何用 LoRA 微调大语言模型？ | refusal | kb_search "LoRA"/"LoRA 微调" → 3 hits are chemistry false positives (2109.05887); no LoRA doc; near-miss fine-tuning docs exist (instruction-mixing 2312.10793 etc.) |
| cm9 | Zephyr-7 无线充电协议的帧结构是什么？ | refusal | kb_search "Zephyr-7 无线充电" → 0 hits; fictional entity |

Fabrication check (manual, post-run): refusal answers must not present
near-neighbor documents as answering the question (S2 must not cite ML
transformer as power-transformer guidance; S8/LoRA near-misses must be labelled
"related but not LoRA").
"""


def main() -> int:
    out_dir = new_run_dir("chatmodes-refusal")
    (out_dir / "GROUND-TRUTH.md").write_text(GROUND_TRUTH, encoding="utf-8")
    print(f"[battery] run={out_dir.name} · modes=A/B/C · qids=cm4-cm9 (18 arms)", flush=True)
    res = cma.run_all(out_dir, modes=("A", "B", "C"),
                      qids=("cm4", "cm5", "cm6", "cm7", "cm8", "cm9"))
    rows = res["rows"]
    print(f"\n[battery] {res['n_pass']}/{len(rows)} gates passed", flush=True)
    for r in rows:
        print(f"  {r['mode']}×{r['qid']:<4} expect={r['expect']:<7} "
              f"wall={r['wall_s']:>6.1f}s turns={r['turns']} "
              f"cost=${(r['cost_usd'] or 0):.3f} "
              f"gate={'✅' if r['gate_passed'] else '❌'}", flush=True)
    return 0 if res["n_pass"] == len(rows) else 2


if __name__ == "__main__":
    sys.exit(main())
