"""Wilson CI calculator for ws_001 labeling output.

External research artifact for fab workstream ws_001
(contract: contract_pilot_a3_false_positive v1).

Reads a JSONL file with one record per labeled item:

    {"is_false_positive": true, "tier": "A"}
    {"is_false_positive": false, "tier": "B"}
    ...

and prints:
    - per-tier Wilson 95% CI for the FP proportion;
    - the tier-difference (A - B) point estimate and its 95% CI under
      Newcombe's hybrid score interval.

No external dependencies. Pure stdlib so it runs anywhere.

Pre-register the analysis plan (see prereg-labeling-plan.md) before
running this script. Re-running it after seeing the labels with a different
rubric is a degree of freedom this script cannot prevent.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable

Z_95 = 1.959963984540054  # two-sided 95% normal quantile


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float, float]:
    """Return (point_estimate, lower, upper) for a binomial proportion.

    Uses the Wilson score interval, which behaves well at small n and at
    extreme proportions. Returns NaNs for n == 0.
    """
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, center - margin, center + margin


def newcombe_difference(
    successes_a: int, n_a: int, successes_b: int, n_b: int, z: float = Z_95
) -> tuple[float, float, float]:
    """Return (point_estimate, lower, upper) for p_a - p_b.

    Uses Newcombe's hybrid score interval, which combines the two
    Wilson intervals and avoids the worst pathologies of the naive
    normal-approximation difference at small n.
    """
    if n_a == 0 or n_b == 0:
        return float("nan"), float("nan"), float("nan")
    p_a, l_a, u_a = wilson_interval(successes_a, n_a, z)
    p_b, l_b, u_b = wilson_interval(successes_b, n_b, z)
    diff = p_a - p_b
    lower = diff - math.sqrt((p_a - l_a) ** 2 + (u_b - p_b) ** 2)
    upper = diff + math.sqrt((u_a - p_a) ** 2 + (p_b - l_b) ** 2)
    return diff, lower, upper


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"line {line_no}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise SystemExit(f"line {line_no}: expected JSON object")
            if "is_false_positive" not in obj:
                raise SystemExit(f"line {line_no}: missing is_false_positive")
            if not isinstance(obj["is_false_positive"], bool):
                raise SystemExit(f"line {line_no}: is_false_positive must be bool")
            obj.setdefault("tier", "A")
            records.append(obj)
    return records


def summarize(records: Iterable[dict]) -> dict:
    by_tier: dict[str, list[bool]] = {}
    for record in records:
        tier = str(record.get("tier", "A"))
        by_tier.setdefault(tier, []).append(bool(record["is_false_positive"]))
    summary: dict = {"per_tier": {}}
    for tier, labels in sorted(by_tier.items()):
        n = len(labels)
        successes = sum(labels)
        p, lower, upper = wilson_interval(successes, n)
        summary["per_tier"][tier] = {
            "n": n,
            "false_positives": successes,
            "rate": p,
            "ci_low": lower,
            "ci_high": upper,
        }
    a = summary["per_tier"].get("A")
    b = summary["per_tier"].get("B")
    if a and b:
        diff, lower, upper = newcombe_difference(
            a["false_positives"], a["n"], b["false_positives"], b["n"]
        )
        summary["tier_diff_A_minus_B"] = {
            "point": diff,
            "ci_low": lower,
            "ci_high": upper,
        }
    return summary


def format_human(summary: dict) -> str:
    lines = ["Wilson 95% confidence intervals for FP rate"]
    for tier, stats in summary.get("per_tier", {}).items():
        lines.append(
            f"- tier {tier}: n={stats['n']:>4}  fp={stats['false_positives']:>4}  "
            f"rate={stats['rate']:.3f}  95% CI [{stats['ci_low']:.3f}, "
            f"{stats['ci_high']:.3f}]"
        )
    diff = summary.get("tier_diff_A_minus_B")
    if diff:
        lines.append(
            f"- A - B: {diff['point']:+.3f}  95% CI "
            f"[{diff['ci_low']:+.3f}, {diff['ci_high']:+.3f}]"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSONL of labeled items")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    records = load_records(args.path)
    if not records:
        print("no records loaded", file=sys.stderr)
        return 2

    summary = summarize(records)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_human(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())