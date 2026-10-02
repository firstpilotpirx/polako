#!/usr/bin/env python3
"""Rank the deck by importance for THIS person: rank, group of 50, frequency band.

    run score_words.py --dir ~/polako                    # rewrite rank / grp / score / zipf / band / pm in prep/words.yaml
    run score_words.py --dir ~/polako --explain kuća     # how one word's score is made

    score = zipf + 0.4·log10(1 + pm)
          + [in situations] (0.6·w_pri + 0.6·log10(1 + f_sit))
          + [in own texts]  (1.5 + 0.8·log10(1 + f_my))
          + boost

  zipf   lemma frequency on the zipf scale: the larger of written Serbo-Croatian (wordfreq 'sh') and
         spoken (all forms in subtitles, log10(pm) + 3); 6 — very common, 3 — rare
  pm     per million in spoken Serbian (subtitles): conversational words rise above bookish ones
  f_sit  occurrences in the person's situations; w_pri — the best priority among them (1 → 2, 2 → 1, 3 → 0.5)
  f_my   occurrences in the person's own texts (my/) — words they already need: a flat +1.5 lifts a
         rare word from a landlord's message (kirija, zipf ≈ 3) above common words nobody sent them
  floor  a card tagged with situations gets zipf ≥ 4.5 / 4.0 / 3.5 by the best priority of its situations
  boost  prep/word-boosts.txt, one "word +N" per line (words for an upcoming appointment, say),
         plus +0.5 for function words at levels a0/a1: without ja, ti, u, na, da no sentence is possible

Logarithms keep one word seen 40 times in a contract from crushing everything else. Phrases are
ordered by the best priority of their situations, then by how often their words occur in own texts.
Cloze cards follow their word. Ids are never touched: progress is tied to them.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import data_dir, read_yaml, write_yaml  # noqa: E402
from translit import norm  # noqa: E402

FUNCTION_POS = {"pron", "prep", "conj", "part", "num", "interj"}
PRI_W = {1: 2.0, 2: 1.0, 3: 0.5}
BANDS = (5.3, 4.5, 3.5)


def band(z: float) -> int:
    return 1 if z >= BANDS[0] else 2 if z >= BANDS[1] else 3 if z >= BANDS[2] else 4


def read_boosts(p: Path) -> dict[str, float]:
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            w, _, v = line.rpartition(" ")
            try:
                out[norm(w)] = float(v)
            except ValueError:
                continue
    return out


class Signals:
    """Everything the score needs, loaded once."""

    def __init__(self, root: Path):
        base_p = data_dir() / "base-freq.json"
        base = json.loads(base_p.read_text(encoding="utf-8")) if base_p.exists() else {"lemmas": []}
        self.base = {r["l"]: r for r in base["lemmas"]}
        self.base_sr = {}
        for r in base["lemmas"]:
            self.base_sr.setdefault(norm(r["sr"]), r)
        my = read_yaml(root / "prep" / "my-freq.yaml", {}) or {}
        self.my = {r["l"]: r for r in my.get("lemmas", [])}
        self.my_sr = {}
        for r in my.get("lemmas", []):
            self.my_sr.setdefault(norm(r["sr"]), r)
        sits = read_yaml(root / "prep" / "situations.yaml", {}) or {}
        self.pri = {s["id"]: s.get("pri", 2) for s in sits.get("situations", [])}
        prof = read_yaml(root / "prep" / "profile.yaml", {}) or {}
        self.level = prof.get("level", "a1")
        self.boosts = read_boosts(root / "prep" / "word-boosts.txt")
        try:
            from wordfreq import zipf_frequency
            self.zipf = lambda w: zipf_frequency(w, "sh")
        except ImportError:  # pragma: no cover
            self.zipf = lambda w: 0.0

    def lookup(self, key: str, sr: str):
        b = self.base.get(key) or self.base_sr.get(norm(sr)) or {}
        m = self.my.get(key) or self.my_sr.get(norm(sr)) or {}
        return b, m

    def score(self, key: str, sr: str, pos: str = "", explain: bool = False, sits: list | None = None):
        b, m = self.lookup(key, sr)
        if sits and not m.get("sit"):
            # a card tagged with situations (a pack, a hand-made card) counts as met in them at least once
            m = {**m, "sit": 1, "src": list(m.get("src", [])) + [f"sit.{x}" for x in sits]}
        pm = b.get("pm", 0.0)
        z_text = b.get("z") if b.get("z") is not None else self.zipf(sr)
        # a lemma's frequency, not its dictionary form's: wordfreq counts only the infinitive of a verb
        # (hteti ≈ 3.4) and misses everyday words (kirija); subtitles count all forms of the lemma
        z_spoken = math.log10(pm) + 3 if pm > 0 else 0.0
        z = round(min(8.0, max(z_text, z_spoken)), 2)
        if sits:
            # a word the person needs in a situation is useful to THEM whatever its corpus frequency:
            # a floor by the situation's priority (1 → 4.5, 2 → 4.0, 3 → 3.5) keeps «uplatnica» from the deck's tail
            best = min((self.pri.get(x, 2) for x in sits), default=2)
            z = max(z, {1: 4.5, 2: 4.0, 3: 3.5}.get(best, 4.0))
        f_my = m.get("my", 0)
        f_sit = m.get("sit", 0)
        w_pri = 0.0
        if f_sit:
            sit_src = [s.split(".", 1)[1] for s in m.get("src", []) if s.startswith("sit.")]
            w_pri = max((PRI_W.get(self.pri.get(s, 2), 1.0) for s in sit_src), default=1.0)
        boost = self.boosts.get(norm(sr), 0.0)
        if pos in FUNCTION_POS and self.level in ("a0", "a1"):
            boost += 0.5
        parts = {"zipf": z, "spoken": 0.4 * math.log10(1 + pm),
                 "sit": (0.6 * w_pri + 0.6 * math.log10(1 + f_sit)) if f_sit else 0.0,
                 "my": (1.5 + 0.8 * math.log10(1 + f_my)) if f_my else 0.0, "boost": boost}
        s = round(sum(parts.values()), 3)
        if explain:
            return s, {**parts, "f_sit": f_sit, "f_my": f_my, "pm": pm}
        return s, {"zipf": z, "pm": pm}


def rescore(root: Path, quiet: bool = False) -> dict:
    p = root / "prep" / "words.yaml"
    deck = read_yaml(p, None)
    if not deck:
        return {}
    sig = Signals(root)
    gs = int(deck.get("group_size", 50))
    words = deck.get("words", [])
    for w in words:
        s, extra = sig.score(w.get("lemma", norm(w["sr"])), w["sr"], w.get("pos", ""), sits=w.get("sit"))
        w["score"] = s
        w["zipf"] = extra["zipf"]
        w["pm"] = extra["pm"]
        w["band"] = band(extra["zipf"])
    active = sorted([w for w in words if not w.get("retired")], key=lambda w: (-w["score"], w["sr"]))
    retired = [w for w in words if w.get("retired")]
    for i, w in enumerate(active + retired, 1):
        w["rank"] = i
        w["grp"] = (i - 1) // gs + 1
    deck["words"] = active + retired
    rank_of = {w["id"]: w["rank"] for w in deck["words"]}
    ph = deck.get("phrases", [])
    for i, x in enumerate(ph):
        x.setdefault("_i", i)
    ph.sort(key=lambda x: (min((sig.pri.get(s, 3) for s in x.get("sit", [])), default=3),
                           -sum(1 for wid in x.get("words", []) if wid in rank_of), x["_i"]))
    for i, x in enumerate(ph, 1):
        x.pop("_i", None)
        x["rank"] = i
        x["grp"] = (i - 1) // gs + 1
    write_yaml(p, deck, "words.schema.json")
    if not quiet:
        print(f"ranked {len(active)} words ({len(retired)} retired), {len(ph)} phrases · groups of {gs}")
    return deck


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--explain", default=None)
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    if args.explain:
        from sr_lemma import load
        key, _ = load().lemma(args.explain)
        s, parts = Signals(root).score(key, args.explain, explain=True)
        print(json.dumps({"word": args.explain, "score": s, **{k: round(v, 3) for k, v in parts.items()}}, ensure_ascii=False))
        return 0
    rescore(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
