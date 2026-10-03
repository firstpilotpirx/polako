#!/usr/bin/env python3
"""Personal FSRS parameters from the person's own review log.

    run fsrs_fit.py --dir ~/polako            # report; with enough data writes prep/fsrs-params.json
    run fsrs_fit.py --dir ~/polako --dry      # report only

The default FSRS weights are fitted on millions of Anki reviews. After a few weeks the person's own
log says more about THEIR memory for Serbian words. This fit is deliberately small and safe:
  1. initial stabilities w0..w3 (memory after the first answer Again / Hard / Good / Easy) — fitted on
     the outcome of each side's second review by maximum likelihood, R = (1 + 19/81·t/S)^-0.5;
  2. a calibration table: predicted recall vs actual, in bands — to show whether the schedule is right.
It needs at least 300 second reviews (and 50 per grade to move that grade's weight); otherwise it
reports and changes nothing. The page reads prep/fsrs-params.json at the next build (build_page.py).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsrs  # noqa: E402
from prepio import read_json, write_json, read_log  # noqa: E402

MIN_TOTAL, MIN_GRADE = 300, 50


def pairs(log: list) -> list[tuple[int, float, int]]:
    """(first grade, days until the second review, recalled?) per side."""
    first: dict[str, tuple] = {}
    out = []
    for x in sorted(log, key=lambda r: r[0]):
        k = x[1]
        if k not in first:
            first[k] = (x[0], x[2])
            continue
        if first[k] is None:
            continue
        t0, g = first[k]
        e = (x[0] - t0) / fsrs.DAYMS
        if e >= 0.5:
            out.append((g, e, 1 if x[2] > 1 else 0))
        first[k] = None
    return out


def fit_s0(obs: list[tuple[float, int]]) -> float:
    best, best_ll = None, -1e18
    for i in range(0, 241):
        s = 10 ** (-1 + i * 3 / 240)            # 0.1 … 100 days, log grid
        ll = 0.0
        for e, y in obs:
            r = min(1 - 1e-6, max(1e-6, fsrs.retrievability(e, s)))
            ll += math.log(r if y else 1 - r)
        if ll > best_ll:
            best, best_ll = s, ll
    return best


def calibration(log: list) -> list[dict]:
    bands = [(0, 0.7), (0.7, 0.8), (0.8, 0.85), (0.85, 0.9), (0.9, 0.95), (0.95, 1.01)]
    acc = defaultdict(lambda: [0, 0, 0.0])
    for x in log:
        if x[4] < 1 or not x[5]:
            continue
        r = fsrs.retrievability(x[4], x[5])
        for lo, hi in bands:
            if lo <= r < hi:
                a = acc[(lo, hi)]
                a[0] += 1
                a[1] += x[2] > 1
                a[2] += r
    return [{"band": f"{lo:.2f}-{min(hi, 1):.2f}", "n": v[0], "predicted": round(v[2] / v[0], 3), "actual": round(v[1] / v[0], 3)}
            for (lo, hi), v in sorted(acc.items()) if v[0]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    log = read_log(root)
    ps = pairs(log)
    print(f"answers: {len(log)} · second reviews: {len(ps)}")
    for row in calibration(log):
        print(f"  predicted {row['predicted']:.0%} → actual {row['actual']:.0%}  ({row['n']} reviews, band {row['band']})")
    if len(ps) < MIN_TOTAL:
        print(f"not enough data yet: need {MIN_TOTAL} second reviews — keeping the default weights")
        return 0
    w = list(fsrs.W)
    for g in (1, 2, 3, 4):
        obs = [(e, y) for gg, e, y in ps if gg == g]
        if len(obs) >= MIN_GRADE:
            new = fit_s0(obs)
            print(f"  w{g - 1} (after {['Again', 'Hard', 'Good', 'Easy'][g - 1]}): {w[g - 1]:.2f} → {new:.2f} days ({len(obs)} reviews)")
            w[g - 1] = round(new, 4)
    w[0:4] = sorted(w[0:4])   # memory after Easy is never shorter than after Good, …
    if not a.dry:
        write_json(root / "prep" / "fsrs-params.json", {"w": w, "from": len(ps)})
        print("FSRS_PARAMS prep/fsrs-params.json — the page uses them after the next build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
