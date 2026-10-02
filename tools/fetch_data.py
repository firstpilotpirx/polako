#!/usr/bin/env python3
"""Download the open corpora once into the data cache (~/.local/share/polako/data, or $POLAKO_DATA).

    run fetch_data.py                 # the required set: UniMorph forms + subtitle frequency lists
    run fetch_data.py --tatoeba       # + Tatoeba sentence pairs sr–<explain language> for examples
    run fetch_data.py --status        # what is there, sizes, dates

Everything is downloaded from GitHub (raw.githubusercontent.com) except Tatoeba. A file already
present is not downloaded again (--force to refresh). Nothing from these corpora is copied into the
plugin or the person's folder except derived counts.

| key       | what                                                        | licence      |
|-----------|-------------------------------------------------------------|--------------|
| unimorph  | UniMorph hbs: lemma → inflected forms with features, accents | CC BY-SA 3.0 |
| subs-sr   | OpenSubtitles 2018, Serbian: 50k most frequent word forms     | CC BY-SA 4.0 |
| subs-hr   | the same for Croatian — to tell Croatianisms apart           | CC BY-SA 4.0 |
| tatoeba   | Tatoeba sentences (srp) + links to the explanation language  | CC BY 2.0 FR |

Exit code 6 and the line POLAKO_OFFLINE … when a required file cannot be downloaded: the hub tells
the person and continues with the bundled core lexicon only.
"""
from __future__ import annotations

import argparse
import bz2
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import data_dir  # noqa: E402

RAW = "https://raw.githubusercontent.com"
SOURCES = {
    "unimorph": (f"{RAW}/unimorph/hbs/master/hbs", "unimorph-hbs.tsv", 20_000_000),
    "subs-sr": (f"{RAW}/hermitdave/FrequencyWords/master/content/2018/sr/sr_50k.txt", "subs-sr-50k.txt", 400_000),
    "subs-hr": (f"{RAW}/hermitdave/FrequencyWords/master/content/2018/hr/hr_50k.txt", "subs-hr-50k.txt", 400_000),
}
TATOEBA = "https://downloads.tatoeba.org/exports/per_language"
ISO3 = {"ru": "rus", "en": "eng", "uk": "ukr", "de": "deu", "be": "bel", "pl": "pol", "fr": "fra", "es": "spa", "it": "ita"}


def get(url: str, dest: Path, min_size: int = 0) -> bool:
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "polako-plugin/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        if tmp.stat().st_size < min_size:
            raise OSError(f"too small: {tmp.stat().st_size} bytes")
        tmp.replace(dest)
        return True
    except Exception as e:  # network, proxy, 404
        print(f"! {url}: {e}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False


def status(d: Path) -> dict:
    out = {}
    for key, (_, name, _) in SOURCES.items():
        p = d / name
        out[key] = {"file": str(p), "ok": p.exists(), "bytes": p.stat().st_size if p.exists() else 0,
                    "date": dt.date.fromtimestamp(p.stat().st_mtime).isoformat() if p.exists() else None}
    tp = d / "tatoeba-pairs.tsv"
    out["tatoeba"] = {"file": str(tp), "ok": tp.exists(), "bytes": tp.stat().st_size if tp.exists() else 0}
    return out


def tatoeba(d: Path, lang: str) -> bool:
    """Sentence pairs sr ↔ lang as one TSV: sr<TAB>translation. Serbian sentences in Cyrillic are converted."""
    from translit import to_latin
    l3 = ISO3.get(lang, lang)
    files = {
        "srp": (f"{TATOEBA}/srp/srp_sentences.tsv.bz2", d / "tatoeba-srp.tsv.bz2"),
        "oth": (f"{TATOEBA}/{l3}/{l3}_sentences.tsv.bz2", d / f"tatoeba-{l3}.tsv.bz2"),
        "links": (f"{TATOEBA}/srp/srp-{l3}_links.tsv.bz2", d / f"tatoeba-srp-{l3}-links.tsv.bz2"),
    }
    for url, dest in files.values():
        if not dest.exists() and not get(url, dest, 1000):
            return False
    def sents(p):
        out = {}
        with bz2.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3:
                    out[parts[0]] = parts[2]
        return out
    sr, oth = sents(files["srp"][1]), sents(files["oth"][1])
    n = 0
    with bz2.open(files["links"][1], "rt", encoding="utf-8") as f, open(d / "tatoeba-pairs.tsv", "w", encoding="utf-8") as out:
        for line in f:
            a, _, b = line.rstrip("\n").partition("\t")
            if a in sr and b in oth:
                out.write(f"{to_latin(sr[a])}\t{oth[b]}\n")
                n += 1
            elif b in sr and a in oth:
                out.write(f"{to_latin(sr[b])}\t{oth[a]}\n")
                n += 1
    print(f"tatoeba: {n} sentence pairs sr–{lang}")
    return n > 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tatoeba", action="store_true", help="also download Tatoeba sentence pairs")
    ap.add_argument("--lang", default="ru", help="explanation language for Tatoeba pairs (default ru)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    d = data_dir()
    if args.status:
        print(json.dumps(status(d), ensure_ascii=False, indent=1))
        return 0
    missing = []
    for key, (url, name, min_size) in SOURCES.items():
        dest = d / name
        if dest.exists() and not args.force:
            print(f"{key}: already here ({dest.stat().st_size // 1024} KB)")
            continue
        print(f"{key}: downloading…", file=sys.stderr)
        if get(url, dest, min_size):
            print(f"{key}: ok ({dest.stat().st_size // 1024} KB)")
        else:
            missing.append(key)
    if args.tatoeba and not tatoeba(d, args.lang):
        print("tatoeba: not available — examples will be written by Claude instead", file=sys.stderr)
    if missing:
        print(f"POLAKO_OFFLINE {' '.join(missing)}")
        return 6
    # the lemma index is rebuilt lazily by sr_lemma.py when its sources change
    print(f"DATA {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
