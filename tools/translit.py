#!/usr/bin/env python3
"""Serbian script and spelling helpers — Latin is the main script, Cyrillic is only input.

    run translit.py lat "Идем у продавницу"        # → Idem u prodavnicu
    run translit.py cyr "Idem u prodavnicu"        # → Идем у продавницу (for display only)
    run translit.py fold "kuća đak"                # → kuca djak (as people type without diacritics)
    run translit.py slug "kuća"                    # → kucja (card id part)

Library (imported by other scripts):
- to_latin(text)      Cyrillic → Latin (Љ → Lj / LJ by context). Latin text passes through.
- to_cyrillic(text)   Latin → Cyrillic with the digraphs lj, nj, dž and the known exceptions
                      where they are two letters (injekcija, konjunkcija, nadživeti, podžanr).
- strip_accents(s)    removes pitch-accent and length marks (kȕća → kuća, ā → a) but keeps
                      č ć š ž (and đ). Accented dictionary forms come from UniMorph.
- fold(s)             ASCII fold as people type without diacritics: č ć → c, š → s, ž → z, đ → dj.
- norm(s)             lowercase + Latin + no accents: the key every script uses for matching.
- slug(s)             id-safe and collision-free: č → ch, ć → cj, š → sh, ž → zh, đ → dj, dž → dzh,
                      so kuća (kucja) and kuca (kuca) never share an id.
- tokens(text)        words of a text (Latin, lowercase kept as written); digits and code are dropped.
- sentences(text)     rough sentence split, for examples from one's own texts.
"""
from __future__ import annotations

import re
import sys
import unicodedata

CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e", "ж": "ž", "з": "z", "и": "i",
    "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "ћ": "ć", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "č", "џ": "dž", "ш": "š",
}
LAT2 = {"lj": "љ", "nj": "њ", "dž": "џ"}
LAT1 = {v: k for k, v in CYR.items() if len(v) == 1}
# words where lj / nj / dž are two letters, not one (prefix + root); matched on the folded lowercase word
SPLIT = re.compile(r"^(?:in(?=jek)|kon(?=junk)|tan(?=jug)|van(?=jez)|nad(?=ž)|pod(?=ž)|od(?=ž)|izvan(?=j))", re.I)
KEEP_MARKS = {"̌", "́"}   # caron (č š ž) and acute (ć) on c/s/z only


def to_latin(text: str) -> str:
    out = []
    n = len(text)
    for i, ch in enumerate(text):
        low = ch.lower()
        if low not in CYR:
            out.append(ch)
            continue
        lat = CYR[low]
        if ch != low:   # uppercase: Љ before an uppercase letter (or alone in an all-caps word) → LJ
            nxt = text[i + 1] if i + 1 < n else ""
            whole_caps = nxt.isupper() or (not nxt.isalpha() and i > 0 and text[i - 1].isupper())
            lat = lat.upper() if whole_caps else lat[0].upper() + lat[1:]
        out.append(lat)
    return "".join(out)


def _word_to_cyr(w: str) -> str:
    out, i, lw = [], 0, w.lower()
    m = SPLIT.match(lw)
    guard = len(m.group(0)) if m else -1   # the match ends between the two letters: no digraph across it
    while i < len(w):
        pair = lw[i:i + 2]
        if pair in LAT2 and i + 1 != guard:
            c = LAT2[pair]
            out.append(c.upper() if w[i].isupper() else c)
            i += 2
            continue
        ch = w[i]
        c = LAT1.get(ch.lower())
        out.append((c.upper() if ch.isupper() else c) if c else ch)
        i += 1
    return "".join(out)


def to_cyrillic(text: str) -> str:
    return re.sub(r"[^\W\d_]+", lambda m: _word_to_cyr(m.group(0)), text)


def strip_accents(s: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.combining(ch):
            if out and out[-1].lower() in "csz" and ch in KEEP_MARKS:
                out.append(ch)
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


FOLD = str.maketrans({"č": "c", "ć": "c", "š": "s", "ž": "z", "Č": "C", "Ć": "C", "Š": "S", "Ž": "Z"})


def fold(s: str) -> str:
    return s.translate(FOLD).replace("đ", "dj").replace("Đ", "Dj")


def norm(s: str) -> str:
    return strip_accents(to_latin(s)).lower().strip()


SLUG = [("dž", "dzh"), ("č", "ch"), ("ć", "cj"), ("š", "sh"), ("ž", "zh"), ("đ", "dj")]


def slug(s: str) -> str:
    s = norm(s)
    for a, b in SLUG:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


CODE = re.compile(r"```.*?```|`[^`]*`|https?://\S+|\S+@\S+", re.S)
WORD = re.compile(r"[^\W\d_]+")   # hyphen and apostrophe split words: Šta-ti-je → šta, ti, je


def tokens(text: str) -> list[str]:
    text = to_latin(CODE.sub(" ", text))
    return [strip_accents(w) for w in WORD.findall(text)]


def sentences(text: str) -> list[str]:
    text = to_latin(CODE.sub(" ", text))
    parts = re.split(r"(?<=[.!?…])\s+|\n{1,}", text)
    return [p.strip() for p in parts if len(p.strip()) > 1]


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("lat", "cyr", "fold", "slug", "norm"):
        print(__doc__)
        return 2
    text = " ".join(argv[2:])
    fn = {"lat": to_latin, "cyr": to_cyrillic, "fold": fold, "slug": slug, "norm": norm}[argv[1]]
    print(fn(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
