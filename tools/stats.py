#!/usr/bin/env python3
"""Statistics in the chat — the same measures as the page's Statistics tab, from the review log.

    run stats.py --dir ~/polako            # a short report
    run stats.py --dir ~/polako --json     # for the hub's status line and for comparisons

From prep/review-log.json ([ts, side key, grade, ms, elapsed days, stability before]) and
prep/trainer-state.json:
  coverage   spoken Serbian and own texts (coverage.py)
  cards      learned (every side stable ≥ 21 days) / firm (≥ 7) / learning / not started — per word
  retention  share of right answers on real reviews (≥ 1 day since the last one), last 30 days, vs target
  by side    accuracy and mean answer time per card side — where the weak spot is
  load       sides due today and in each of the next 7 days
  activity   streak of days with answers, minutes in the last 7 days (an answer counts ≤ 60 s)
  leeches    sides forgotten 6+ times (they leave the rounds until a mnemonic is added)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import read_json, read_yaml, read_log  # noqa: E402

DAY = 86_400_000
LEARNED_S, FIRM_S, LEECH = 21, 7, 6


def day0(ts: int) -> int:
    d = dt.datetime.fromtimestamp(ts / 1000)
    return int(dt.datetime(d.year, d.month, d.day).timestamp() * 1000)


def compute(root: Path, now: int | None = None) -> dict:
    now = now or int(time.time() * 1000)
    st = read_json(root / "prep" / "trainer-state.json", {}) or {}
    cards = st.get("cards") or {}
    log = read_log(root)
    deck = read_yaml(root / "prep" / "words.yaml", {}) or {}
    target = st.get("retention") or (read_yaml(root / "prep" / "profile.yaml", {}) or {}).get("retention", 0.9)
    from words import known_ids
    known, _ = known_ids(root)
    per: dict[str, list] = defaultdict(list)
    for k, c in cards.items():
        per[k.split("|")[0]].append(c)
    state = Counter()
    for w in deck.get("words", []):
        if w.get("retired") or w["id"] in known:
            continue
        cs = per.get(w["id"])
        if not cs:
            state["fresh"] += 1
            continue
        m = min(c.get("s", 0) for c in cs)
        state["learned" if m >= LEARNED_S else "firm" if m >= FIRM_S else "learning"] += 1
    rev = [x for x in log if x[0] >= now - 30 * DAY and x[4] >= 1]
    ret = sum(1 for x in rev if x[2] > 1) / len(rev) if rev else None
    sides: dict[str, dict] = defaultdict(lambda: {"n": 0, "ok": 0, "ms": 0})
    for x in log:
        if x[0] < now - 30 * DAY:
            continue
        s = sides[x[1].split("|")[1] if "|" in x[1] else ""]
        s["n"] += 1
        s["ok"] += x[2] > 1
        s["ms"] += min(60000, x[3] or 0)
    t0 = day0(now)
    load = [0] * 8
    for c in cards.values():
        due = c.get("due")
        if not due:
            continue
        i = max(0, (day0(due) - t0) // DAY)
        if i < 8:
            load[int(i)] += 1
    days = {day0(x[0]) for x in log}
    streak, d = 0, t0
    if d not in days:
        d -= DAY
    while d in days:
        streak += 1
        d -= DAY
    mins = sum(min(60000, x[3] or 0) for x in log if x[0] >= now - 7 * DAY) / 60000
    leeches = sorted({k for k, c in cards.items() if (c.get("lapses") or 0) >= LEECH})
    try:
        from coverage import compute as cov
        c = cov(root)
        coverage = {"spoken": c["spoken"], "my": c["my"]}
    except Exception:
        coverage = {"spoken": None, "my": None}
    return {"coverage": coverage, "words": dict(state), "known_marked": len(known), "retention_30d": ret, "target": target,
            "reviews_30d": len(rev), "by_side": {k: {"n": v["n"], "acc": round(v["ok"] / v["n"], 3), "sec": round(v["ms"] / v["n"] / 1000, 1)}
                                                  for k, v in sorted(sides.items()) if v["n"]},
            "due_today": load[0], "load_7d": load[1:], "streak": streak, "minutes_7d": round(mins), "answers": len(log), "leeches": leeches}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = compute(Path(a.dir).expanduser().resolve())
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    pct = lambda v: "—" if v is None else f"{v * 100:.0f}%"  # noqa: E731
    w = r["words"]
    print(f"understand: spoken {pct(r['coverage']['spoken'])} · own texts {pct(r['coverage']['my'])}")
    print(f"words: learned {w.get('learned', 0)} · firm {w.get('firm', 0)} · learning {w.get('learning', 0)} · not started {w.get('fresh', 0)} · marked known {r['known_marked']}")
    print(f"remembered on reviews (30 d): {pct(r['retention_30d'])} of {r['reviews_30d']} (target {pct(r['target'])})")
    print(f"due today: {r['due_today']} · next 7 days: {' '.join(map(str, r['load_7d']))}")
    print(f"streak: {r['streak']} days · {r['minutes_7d']} min in 7 days · {r['answers']} answers in total")
    weak = sorted(r["by_side"].items(), key=lambda kv: kv[1]["acc"])[:3]
    if weak:
        print("weakest sides: " + ", ".join(f"{k} {pct(v['acc'])} ({v['sec']} s)" for k, v in weak))
    if r["leeches"]:
        print(f"leeches ({len(r['leeches'])}): " + ", ".join(k.split('|')[0] for k in r["leeches"][:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
