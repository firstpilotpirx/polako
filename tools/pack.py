#!/usr/bin/env python3
"""Ready-made sets (packs): situations with dialogs + a minimal word list + phrases + case cards.

    run pack.py list                                    # bundled packs (data/packs/*.yaml)
    run pack.py show belgrade-basics                    # what is inside: situations, words per situation
    run pack.py --dir ~/polako install belgrade-basics  # put it into the learner's folder
    run pack.py --dir ~/polako coverage belgrade-basics # how much of the pack's dialogs its words cover

`install` is idempotent and goes through the usual scripts, so ids, ranks and progress rules are the same
as for hand-made rounds:
  1. situations.py add (dialogs), the profile gets the pack's situations;
  2. text_freq.py (the dialogs count as the person's situations);
  3. words.py add — words; examples and situation tags come from the dialogs automatically;
  4. words.py add --kind phrases — every line the person says and short lines they hear, plus the pack's phrases;
  5. words.py add --kind cloze — "the right form" cards;
  6. validate + page rebuild.
A pack is content, written and checked by hand: Serbian ekavian Latin, translations in the pack's
`explain` language.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import BUNDLED, Fail, read_yaml, write_yaml  # noqa: E402
from translit import norm, tokens  # noqa: E402

PACKS = BUNDLED / "packs"
TOOLS = Path(__file__).resolve().parent


def load_pack(name: str) -> dict:
    p = PACKS / f"{name}.yaml"
    if not p.exists():
        raise Fail(f"! no pack {name}; available: {', '.join(x.stem for x in PACKS.glob('*.yaml'))}")
    return read_yaml(p, {})


def run(*args) -> None:
    r = subprocess.run([sys.executable, str(TOOLS / args[0]), *args[1:]], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        raise Fail(f"! {args[0]} failed:\n{out}")
    if out:
        print("  " + "\n  ".join(line for line in out.splitlines() if not line.startswith(("PAGE", "MYFREQ"))))


def dialog_phrases(pack: dict) -> list[dict]:
    out, seen = [], set()
    for s in pack.get("situations", []):
        for d in s.get("dialogs", []):
            for ln in d["lines"]:
                n = len(tokens(ln["sr"]))
                if ln["who"] == "they" and n > 7:
                    continue
                k = norm(ln["sr"])
                if k in seen:
                    continue
                seen.add(k)
                out.append({"sr": ln["sr"], "tr": ln["tr"], "sit": [s["id"]], "from": f"sit.{s['id']}",
                            "note": "говорю я" if ln["who"] == "me" else "слышу"})
    for ph in pack.get("phrases", []):
        if norm(ph["sr"]) not in seen:
            seen.add(norm(ph["sr"]))
            out.append(ph)
    return out


def coverage(pack: dict) -> dict:
    """Share of the running words of the pack's dialogs whose lemma is a pack word."""
    from sr_lemma import load
    lex = load()
    have = set()
    for w in pack["words"]:
        have.add(norm(w["sr"]))
        for t in tokens(w["sr"]):   # a multiword card (lična karta) covers its words
            have.add(lex.lemma(t)[0])
    res, tot_all, cov_all, missing = {}, 0, 0, {}
    for s in pack["situations"]:
        tot = cov = 0
        for d in s.get("dialogs", []):
            for ln in d["lines"]:
                for t in tokens(ln["sr"]):
                    cands = lex.candidates(t)
                    tot += 1
                    if any(c in have or lex.word(c) in have for c in cands) or norm(t) in have:
                        cov += 1
                    else:
                        missing[lex.lemma(t)[0]] = missing.get(lex.lemma(t)[0], 0) + 1
        res[s["id"]] = round(cov / tot, 3) if tot else None
        tot_all += tot
        cov_all += cov
    return {"situations": res, "all": round(cov_all / tot_all, 3) if tot_all else None,
            "missing": sorted(missing.items(), key=lambda x: -x[1])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for c in ("show", "install", "coverage"):
        x = sub.add_parser(c)
        x.add_argument("name")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    if a.cmd == "list":
        for p in sorted(PACKS.glob("*.yaml")):
            d = read_yaml(p, {})
            print(f"{p.stem:<20} {d.get('title', '')} — {len(d.get('words', []))} words, {len(d.get('situations', []))} situations")
        return 0
    pack = load_pack(a.name)
    if a.cmd == "show":
        print(f"{pack['title']}: {len(pack['words'])} words, {len(pack.get('phrases', []))} extra phrases, {len(pack.get('cloze', []))} case cards")
        core = [w for w in pack["words"] if not w.get("sit")]
        print(f"  core ({len(core)}): " + ", ".join(w["sr"] for w in core))
        for s in pack["situations"]:
            ws = [w["sr"] for w in pack["words"] if s["id"] in (w.get("sit") or [])]
            print(f"  {s['title']} ({len(ws)}): " + ", ".join(ws))
        return 0
    if a.cmd == "coverage":
        r = coverage(pack)
        print(json.dumps({k: v for k, v in r.items() if k != "missing"}, ensure_ascii=False))
        print("not covered: " + ", ".join(f"{k}×{n}" for k, n in r["missing"][:40]))
        return 0
    # install
    prep = root / "prep"
    prep.mkdir(parents=True, exist_ok=True)
    prof_p = prep / "profile.yaml"
    prof = read_yaml(prof_p, None) or {"version": 1, "explain": pack.get("explain", "ru"), "goal": 15, "retention": 0.9,
                                       "listening": True, "typing": False}
    prof["situations"] = sorted(set(prof.get("situations") or []) | {s["id"] for s in pack["situations"]})
    write_yaml(prof_p, prof, "profile.schema.json")
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        write_yaml(t / "sit.yaml", pack["situations"])
        print("situations:")
        run("situations.py", "--dir", str(root), "add", str(t / "sit.yaml"))
        run("text_freq.py", "--dir", str(root))
        deck = read_yaml(prep / "words.yaml", {}) or {}
        rnd = int(deck.get("rounds", 0)) + 1
        words = [{**w, "src": w.get("src") or (["sit"] if w.get("sit") else ["base"])} for w in pack["words"]]
        write_yaml(t / "words.yaml", words)
        print("words:")
        run("words.py", "--dir", str(root), "add", str(t / "words.yaml"), "--round", str(rnd))
        write_yaml(t / "phrases.yaml", dialog_phrases(pack))
        print("phrases:")
        run("words.py", "--dir", str(root), "add", str(t / "phrases.yaml"), "--kind", "phrases", "--round", str(rnd))
        if pack.get("cloze"):
            write_yaml(t / "cloze.yaml", pack["cloze"])
            print("case cards:")
            run("words.py", "--dir", str(root), "add", str(t / "cloze.yaml"), "--kind", "cloze", "--round", str(rnd))
    run("validate.py", "--dir", str(root), "--update-lock")
    run("build_page.py", "--dir", str(root))
    cov = coverage(pack)
    print(f"PACK {a.name} installed · the pack's words cover {cov['all'] * 100:.0f}% of the words in its dialogs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
