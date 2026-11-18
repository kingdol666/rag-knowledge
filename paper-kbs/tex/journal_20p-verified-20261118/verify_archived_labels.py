#!/usr/bin/env python3
"""Recompute archived labels only; never call services or write data."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "experiment_data"
N_QUESTIONS = 72
ARMS = ("A0", "A0f", "A0h", "PD", "A1b", "A2", "A3")
READ_ALL = "A1-readall"
# Reference counts are the published table values, not independently verified truth.
CAMPAIGNS = (
    ("frozen", "supp_traces_frozen.csv", "frozen-20261111",
     (37, 45, 52, 46, 39, 25, 33), (15, 0), (7, 1)),
    ("follow-up", "supp_traces_followup.csv", "followup-20261112",
     (39, 44, 51, 45, 39, 25, 25), (12, 0), (7, 1)),
    ("rerun-20261117", "supp_traces_rerun_20261117.csv", "rerun-20261117",
     (36, 41, 48, 42, 36, 23, 26), (12, 0), (7, 1)),
)
EXPECTED_ROUTES = {"frozen": (72, 37), "follow-up": (72, 49), "rerun-20261117": (72, 49)}


class ValidationError(Exception):
    """A malformed archive cannot be safely analyzed."""


def boolean(value: str, location: str) -> bool:
    if value not in ("True", "False"):
        raise ValidationError(f"{location}: expected True or False, got {value!r}")
    return value == "True"


Record = tuple[bool, bool, Optional[bool]]


def read_campaign(filename: str, expected_run: str) -> dict[str, dict[str, Record]]:
    path = DATA / filename
    arms: dict[str, dict[str, Record]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        required = {"run", "arm", "qid", "gold_hit", "is_refusal", "route_correct"}
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValidationError(f"{filename}: missing or duplicate CSV headers")
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValidationError(f"{filename}: missing columns {sorted(missing)}")
        for line, row in enumerate(reader, 2):
            location = f"{filename}:{line}"
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"{location}: incorrect number of CSV fields")
            if row["run"] != expected_run:
                raise ValidationError(f"{location}: unexpected run {row['run']!r}")
            arm, qid = row["arm"], row["qid"]
            if arm not in (*ARMS, READ_ALL):
                raise ValidationError(f"{location}: unexpected arm {arm!r}")
            if not qid or qid != qid.strip():
                raise ValidationError(f"{location}: empty or whitespace-padded qid")
            records = arms.setdefault(arm, {})
            if qid in records:
                raise ValidationError(f"{location}: duplicate (arm, qid) {arm!r}, {qid!r}")
            refusal = boolean(row["is_refusal"], location)
            route = (boolean(row["route_correct"], location)
                     if arm in ("A0", "A3") and not refusal else None)
            records[qid] = (boolean(row["gold_hit"], location), refusal, route)
    return arms


def exact_mcnemar(first_only: int, second_only: int) -> float:
    """Two-sided exact binomial test conditional on discordant pairs."""
    n = first_only + second_only
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(first_only, second_only) + 1)) / 2**n)


def discordance(first: dict[str, Record], second: dict[str, Record],
                ids: set[str]) -> tuple[int, int]:
    return (sum(first[qid][0] and not second[qid][0] for qid in ids),
            sum(second[qid][0] and not first[qid][0] for qid in ids))


def validate() -> int:
    failures: list[str] = []
    datasets = [(name, read_campaign(filename, run), counts, a0, pd)
                for name, filename, run, counts, a0, pd in CAMPAIGNS]
    reference_arm = datasets[0][1].get("A0", {})
    reference = {qid: record[1] for qid, record in reference_arm.items()}
    in_domain = {qid for qid, refusal in reference.items() if not refusal}
    if len(in_domain) != N_QUESTIONS:
        failures.append(f"frozen A0 has {len(in_domain)} non-refusal IDs, expected {N_QUESTIONS}")
    if len(reference) - len(in_domain) != 4:
        failures.append(f"frozen A0 has {len(reference) - len(in_domain)} refusal IDs, expected 4")

    print("Archived gold_hit labels: non-refusal questions only; paired by qid")
    print("Full arms require all 72 non-refusal IDs plus the same 4 refusal IDs.")
    for name, arms, expected_counts, expected_a0, expected_pd in datasets:
        print(f"\n[{name}]")
        valid: set[str] = set()
        for arm, expected in zip(ARMS, expected_counts):
            records = arms.get(arm, {})
            missing = set(reference) - set(records)
            extra = set(records) - set(reference)
            mismatched = sorted(qid for qid in set(records) & set(reference)
                                if records[qid][1] != reference[qid])
            if not records or missing or extra or mismatched:
                failures.append(f"{name} {arm}: ID/refusal mismatch; missing={sorted(missing)}, "
                                f"extra={sorted(extra)}, refusal_changed={mismatched}")
                print(f"  {arm}: INVALID ID/refusal alignment; no hit count")
                continue
            valid.add(arm)
            hits = sum(records[qid][0] for qid in in_domain)
            print(f"  {arm}: {hits}/{len(in_domain)}" + (" (reference mismatch)" if hits != expected else ""))
            if hits != expected:
                failures.append(f"{name} {arm}: {hits} hits, reference {expected}")

        if {"A0", "A3"} <= valid:
            routes = tuple(sum(arms[arm][qid][2] is True for qid in in_domain)
                           for arm in ("A0", "A3"))
            print(f"  Labelled-collection routing: A0 {routes[0]}/{len(in_domain)}, "
                  f"A3 {routes[1]}/{len(in_domain)}")
            if routes != EXPECTED_ROUTES[name]:
                failures.append(f"{name}: routing counts {routes}, reference {EXPECTED_ROUTES[name]}")

        records = arms.get(READ_ALL, {})
        unknown = sorted(set(records) - set(reference))
        changed = sorted(qid for qid in set(records) & set(reference)
                         if records[qid][1] != reference[qid])
        if unknown or changed:
            failures.append(f"{name} {READ_ALL}: unknown IDs={unknown}, refusal_changed={changed}")
        read_ids = set(records) & in_domain
        if not records:
            print("  read-all: no rows in this CSV; completeness and hits not measurable")
        elif len(read_ids) != N_QUESTIONS or unknown or changed:
            print(f"  read-all: INCOMPLETE/INVALID ({len(read_ids)}/{N_QUESTIONS} in-domain rows); "
                  "not a 72-question hit rate")
        else:
            hits = sum(records[qid][0] for qid in in_domain)
            print(f"  read-all: complete {hits}/{N_QUESTIONS}")
            if name == "frozen" and hits != 72:
                failures.append(f"frozen read-all: {hits} hits, reference 72")
        if name == "frozen" and len(read_ids) != N_QUESTIONS:
            failures.append("frozen read-all: expected all 72 in-domain rows")

        for other, expected in (("A0", expected_a0), ("PD", expected_pd)):
            if not {"A0h", other} <= valid or len(in_domain) != N_QUESTIONS:
                print(f"  A0h vs {other}: unavailable (invalid paired IDs)")
                continue
            b, c = discordance(arms["A0h"], arms[other], in_domain)
            print(f"  A0h vs {other}: A0h-only={b}, {other}-only={c}, "
                  f"exact two-sided McNemar p={exact_mcnemar(b, c):.10g}")
            if expected is not None and (b, c) != expected:
                failures.append(f"{name} A0h vs {other}: discordance {(b, c)}, reference {expected}")

    print("\nScope: recomputes archived labels, not source-text correctness or a live-system reproduction.")
    if failures:
        print(f"FAIL: {len(failures)} issue(s)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PASS: IDs, label alignment, and available reference counts/contrasts verified.")
    return 0


def main() -> int:
    try:
        return validate()
    except (OSError, UnicodeError, csv.Error, ValidationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
