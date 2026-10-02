#!/usr/bin/env python3
"""Serbian lemmatizer for frequency analysis: word form → dictionary form (lemma).

    run sr_lemma.py kućama idemo vidio ljudi kuca        # each token → lemma, how it was found, pos
    run sr_lemma.py --forms kuća                         # every known form of a lemma
    run sr_lemma.py --info dobar                         # what the lexicon knows about a lemma
    run sr_lemma.py --rebuild                            # rebuild the cached index

Sources, in priority order (an earlier source wins when a form belongs to several lemmas):
1. data/core_lexicon.yaml — ~480 most frequent lemmas with all their forms (ekavian, curated):
   pronouns, prepositions, biti/imati/znati/moći/ići…, everyday nouns. Regular noun and adjective
   forms are generated from the lemma, gender and stem (paradigm below).
2. UniMorph hbs (fetch_data.py) — ~20k lemmas with inflection tables and pitch accents. Croatian and
   ijekavian lemmas are skipped (data/variants.yaml + rule ije → e when the ekavian word exists).
3. Fallbacks for a form found nowhere: diacritic restoration (kuca → kuća when only kuća is a
   known form), ending stripping onto a known lemma (prodavnicama → prodavnica), otherwise the
   form stands for itself and is marked `self` — the agent fixes the lemma when making the card.

`how` in the output: lex (found), variant (Croatian/ijekavian form mapped to Serbian), fold
(diacritics restored), stem (ending stripped), self (unknown). Library: load() → Lexicon.
"""
from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import BUNDLED, data_dir, read_yaml  # noqa: E402
from translit import fold, norm  # noqa: E402

INDEX_VERSION = 5
POS_UM = {"N": "noun", "V": "verb", "V.PTCP": "verb", "ADJ": "adj"}
SOFT = ("j", "č", "ć", "š", "ž", "đ", "c")
PAL = {"k": "c", "g": "z", "h": "s"}
CONS = "bcčćdđfghklmnprsštvzž"
ADJ_HARD = ["a", "o", "i", "e", "u", "og", "oga", "om", "ome", "oj", "im", "ih", "ima"]
ADJ_SOFT = ["a", "e", "i", "u", "eg", "ega", "em", "emu", "oj", "im", "ih", "ima"]
# ending stripping is a last resort: only long forms, only onto a lemma of a matching part of speech
NOMINAL_ENDS = ["ovima", "evima", "ama", "ima", "ega", "emu", "oga", "ome", "ovi", "evi", "ova", "eva", "ove", "eve",
                "om", "em", "og", "oj", "ih", "im", "a", "e", "i", "u"]
VERBAL_ENDS = ["emo", "imo", "amo", "ete", "ite", "ate", "eju", "uju", "ju", "la", "lo", "li", "le", "ao", "eo", "io", "uo"]
STRIP = sorted([(e, ("noun", "adj")) for e in NOMINAL_ENDS] + [(e, ("verb",)) for e in VERBAL_ENDS],
               key=lambda x: len(x[0]), reverse=True)
LEMMA_ENDS = {"noun": ["", "a", "o", "e"], "adj": ["", "i"], "verb": ["ti", "ati", "iti", "eti", "ovati", "ivati", "nuti"]}
FUTURE = ("ćemo", "ćete", "ćeš", "ću", "će")   # synthetic future: radiću = radi(ti) + ću


# ---------- paradigm generator for the core lexicon ----------
def _pal_last(stem: str) -> str:
    return stem[:-1] + PAL[stem[-1]] if stem and stem[-1] in PAL else stem


def noun_forms(e: dict) -> list[str]:
    if e.get("gen") is False:
        return []
    lem, g = e["l"], e.get("g", "m")
    if g == "f" and lem.endswith("a"):
        st = lem[:-1]
        return [st + "e", st + "i", _pal_last(st) + "i", st + "u", st + "o", st + "om", st + "ama"]
    if g == "f":   # consonant stem: noć, stvar, reč
        return [lem + "i", lem + "ju", lem + "ima"]
    if g == "n" and lem[-1] in "oe":
        st = lem[:-1]
        return [st + "a", st + "u", st + ("om" if lem.endswith("o") else "em"), st + "ima"]
    if g in ("fp", "mp", "np"):
        return []
    st = e.get("st", lem)
    pl = e.get("pl") or _pal_last(st) + "i"
    plst = pl[:-1]
    infix = plst.endswith(("ov", "ev"))
    base = plst if infix else st
    return [st + "a", st + "u", st + ("em" if st.endswith(SOFT) else "om"), st + "e",
            pl, base + "a", plst + "ima", base + "e"]


def adj_forms(e: dict) -> list[str]:
    st = e.get("st", e["l"])
    ends = ADJ_SOFT if st.endswith(SOFT) else ADJ_HARD
    out = [st + x for x in ends]
    if e.get("cmp"):
        c = e["cmp"]
        cs = c[:-1]
        comp = [c] + [cs + x for x in ADJ_SOFT]
        out += comp + ["naj" + x for x in comp]
    return out


def ekavize(w: str) -> str:
    """Ijekavian → ekavian by rule: ije → e, consonant + je → consonant + e (lijep → lep, mjesto → mesto)."""
    w2 = w.replace("ije", "e")
    return re.sub(f"([{CONS}])je", r"\1e", w2)


class Lexicon:
    def __init__(self, forms, lemmas, folded, variants, subs):
        self.forms = forms        # norm form → [lemma, …] in priority order
        self.lemmas = lemmas      # lemma → {pos, src, ru?, g?, asp?, pair?, accent?, z?}
        self.folded = folded      # ascii-folded form → form (only where folding changes it)
        self.variants = variants  # variant → Serbian form
        self.subs = subs          # Serbian subtitle counts (form → count), may be empty
        self._rev = None

    # -- lookups --
    def variant(self, w: str) -> str | None:
        w = norm(w)
        if w in self.variants:
            return self.variants[w]
        if ("ije" in w or re.search(f"[{CONS}]je", w)) and w not in self.forms:
            e = ekavize(w)
            if e != w and (e in self.forms or self.subs.get(e, 0) > self.subs.get(w, 0)):
                return e
        return None

    def lemma(self, token: str) -> tuple[str, str]:
        w = norm(token)
        if not w:
            return w, "self"
        if w in self.forms:
            return self.forms[w][0], "lex"
        v = self.variant(w)
        if v:
            return (self.forms[v][0] if v in self.forms else v), "variant"
        if w == fold(w) and w in self.folded:
            return self.forms[self.folded[w]][0], "fold"
        for end in FUTURE:
            if w.endswith(end) and len(w) > len(end) + 1:
                cand = w[: -len(end)] + "ti"
                if cand in self.lemmas and self.lemmas[cand].get("pos") == "verb":
                    return cand, "lex"
        if len(w) >= 6:
            for end, poses in STRIP:
                if not w.endswith(end) or len(w) - len(end) < 4:
                    continue
                base = w[: len(w) - len(end)]
                for pos in poses:
                    for le in LEMMA_ENDS[pos]:
                        cand = base + le
                        if cand != w and self.lemmas.get(cand, {}).get("pos") == pos:
                            return cand, "stem"
        return w, "self"

    def candidates(self, token: str) -> list[str]:
        """Every lemma the form may belong to (stanu → stati, stan), most likely first."""
        w = norm(token)
        if w in self.forms:
            return list(self.forms[w])
        return [self.lemma(token)[0]]

    def info(self, lemma: str) -> dict:
        key = lemma if lemma in self.lemmas else norm(lemma)
        return dict(self.lemmas.get(key, {}))

    @staticmethod
    def word(lemma_key: str) -> str:
        """Display form of a lemma key: oko~noun → oko."""
        return lemma_key.split("~", 1)[0]

    def forms_of(self, lemma: str) -> list[str]:
        if self._rev is None:
            rev: dict[str, list[str]] = {}
            for f, ls in self.forms.items():
                for lem in ls:
                    rev.setdefault(lem, []).append(f)
            self._rev = rev
        key = lemma if lemma in self._rev else norm(lemma)
        return sorted(self._rev.get(key, []))

    def known(self, w: str) -> bool:
        return norm(w) in self.forms


# ---------- building the index ----------
def _signature(paths: list[Path]) -> str:
    parts = [str(INDEX_VERSION)]
    for p in paths:
        parts.append(f"{p.name}:{p.stat().st_size}:{int(p.stat().st_mtime)}" if p.exists() else f"{p.name}:-")
    return "|".join(parts)


def read_subs(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if not path.exists():
        return out
    from translit import to_latin
    for line in path.open(encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            w = norm(to_latin(parts[0]))
            out[w] = out.get(w, 0) + int(parts[1])
    return out


def build(core_path: Path, um_path: Path, var_path: Path, subs_path: Path) -> Lexicon:
    forms: dict[str, list[str]] = {}
    lemmas: dict[str, dict] = {}

    def add(form: str, lemma: str):
        f = norm(form)
        if not f or " " in f:
            return
        lst = forms.setdefault(f, [])
        if lemma not in lst:
            lst.append(lemma)

    core = read_yaml(core_path, {}) or {}
    for section, pos_default in (("function", None), ("verbs", "verb"), ("nouns", "noun"), ("adjectives", "adj")):
        for e in core.get(section, []):
            word = norm(e["l"])
            info = {k: e[k] for k in ("ru", "g", "asp", "pair", "cmp") if k in e}
            info.update(l=word, pos=e.get("pos", pos_default), src="core")
            lem = word
            if lem in lemmas:   # a homonym (oko prep / oko noun): its own key, the earlier one keeps the bare form
                lem = f"{word}~{info['pos']}"
            lemmas[lem] = info
            add(word, lem)
            extra = (e.get("f") or "").split()
            gen = noun_forms(e) if section == "nouns" else adj_forms(e) if section == "adjectives" else []
            for f in extra + gen:
                add(f, lem)

    variants = {norm(k): norm(v) for k, v in ((read_yaml(var_path, {}) or {}).get("variants") or {}).items()}
    subs = read_subs(subs_path)

    if um_path.exists():
        um_forms: dict[str, set] = {}
        accents: dict[str, str] = {}
        um_pos: dict[str, str] = {}
        cyr = re.compile("[а-яђјљњћџ]", re.I)
        for line in um_path.open(encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3 or not parts[2] or cyr.search(parts[0]) or " " in parts[0]:
                continue
            lem_raw, form, tag = parts
            lem = norm(lem_raw)
            if lem in lemmas or lem in variants:
                continue
            pos = POS_UM.get(tag.split(";")[0])
            if not pos:
                continue
            um_pos.setdefault(lem, pos)
            if " " in form:   # analytic forms (radio sam) — the last word is a form of the lemma
                form = form.split()[-1] if tag.startswith("V;PST") else ""
                if not form:
                    continue
            f = norm(form)
            um_forms.setdefault(lem, set()).add(f)
            if f == lem and form != lem_raw and tag in ("N;NOM;SG", "ADJ;INDF;MASC;NOM;SG", "ADJ;DEF;MASC;NOM;SG", "V;NFIN"):
                accents.setdefault(lem, form)
        known = set(lemmas) | set(um_forms)
        try:
            from wordfreq import zipf_frequency
        except ImportError:  # pragma: no cover
            zipf_frequency = None
        order = []
        for lem in um_forms:
            e = ekavize(lem)
            if e != lem and (e in known or subs.get(e, 0) > subs.get(lem, 0)):
                variants.setdefault(lem, e)   # ijekavian lemma: its forms are not Serbian standard
                continue
            z = zipf_frequency(lem, "sh") if zipf_frequency else 0.0
            order.append((-z, lem))
        for negz, lem in sorted(order):
            info = {"l": lem, "pos": um_pos.get(lem, "noun"), "src": "unimorph", "z": round(-negz, 2)}
            if lem in accents:
                info["accent"] = accents[lem]
            if info["pos"] == "noun":
                info["g"] = "f" if lem.endswith("a") else "n" if lem[-1] in "oe" else "m"
                info["g_guess"] = True
            lemmas[lem] = info
            add(lem, lem)
            for f in sorted(um_forms[lem]):
                add(f, lem)

    folded: dict[str, str] = {}
    for f in forms:
        ff = fold(f)
        if ff != f and ff not in forms:
            prev = folded.get(ff)
            if prev is None or subs.get(f, 0) > subs.get(prev, 0):
                folded[ff] = f
    return Lexicon(forms, lemmas, folded, variants, subs)


_CACHE: Lexicon | None = None


def load(rebuild: bool = False) -> Lexicon:
    global _CACHE
    if _CACHE is not None and not rebuild:
        return _CACHE
    d = data_dir()
    core_p, var_p = BUNDLED / "core_lexicon.yaml", BUNDLED / "variants.yaml"
    um_p, subs_p = d / "unimorph-hbs.tsv", d / "subs-sr-50k.txt"
    sig = _signature([core_p, var_p, um_p, subs_p])
    pk = d / "lexicon.pickle"
    if pk.exists() and not rebuild:
        try:
            with pk.open("rb") as f:
                saved = pickle.load(f)
            if saved.get("sig") == sig:
                _CACHE = saved["lex"]
                return _CACHE
        except Exception:
            pass
    lex = build(core_p, um_p, var_p, subs_p)
    try:
        with pk.open("wb") as f:
            pickle.dump({"sig": sig, "lex": lex}, f, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError:
        pass
    _CACHE = lex
    return lex


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*")
    ap.add_argument("--forms", help="list the forms of a lemma")
    ap.add_argument("--info", help="what is known about a lemma")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    lex = load(rebuild=args.rebuild)
    if args.forms:
        print(" ".join(lex.forms_of(args.forms)))
        return 0
    if args.info:
        print(json.dumps(lex.info(args.info), ensure_ascii=False))
        return 0
    rows = []
    for w in args.words:
        lem, how = lex.lemma(w)
        rows.append({"form": w, "lemma": lem, "how": how, **{k: v for k, v in lex.info(lem).items() if k in ("pos", "ru", "src")}})
    if args.json:
        print(json.dumps(rows, ensure_ascii=False))
    else:
        for r in rows:
            print(f"{r['form']:>16} → {r['lemma']:<16} {r['how']:<8} {r.get('pos', '')} {r.get('ru', '')}")
    if args.rebuild and not args.words:
        print(f"lemmas: {len(lex.lemmas)}, forms: {len(lex.forms)}, variants: {len(lex.variants)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
