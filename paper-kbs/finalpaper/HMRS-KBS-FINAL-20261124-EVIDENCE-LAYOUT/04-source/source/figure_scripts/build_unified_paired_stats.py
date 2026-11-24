"""Paired exploratory statistics for the four retrieval-mode arms of the
unified eight-arm blind batch (E2). Reads judgments-unified.jsonl verbatim,
computes two-sided exact sign tests on per-question dimension/overall
differences and exact McNemar tests on correct-vs-not verdicts, and writes
paired-unified.json next to the source data. Means are cross-checked against
summary-unified.json. Deterministic; no randomness.
"""
import hashlib
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "experiment_data" / "external_baselines_v3"
JUDGMENTS = DATA / "judgments-unified.jsonl"
SUMMARY = DATA / "summary-unified.json"
OUT = DATA / "paired-unified.json"

EXPECTED_SHA256 = {
    "judgments-unified.jsonl": "afcf4aea323c02eb487d96de49359ed8f76efb68685fddf3e490cef908dc182b",
    "summary-unified.json": "6fbb2114db27d20c037b2dbe654a9f09adc815c92f0fe6f5c2807235d09faf58",
}

MATCHED = ["hmrs-agent", "bm25", "dense", "rrf"]
DIMS = ["factual", "completeness", "groundedness", "sources"]
QIDS = [f"BQ{i:02d}" for i in range(1, 11)]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def exact_sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(Fraction(1, 2**n) * Fraction(comb(n, i), 1) for i in range(k + 1))
    return float(min(Fraction(1), 2 * tail))


def comb(n: int, k: int) -> int:
    from math import comb as c
    return c(n, k)


def main() -> None:
    for name, want in EXPECTED_SHA256.items():
        got = sha256(DATA / name)
        if got != want:
            raise SystemExit(f"hash mismatch for {name}: {got}")

    rows = [json.loads(l) for l in JUDGMENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = {(r["qid"], r["arm"]): r for r in rows}
    assert len(rows) == 80, len(rows)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))["primary"]

    def overall(r):
        return sum(r[d] for d in DIMS) / 4.0

    out = {"source": "judgments-unified.jsonl", "matched_arms": MATCHED,
           "tests": "two-sided exact sign (dimensions/overall) and exact McNemar (verdict correct vs not)",
           "contrasts": {}}
    for base in MATCHED[1:]:
        c = {"overall": {}, "dimensions": {}, "verdict": {}}
        w = l = 0
        for q in QIDS:
            d = overall(by[(q, "hmrs-agent")]) - overall(by[(q, base)])
            w += d > 0
            l += d < 0
        c["overall"] = {"wins": w, "losses": l, "ties": 10 - w - l, "sign_p": exact_sign_p(w, l)}
        for dim in DIMS:
            w = l = 0
            for q in QIDS:
                d = by[(q, "hmrs-agent")][dim] - by[(q, base)][dim]
                w += d > 0
                l += d < 0
            c["dimensions"][dim] = {"wins": w, "losses": l, "ties": 10 - w - l, "sign_p": exact_sign_p(w, l)}
        a = sum(by[(q, "hmrs-agent")]["verdict"] == "correct" and by[(q, base)]["verdict"] != "correct" for q in QIDS)
        b = sum(by[(q, "hmrs-agent")]["verdict"] != "correct" and by[(q, base)]["verdict"] == "correct" for q in QIDS)
        c["verdict"] = {"hmrs_only": a, "base_only": b, "mcnemar_p": exact_sign_p(a, b)}
        out["contrasts"][f"hmrs-agent_minus_{base}"] = c

    for arm in MATCHED:
        mean = round(sum(overall(by[(q, arm)]) for q in QIDS) / 10, 2)
        want = summary[arm]["overall"]
        if abs(mean - want) > 0.005:
            raise SystemExit(f"mean cross-check failed for {arm}: {mean} vs {want}")
    out["mean_cross_check"] = "PASS"

    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()