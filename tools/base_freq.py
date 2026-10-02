#!/usr/bin/env python3
"""Step 1 of the vocabulary method: what spoken Serbian sounds like — lemma frequency of subtitles.

    run base_freq.py                      # → <data cache>/base-freq.json (once per machine; the same for everyone)
    run base_freq.py --top 40             # also print the top 40 and the coverage table

Input: OpenSubtitles Serbian 50k word forms (fetch_data.py). Cyrillic forms are transliterated,
forms are lemmatized (sr_lemma.py), Croatian/ijekavian forms are added to their Serbian lemma.
Each lemma gets:
  n      occurrences in subtitles (all its forms)
  pm     per million tokens
  z      zipf in general Serbo-Croatian text (wordfreq 'sh': news, web, books) — overall usefulness
  pos, how (lex / variant / fold / stem / self), ru (core lexicon translation, if any)
  hr     true when the form is much more common in Croatian subtitles (a Croatianism to skip)
Coverage: what share of all running words the top 100 / 300 / 500 / 1000 / 2000 / 5000 lemmas
cover. Typically top 1000 ≈ 80% of what is said: the tail pays off less and less.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import data_dir, write_json  # noqa: E402
from sr_lemma import load, read_subs  # noqa: E402

CUTS = (100, 300, 500, 1000, 2000, 5000)


def build(top_print: int = 0) -> dict:
    d = data_dir()
    sr_p, hr_p = d / "subs-sr-50k.txt", d / "subs-hr-50k.txt"
    if not sr_p.exists():
        raise SystemExit("! no subtitle frequency list: run fetch_data.py first (POLAKO_NO_DATA)")
    lex = load()
    sr, hr = read_subs(sr_p), read_subs(hr_p)
    total_sr, total_hr = sum(sr.values()) or 1, sum(hr.values()) or 1
    try:
        from wordfreq import zipf_frequency
    except ImportError:  # pragma: no cover
        zipf_frequency = lambda w, l: 0.0  # noqa: E731
    agg: dict[str, dict] = {}
    for form, n in sr.items():
        if not form.isalpha():
            continue
        lem, how = lex.lemma(form)
        a = agg.setdefault(lem, {"n": 0, "how": how, "forms": {}})
        a["n"] += n
        a["forms"][form] = a["forms"].get(form, 0) + n
        if how == "lex":
            a["how"] = "lex"
        hr_share, sr_share = hr.get(form, 0) / total_hr, n / total_sr
        if how == "self" and hr_share > 3 * sr_share and n < 2000:
            a["hr"] = True
    rows = []
    for lem, a in agg.items():
        info = lex.info(lem)
        word = info.get("l", lex.word(lem))
        row = {"l": lem, "sr": word, "n": a["n"], "pm": round(a["n"] * 1e6 / total_sr, 2),
               "z": round(zipf_frequency(word, "sh"), 2), "pos": info.get("pos", ""), "how": a["how"],
               "top": sorted(a["forms"], key=lambda f: -a["forms"][f])[:4]}
        if info.get("ru"):
            row["ru"] = info["ru"]
        if a.get("hr"):
            row["hr"] = True
        rows.append(row)
    rows.sort(key=lambda r: -r["n"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    cum, cov, ci = 0, {}, 0
    for i, r in enumerate(rows, 1):
        cum += r["n"]
        while ci < len(CUTS) and i == CUTS[ci]:
            cov[str(CUTS[ci])] = round(cum / total_sr, 4)
            ci += 1
    out = {"built": dt.date.today().isoformat(), "source": "OpenSubtitles 2018 sr (top 50k forms)",
           "tokens": total_sr, "lemmas": rows, "coverage": cov}
    write_json(d / "base-freq.json", out, indent=None)
    if top_print:
        for r in rows[:top_print]:
            print(f"{r['rank']:>5} {r['sr']:<14} {r['pm']:>9} pm  z={r['z']:<4} {r['pos']:<6} {r['how']:<7} {r.get('ru', '')}")
    print("coverage of spoken Serbian by the top lemmas:")
    for k, v in cov.items():
        print(f"  top {k:>5}: {v * 100:.0f}%")
    print(f"BASE {d / 'base-freq.json'} lemmas={len(rows)}")
    return out


def load_base() -> dict:
    p = data_dir() / "base-freq.json"
    if not p.exists():
        return build()
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=0)
    args = ap.parse_args()
    build(args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
