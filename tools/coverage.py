#!/usr/bin/env python3
"""How much Serbian the person understands — the share of running words covered by what they know.

    run coverage.py --dir ~/polako                 # spoken Serbian, own texts, each situation
    run coverage.py --dir ~/polako --json          # the same as JSON (for the hub's status line)
    run coverage.py --dir ~/polako --deck          # the ceiling: if the whole deck were learned

Known = cards marked "I know" on the Vocabulary tab + cards whose recognition side (Serbian →
meaning) has FSRS stability ≥ 7 days. A known lemma covers every form of it (kuća, kući, kućom…).
Coverage of spoken Serbian is measured on the subtitle lemma list (base_freq.py): "you understand
X% of the words in an ordinary conversation". It is the main number of the statistics tab; the
page computes the same from the shares embedded at build time.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import data_dir, read_yaml  # noqa: E402
from translit import norm, tokens  # noqa: E402


def lemma_counts_of(text: str, lex, prefer: set | None = None) -> Counter:
    c: Counter = Counter()
    for t in tokens(text):
        lem = lex.lemma(t)[0]
        if prefer:
            lem = next((x for x in lex.candidates(t) if x in prefer), lem)
        c[lem] += 1
    return c


def compute(root: Path, whole_deck: bool = False) -> dict:
    from sr_lemma import load
    from text_freq import read_corpus
    from words import known_lemmas, load_deck
    lex = load()
    deck = load_deck(root)
    if whole_deck:
        known = {w.get("lemma", norm(w["sr"])) for w in deck["words"] if not w.get("retired")}
    else:
        known = {k["lemma"] for k in known_lemmas(root)}
    out = {"known": len(known), "spoken": None, "my": None, "texts": [], "situations": []}
    bp = data_dir() / "base-freq.json"
    if bp.exists():
        base = json.loads(bp.read_text(encoding="utf-8"))
        tot = base["tokens"]
        cov = sum(r["n"] for r in base["lemmas"] if r["l"] in known)
        out["spoken"] = round(cov / tot, 4) if tot else None
    my_tot = my_cov = 0
    for doc in read_corpus(root):
        c = lemma_counts_of(doc["text"], lex, known)
        tot = sum(c.values())
        cov = sum(n for lem, n in c.items() if lem in known)
        row = {"id": doc["id"], "title": doc["title"], "words": tot, "coverage": round(cov / tot, 4) if tot else 0.0}
        if doc["kind"] == "my":
            out["texts"].append(row)
            my_tot += tot
            my_cov += cov
        else:
            out["situations"].append(row)
    out["my"] = round(my_cov / my_tot, 4) if my_tot else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--deck", action="store_true")
    args = ap.parse_args()
    res = compute(Path(args.dir).expanduser().resolve(), args.deck)
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
        return 0
    pct = lambda v: "—" if v is None else f"{v * 100:.0f}%"  # noqa: E731
    print(f"known lemmas: {res['known']}" + (" (whole deck)" if args.deck else ""))
    print(f"spoken Serbian: {pct(res['spoken'])} · own texts: {pct(res['my'])}")
    for r in res["texts"]:
        print(f"  text  {r['title'][:40]:<40} {pct(r['coverage']):>5}  ({r['words']} words)")
    for r in res["situations"]:
        print(f"  sit   {r['title'][:40]:<40} {pct(r['coverage']):>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
