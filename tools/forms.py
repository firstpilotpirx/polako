#!/usr/bin/env python3
"""Card details from the lexicons: key forms, gender, accent, aspect, false-friend note.

    run forms.py kuća čitati dobar prozor          # what a card would get
    run forms.py --dir ~/polako fill               # fill the gaps in prep/words.yaml (never overwrites)

Key forms per part of speech (what a learner needs to see on the card):
  noun  gen · acc · loc · ins · pl · gpl         (kuća · kuće · kuću · kući · kućom · kuće · kuća)
  verb  prs1 · prs3 · prs3pl · past · imp        (čitati · čitam · čita · čitaju · čitao · čitaj)
  adj   f · n · cmp                              (dobar · dobra · dobro · bolji)
Sources: the core lexicon's own paradigm first (ekavian), then UniMorph tagged forms (ijekavian
forms are refused), the accented dictionary form only from UniMorph. Gender for nouns outside the
core lexicon is guessed from the ending and marked so (`gender` is then left out of the card).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import BUNDLED, data_dir, read_yaml, write_yaml  # noqa: E402
from sr_lemma import SOFT, Lexicon, adj_forms, load, noun_forms  # noqa: E402
from translit import norm, strip_accents  # noqa: E402

SLOTS = {
    "N;GEN;SG": "gen", "N;ACC;SG": "acc", "N;ESS;SG": "loc", "N;INS;SG": "ins", "N;NOM;PL": "pl", "N;GEN;PL": "gpl",
    "V;PRS;1;SG": "prs1", "V;PRS;3;SG": "prs3", "V;PRS;3;PL": "prs3pl", "V.PTCP;ACT;PST;SG;MASC": "past", "V;IMP;2;SG": "imp",
    "ADJ;INDF;FEM;NOM;SG": "f", "ADJ;INDF;NEUT;NOM;SG": "n", "ADJ;CMPR;MASC;NOM;SG": "cmp",
}
IRREGULAR = {
    "biti": {"prs1": "sam / jesam", "prs3": "je / jeste", "prs3pl": "su / jesu", "past": "bio"},
    "hteti": {"prs1": "hoću / ću", "prs3": "hoće / će", "prs3pl": "hoće / će", "past": "hteo"},
    "imati": {"prs1": "imam / nemam", "prs3": "ima / nema", "prs3pl": "imaju", "past": "imao", "imp": "imaj"},
}
ORDER = {"noun": ["gen", "acc", "loc", "ins", "pl", "gpl"], "verb": ["prs1", "prs3", "prs3pl", "past", "imp"], "adj": ["f", "n", "cmp"]}


def false_friends(lang: str = "ru") -> dict[str, dict]:
    ff = read_yaml(BUNDLED / "false_friends.yaml", {}) or {}
    if ff.get("lang") and ff.get("lang") != lang:
        return {}
    return {norm(x["sr"]): x for x in ff.get("items", [])}


def core_entries() -> dict[str, dict]:
    core = read_yaml(BUNDLED / "core_lexicon.yaml", {}) or {}
    out = {}
    for sec in ("function", "verbs", "nouns", "adjectives"):
        for e in core.get(sec, []):
            out.setdefault(norm(e["l"]), {**e, "_sec": sec})
    return out


def core_forms(e: dict) -> dict:
    sec, lem = e["_sec"], norm(e["l"])
    f = {}
    if sec == "nouns":
        g = e.get("g", "m")
        listed = (e.get("f") or "").split()
        if e.get("gen") is False:
            if listed:
                f["gen"] = listed[0]
            pl = [x for x in listed if x.endswith(("i", "e", "a")) and x not in listed[:1]]
            return f
        if g == "f" and lem.endswith("a"):
            st = lem[:-1]
            f.update(gen=st + "e", acc=st + "u", loc=next((x for x in listed if x.endswith("i")), st + "i"), ins=st + "om", pl=st + "e")
        elif g == "f":
            f.update(gen=lem + "i", loc=lem + "i", pl=lem + "i")
        elif g == "n" and lem[-1] in "oe":
            st = lem[:-1]
            f.update(gen=st + "a", loc=st + "u", ins=st + ("om" if lem.endswith("o") else "em"), pl=st + "a")
        else:
            gen = noun_forms(e)
            st = e.get("st", lem)
            f.update(gen=gen[0], loc=gen[1], ins=gen[2], pl=gen[4], gpl=gen[5])
            if st != lem:
                f["acc"] = lem
        return f
    if sec == "verbs":
        if lem in IRREGULAR:
            return dict(IRREGULAR[lem])
        listed = (e.get("f") or "").split()
        # convention of core_lexicon.yaml: 6 present forms, then the l-participle (m f n pl pl), then the imperative
        if len(listed) >= 6 and listed[0].endswith(("m", "u")) and listed[5].endswith(("u", "e")):
            f.update(prs1=listed[0], prs3=listed[2], prs3pl=listed[5])
            if len(listed) > 6 and listed[6].endswith("o"):
                f["past"] = listed[6]
            imp = [x for x in listed[11:] if not x.endswith("te")]
            if imp:
                f["imp"] = imp[0]
        return f
    if sec == "adjectives":
        st = e.get("st", lem)
        f.update(f=st + "a", n=st + ("e" if st.endswith(SOFT) else "o"))
        if e.get("cmp"):
            f["cmp"] = e["cmp"]
        return f
    return f


def unimorph_slots(words: set[str]) -> dict[str, dict]:
    """One pass over UniMorph: {word: {slot: form, 'accent': …}} for the requested dictionary forms."""
    p = data_dir() / "unimorph-hbs.tsv"
    out: dict[str, dict] = {}
    if not p.exists() or not words:
        return out
    for line in p.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        lem = norm(parts[0])
        if lem not in words:
            continue
        form, tag = parts[1], parts[2]
        slot = SLOTS.get(tag)
        d = out.setdefault(lem, {})
        if slot and slot not in d and " " not in form:
            d[slot] = strip_accents(form).lower()
        if tag in ("N;NOM;SG", "ADJ;INDF;MASC;NOM;SG", "V;NFIN") and norm(form) == lem and form != parts[0] and "accent" not in d:
            d["accent"] = form
    return out


def details(words: list[str], lex: Lexicon | None = None, lang: str = "ru") -> dict[str, dict]:
    """sr dictionary form → {pos, gender, forms, accent, asp, pair, note, tr}"""
    lex = lex or load()
    core = core_entries()
    ff = false_friends(lang)
    keys = {w: lex.lemma(w)[0] for w in words}
    um = unimorph_slots({norm(w) for w in words})
    out = {}
    for w in words:
        n = norm(w)
        info = lex.info(keys[w]) if lex.word(keys[w]) == n else lex.info(n)
        d: dict = {}
        if info.get("pos"):
            d["pos"] = info["pos"]
        e = core.get(n)
        forms = core_forms(e) if e else {}
        for slot, val in (um.get(n) or {}).items():
            if slot == "accent":
                d["accent"] = val
            elif slot not in forms and not lex.variant(val):
                forms[slot] = val
        order = ORDER.get(d.get("pos", ""), [])
        forms = {k: forms[k] for k in order if forms.get(k) and forms[k] != n}
        if forms:
            d["forms"] = forms
        if info.get("g") and not info.get("g_guess"):
            d["gender"] = info["g"]
        for k in ("asp",):
            if info.get(k):
                d[k] = info[k]
        if info.get("pair"):
            d["pair_sr"] = info["pair"]
        if lang == "ru" and info.get("ru"):
            d["tr"] = info["ru"]
        if n in ff:
            x = ff[n]
            d["note"] = f"Ложный друг: не «{x['trap']}», а {x['means']}." if lang == "ru" else f"False friend: {x['means']}"
        out[w] = d
    return out


def fill(root: Path) -> int:
    p = root / "prep" / "words.yaml"
    deck = read_yaml(p, None)
    if not deck:
        print("no deck yet")
        return 0
    lang = deck.get("explain", "ru")
    todo = [w for w in deck.get("words", []) if not w.get("forms") or "pos" not in w]
    det = details([w["sr"] for w in todo], lang=lang)
    n = 0
    for w in todo:
        d = det.get(w["sr"], {})
        for k in ("pos", "gender", "forms", "accent", "asp", "note"):
            if d.get(k) and not w.get(k):
                w[k] = d[k]
                n += 1
    write_yaml(p, deck, "words.schema.json")
    print(f"filled {n} fields in {len(todo)} cards")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--lang", default="ru")
    args = ap.parse_args()
    if args.words and args.words[0] == "fill":
        return fill(Path(args.dir).expanduser().resolve())
    print(json.dumps(details(args.words, lang=args.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
