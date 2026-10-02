#!/usr/bin/env python3
"""Phrase candidates — whole chunks to learn as they are said: "Koliko košta?", "Može karticom?".

    run phrases.py --dir ~/polako                    # → prep/phrases-draft.yaml (draft for words.py add --kind phrases)
    run phrases.py --dir ~/polako --min 2 --top 40   # n-grams from own texts seen at least twice

Two sources:
1. Situation dialogs — every line the person SAYS (who: me) is a phrase card, and short lines they
   HEAR (who: they, up to 6 words) too: understanding "Za ovde ili za poneti?" matters as much.
   These come already translated.
2. Recurring 2–5-word chunks of the person's own texts (n-grams seen ≥ --min times, at least one
   content word, not only function words): formulas like "Molim Vas da", "Hvala na razumevanju".
   Translation left empty for the agent.
Phrases already in the deck are skipped.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import read_yaml, write_yaml  # noqa: E402
from text_freq import read_corpus  # noqa: E402
from translit import norm, sentences, slug, tokens  # noqa: E402

FUNCTION_POS = {"pron", "prep", "conj", "part", "num", "interj"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--min", type=int, default=2)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    deck = read_yaml(root / "prep" / "words.yaml", {}) or {}
    have = {p["id"] for p in deck.get("phrases", [])}
    draft, seen = [], set()

    sits = read_yaml(root / "prep" / "situations.yaml", {}) or {}
    for s in sits.get("situations", []):
        for d in s.get("dialogs", []):
            for ln in d.get("lines", []):
                n = len(tokens(ln["sr"]))
                if ln["who"] == "they" and n > 6:
                    continue
                pid = "p:" + slug(ln["sr"])[:60].strip("-")
                if pid in have or pid in seen:
                    continue
                seen.add(pid)
                draft.append({"sr": ln["sr"], "tr": ln["tr"], "sit": [s["id"]], "from": f"sit.{s['id']}",
                              "note": "говорю я" if ln["who"] == "me" else "слышу"})

    from sr_lemma import load
    lex = load()
    grams: Counter = Counter()
    shown: dict[str, str] = {}
    for doc in read_corpus(root):
        if doc["kind"] != "my":
            continue
        for sent in (seg for s in sentences(doc["text"]) for seg in re.split(r"[\d,;:()\[\]\"«»–—-]+", s)):
            toks = tokens(sent)   # chunks never span a number or punctuation: "od 9 do 14 časova" is not "od do časova"
            low = [norm(t) for t in toks]
            for n in range(2, 6):
                for i in range(len(low) - n + 1):
                    g = tuple(low[i:i + n])
                    grams[g] += 1
                    shown.setdefault(" ".join(g), " ".join(toks[i:i + n]))
    picked = []
    for g, c in grams.most_common():
        if c < args.min:
            break
        poses = [lex.info(lex.lemma(t)[0]).get("pos", "") for t in g]
        if all(p in FUNCTION_POS for p in poses) or any(len(t) < 2 for t in (g[0], g[-1])):
            continue
        key = " ".join(g)
        if any(key in other for other, _ in picked):   # a longer chunk with the same count already covers it
            continue
        picked.append((key, c))
        if len(picked) >= args.top:
            break
    for key, c in picked:
        sr = shown[key]
        sr = sr[0].upper() + sr[1:]
        pid = "p:" + slug(sr)[:60].strip("-")
        if pid in have or pid in seen:
            continue
        seen.add(pid)
        draft.append({"sr": sr, "tr": "", "from": "my", "note": f"{c}× в моих текстах"})
    out = Path(args.out) if args.out else root / "prep" / "phrases-draft.yaml"
    write_yaml(out, draft)
    print(f"phrases: {sum(1 for d in draft if d.get('sit'))} from situations, {sum(1 for d in draft if not d.get('sit'))} from own texts "
          f"· to translate: {sum(1 for d in draft if not d['tr'])}")
    print(f"DRAFT {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
