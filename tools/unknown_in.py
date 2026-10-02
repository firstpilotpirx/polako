#!/usr/bin/env python3
""""Here is a text — what don't I know in it?" A message, a letter, a notice, a menu.

    run unknown_in.py --dir ~/polako --file letter.txt              # analyse a file
    run unknown_in.py --dir ~/polako --text "Poštovani, …"          # or inline text (Cyrillic is fine)
    run unknown_in.py --dir ~/polako --inbox                        # texts sent from the page ("Мои тексты" tab)
    … --save "Письмо от хозяйки" [--from viber]                     # also keep it in my/ (counts for the deck)
    … --draft                                                       # write the unknown words as a draft for words.py add

For every lemma of the text: known (marked or learned) / learning (in the trainer) / in the deck
(not started) / NOT in the deck. Prints the coverage of this text by known words, the words to look
at first (not in the deck, by frequency in the text and in spoken Serbian), and with --draft writes
prep/text-<slug>.yaml in the same format as `words.py candidates` (examples = the sentences of this
text, translation empty — the agent translates, then `words.py add`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import Fail, read_json, write_json, write_text, write_yaml  # noqa: E402
from translit import norm, sentences, slug, to_latin, tokens  # noqa: E402


def classify(root: Path, text: str) -> dict:
    from base_freq import load_base
    from forms import details
    from sr_lemma import load
    from words import known_ids, learned_ids, load_deck, profile
    lex = load()
    deck = load_deck(root)
    known, _ = known_ids(root)
    known |= learned_ids(root)
    st = read_json(root / "prep" / "trainer-state.json", {}) or {}
    started = {k.split("|")[0] for k in (st.get("cards") or {})}
    by_lemma = {}
    for w in deck["words"]:
        by_lemma.setdefault(w.get("lemma", norm(w["sr"])), w)
    c: Counter = Counter()
    seen_form: dict[str, str] = {}
    for t in tokens(text):
        lem, how = lex.lemma(t)
        for cand in lex.candidates(t):   # prefer the reading that is already in the deck
            if cand in by_lemma:
                lem = cand
                break
        if len(lem) < 2:
            continue
        c[lem] += 1
        seen_form.setdefault(lem, t)
    base = {r["l"]: r for r in load_base()["lemmas"]}
    rows = []
    for lem, n in c.items():
        w = by_lemma.get(lem)
        state = "new"
        if w:
            state = "known" if w["id"] in known else "learning" if w["id"] in started else "deck"
        info = lex.info(lem)
        rows.append({"lemma": lem, "sr": info.get("l", lex.word(lem)), "form": seen_form[lem], "n": n, "state": state,
                     "pm": base.get(lem, {}).get("pm", 0.0), **({"id": w["id"]} if w else {})})
    tot = sum(c.values())
    cov = sum(r["n"] for r in rows if r["state"] == "known")
    rows.sort(key=lambda r: (r["state"] != "new", -r["n"], -r["pm"]))
    lang = profile(root).get("explain", "ru")
    new = [r for r in rows if r["state"] == "new"]
    det = details([r["sr"] for r in new], lex=lex, lang=lang)
    for r in new:
        d = det.get(r["sr"], {})
        if d.get("tr"):
            r["tr"] = d["tr"]
        if d.get("pos"):
            r["pos"] = d["pos"]
    return {"words": tot, "coverage": round(cov / tot, 4) if tot else 0.0, "lemmas": rows}


def draft_from(res: dict, text: str, src_id: str) -> list:
    sents = sentences(text)
    out = []
    for r in res["lemmas"]:
        if r["state"] != "new":
            continue
        e = {"sr": r["sr"], "tr": r.get("tr", ""), "src": ["my"], "my": [src_id]}
        if r.get("pos"):
            e["pos"] = r["pos"]
        if r["lemma"] != norm(r["sr"]):
            e["lemma"] = r["lemma"]
        ex = next((s for s in sorted(sents, key=len) if r["form"] in tokens(s) and len(s) <= 160), None)
        if ex:
            e["ex"] = [{"sr": ex, "tr": "", "about": "my", "from": src_id}]
        out.append(e)
    return out


def save_text(root: Path, text: str, title: str, origin: str) -> str:
    name = slug(title)[:40] or dt.date.today().isoformat()
    p = root / "my" / f"{name}.txt"
    i = 2
    while p.exists():
        p = root / "my" / f"{name}-{i}.txt"
        i += 1
    front = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nfrom: {origin}\nadded: {dt.date.today().isoformat()}\n---\n"
    write_text(p, front + to_latin(text).strip() + "\n")
    return "my." + slug(p.stem)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--file")
    ap.add_argument("--text")
    ap.add_argument("--inbox", action="store_true")
    ap.add_argument("--save", default=None, help="keep the text in my/ under this title")
    ap.add_argument("--from", dest="origin", default="")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    texts: list[tuple[str, str, str]] = []   # (text, title, origin)
    if args.file:
        texts.append((Path(args.file).expanduser().read_text(encoding="utf-8"), args.save or Path(args.file).stem, args.origin))
    if args.text:
        texts.append((args.text, args.save or "text", args.origin))
    if args.inbox:
        ip = root / "prep" / "inbox.json"
        items = read_json(ip, []) or []
        rest = []
        for it in items:
            if it.get("type") == "text" and it.get("text") and not it.get("done"):
                texts.append((it["text"], it.get("title") or "Текст со страницы", it.get("from", "page")))
                it["done"] = True
            rest.append(it)
        write_json(ip, rest)
    if not texts:
        raise Fail("! nothing to analyse: --file, --text or --inbox")
    for text, title, origin in texts:
        res = classify(root, text)
        src_id = "my." + slug(title)
        if args.save or args.inbox:
            src_id = save_text(root, text, title, origin or "manual")
        if args.json:
            print(json.dumps({"title": title, **res}, ensure_ascii=False))
            continue
        states = Counter()
        for r in res["lemmas"]:
            states[r["state"]] += r["n"]
        print(f"«{title}»: {res['words']} words · you know {res['coverage'] * 100:.0f}% of them "
              f"(learning {states['learning']}, in the deck {states['deck']}, new {states['new']})")
        new = [r for r in res["lemmas"] if r["state"] == "new"][:25]
        if new:
            print("  not in the deck yet: " + ", ".join(f"{r['sr']}" + (f" ({r['tr']})" if r.get("tr") else "") for r in new))
        if args.draft:
            out = root / "prep" / f"text-{slug(title)[:40] or 'text'}.yaml"
            write_yaml(out, draft_from(res, text, src_id))
            print(f"DRAFT {out}")
    if args.save or args.inbox:
        from text_freq import analyze
        write_yaml(root / "prep" / "my-freq.yaml", analyze(root))
        print("my-freq updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
