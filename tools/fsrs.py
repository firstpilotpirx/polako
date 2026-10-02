#!/usr/bin/env python3
"""FSRS-5 in Python — the same formulas as templates/portal/fsrs.js (the page's scheduler).

Used by stats.py (retention, forecasts from the review log), fsrs_fit.py (personal parameters) and
the tests (both implementations must give the same numbers on one script of answers).

    run fsrs.py 3 3 1 3 4 --gap 1 3 0 2 7       # grades and gaps in days between them → the card after each

Card side: s stability (days), d difficulty 1..10, due/last (ms), reps, lapses. Grades 1 Again,
2 Hard, 3 Good, 4 Easy.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

W = [0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046, 1.54575, 0.1192,
     1.01925, 1.9395, 0.11, 0.29605, 2.2698, 0.2315, 2.9898, 0.51655, 0.6621]
DECAY, FACTOR, DAYMS, MAX_IVL, RELEARN_MS = -0.5, 19 / 81, 86_400_000, 3650, 10 * 60_000


def clamp(x, a, b):
    return min(b, max(a, x))


def r4(x):
    # the same rounding as JS Math.round(x * 10000) / 10000 (half up, not banker's)
    return math.floor(x * 10000 + 0.5) / 10000


def retrievability(elapsed_days: float, s: float, w=W) -> float:
    return (1 + FACTOR * elapsed_days / s) ** DECAY


def interval(s: float, retention: float) -> float:
    return s / FACTOR * (retention ** (1 / DECAY) - 1)


def d0(g, w=W):
    return clamp(w[4] - math.exp(w[5] * (g - 1)) + 1, 1, 10)


def s0(g, w=W):
    return max(0.1, w[g - 1])


def next_d(d, g, w=W):
    d1 = d + (-w[6] * (g - 3)) * (10 - d) / 9
    return clamp(w[7] * d0(4, w) + (1 - w[7]) * d1, 1, 10)


def s_recall(d, s, r, g, w=W):
    hard = w[15] if g == 2 else 1
    easy = w[16] if g == 4 else 1
    return s * (1 + math.exp(w[8]) * (11 - d) * s ** (-w[9]) * (math.exp(w[10] * (1 - r)) - 1) * hard * easy)


def s_forget(d, s, r, w=W):
    return min(s, w[11] * d ** (-w[12]) * ((s + 1) ** w[13] - 1) * math.exp(w[14] * (1 - r)))


def s_short(s, g, w=W):
    return s * math.exp(w[17] * (g - 3 + w[18]))


def review(c: dict | None, g: int, now: int, retention: float = 0.9, w=W) -> dict:
    n = {"reps": 0, "lapses": 0}
    elapsed, s_before, r_before = 0.0, 0.0, 1.0
    if not c or not c.get("s"):
        n["s"], n["d"] = s0(g, w), d0(g, w)
    else:
        elapsed = max(0.0, (now - (c.get("last") or now)) / DAYMS)
        s_before, r_before = c["s"], retrievability(elapsed, c["s"])
        n["reps"], n["lapses"] = c.get("reps", 0), c.get("lapses", 0)
        if c.get("f"):
            n["f"] = c["f"]
        d = c.get("d") or d0(3, w)
        n["d"] = next_d(d, g, w)
        if elapsed < 1:
            n["s"] = s_short(c["s"], g, w)
        elif g == 1:
            n["s"] = s_forget(d, c["s"], r_before, w)
            n["lapses"] += 1
        else:
            n["s"] = s_recall(d, c["s"], r_before, g, w)
    n["s"] = clamp(n["s"], 0.1, 36500)
    n["reps"] += 1
    n["last"] = now
    n.setdefault("f", now)
    if g == 1:
        n["due"] = now + RELEARN_MS
    else:
        n["due"] = now + int(clamp(round_js(interval(n["s"], retention)), 1, MAX_IVL)) * DAYMS
    n["s"], n["d"] = r4(n["s"]), r4(n["d"])
    return {"card": n, "elapsed": r4(elapsed), "sBefore": r4(s_before), "r": r4(r_before)}


def round_js(x: float) -> int:
    return math.floor(x + 0.5)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grades", nargs="+", type=int)
    ap.add_argument("--gap", nargs="*", type=float, default=[])
    ap.add_argument("--retention", type=float, default=0.9)
    args = ap.parse_args()
    now, c = 1_790_000_000_000, None
    for i, g in enumerate(args.grades):
        if i:
            now += int((args.gap[i - 1] if i - 1 < len(args.gap) else 1) * DAYMS)
        res = review(c, g, now, args.retention)
        c = res["card"]
        print(json.dumps({"grade": g, "s": c["s"], "d": c["d"], "ivl_days": round((c["due"] - now) / DAYMS, 2), "r": res["r"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
