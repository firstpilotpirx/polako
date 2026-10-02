#!/usr/bin/env python3
"""The deck prep/words.yaml — candidates, adding cards, rounds of the "what I know" check. No manual editing.

    run words.py --dir . candidates [--n 400]          # → prep/round-<N>.yaml: a ready draft of the next round
    run words.py --dir . add prep/round-<N>.yaml       # cards from the (checked, translated) draft
    run words.py --dir . add draft.yaml --kind phrases # phrase cards;  --kind cloze for "fill the form" cards
    run words.py --dir . round                         # result of the last check round → what next
    run words.py --dir . known [--json]                # lemmas the person knows (marked or learned)
    run words.py --dir . seen                          # every word already in the deck (one per line)
    run words.py --dir . retire w:kuca                 # stop offering a card; progress is kept
    run words.py --dir . set w:kucja tr="дом" note="…" # fix a card's text fields (never its id)

candidates — the method in one command (skills/polako-start/modules/vocab.md):
  1. merges three signals: spoken frequency (base_freq.py), the person's own texts and situations
     (text_freq.py — rerun first if my/ or situations changed);
  2. drops what must not be learned: already in the deck, Croatianisms and ijekavian forms, one-letter
     junk, words a learner of this level surely knows (b1: zipf ≥ 6.3, b2: ≥ 5.8);
  3. takes every word of the person's own texts and situations, then fills the round up to --n from
     the top of spoken frequency, ranked by the same score as score_words.py;
  4. pre-fills every entry: translation (core lexicon, Russian), part of speech, gender, key forms,
     accent, aspect partner, false-friend note, and examples — from the person's own texts (tr empty:
     to translate), from situation dialogs (already translated), from Tatoeba if downloaded.
  The agent then deletes junk (names from subtitles, `flags: [self]` that are not words), fills the
  empty `tr`, adds a short example where there is none, and runs `add`.

add — ids are slugs of the Serbian word (w:kucja for kuća) and NEVER change; a homonym gets its part
  of speech appended (w:oko-noun). Missing details are filled from the lexicons (forms.py); entries with
  an empty `tr` are refused, examples with an empty `tr` are dropped with a warning. Duplicates (same sr
  and pos) are skipped. Then the deck is re-ranked (score_words.py) and the page rebuilt.

round — from prep/vocab-state.json (the page's "I know" marks): share known in the last round →
  ≥ 80% "go deeper: ≈400 more", 50–80% "one more smaller round ≈200", < 50% "boundary found — learn".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import Fail, data_dir, read_json, read_yaml, rebuild, write_yaml  # noqa: E402
from translit import norm, slug, to_latin, tokens  # noqa: E402

SCHEMA = "words.schema.json"
LEVEL_N = {"a0": 300, "a1": 400, "a2": 500, "b1": 500, "b2": 500}
LEVEL_SKIP = {"b1": 6.3, "b2": 5.8}
LEARNED_S = 21.0     # days of FSRS stability for "learned"
KNOWN_S = 7.0        # recognition stability that counts as "understood" for coverage


def deck_path(root: Path) -> Path:
    return root / "prep" / "words.yaml"


def load_deck(root: Path, explain: str = "ru") -> dict:
    d = read_yaml(deck_path(root), None)
    if not d:
        d = {"version": 1, "built": dt.date.today().isoformat(), "explain": explain, "group_size": 50, "rounds": 0,
             "words": [], "phrases": [], "cloze": []}
    for k in ("words", "phrases", "cloze"):
        d.setdefault(k, [])
    return d


def profile(root: Path) -> dict:
    return read_yaml(root / "prep" / "profile.yaml", {}) or {}


# ---------- what the person knows ----------
def known_ids(root: Path) -> tuple[set, set]:
    """(known, checked) card ids from the page's "I know" marks; a {reset: true} record is ignored."""
    v = read_json(root / "prep" / "vocab-state.json", {}) or {}
    known, checked = set(), set()
    for rec in v.values():
        if not isinstance(rec, dict) or rec.get("reset"):
            continue
        known |= set(rec.get("known", []))
        checked |= set(rec.get("known", [])) | set(rec.get("unknown", []))
    return known, checked


def learned_ids(root: Path, min_s: float = KNOWN_S) -> set:
    """Words whose recognition side (sr → meaning) is stable enough to count as understood."""
    st = read_json(root / "prep" / "trainer-state.json", {}) or {}
    cards = st.get("cards") or {}
    out = set()
    for key, c in cards.items():
        cid, _, side = key.partition("|")
        if side in ("say-tr", "pick-tr", "listen") and (c.get("s") or 0) >= min_s:
            out.add(cid)
    return out


def known_lemmas(root: Path) -> list[dict]:
    deck = load_deck(root)
    known, _ = known_ids(root)
    known |= learned_ids(root)
    return [{"id": w["id"], "sr": w["sr"], "lemma": w.get("lemma", norm(w["sr"]))} for w in deck["words"] if w["id"] in known]


# ---------- candidates ----------
def _examples_index(root: Path):
    sits = read_yaml(root / "prep" / "situations.yaml", {}) or {}
    lines = []
    for s in sits.get("situations", []):
        for d in s.get("dialogs", []):
            for ln in d.get("lines", []):
                lines.append((ln["sr"], ln["tr"], "sit." + s["id"]))
    tat = []
    tp = data_dir() / "tatoeba-pairs.tsv"
    if tp.exists():
        for line in tp.open(encoding="utf-8"):
            a, _, b = line.rstrip("\n").partition("\t")
            if a and b and len(a) <= 80:
                tat.append((a, b))
    return lines, tat


def candidates(root: Path, n: int | None, out: Path | None) -> int:
    from base_freq import load_base
    from forms import details
    from score_words import Signals
    from sr_lemma import load
    prof = profile(root)
    level, lang = prof.get("level", "a1"), prof.get("explain", "ru")
    n = n or LEVEL_N.get(level, 400)
    lex = load()
    deck = load_deck(root, lang)
    have = {w.get("lemma", norm(w["sr"])) for w in deck["words"]} | {norm(w["sr"]) for w in deck["words"]}
    base = load_base()
    my = read_yaml(root / "prep" / "my-freq.yaml", {}) or {}
    sig = Signals(root)
    pool: dict[str, dict] = {}
    for r in base["lemmas"][:20000]:
        pool[r["l"]] = {"l": r["l"], "sr": r["sr"], "pos": r.get("pos", ""), "how": r["how"], "src": ["base"], "hr": r.get("hr", False)}
    for r in my.get("lemmas", []):
        e = pool.setdefault(r["l"], {"l": r["l"], "sr": r["sr"], "pos": r.get("pos", ""), "how": r["how"], "src": []})
        if r.get("my"):
            e["src"].append("my")
            e["my"] = [s for s in r["src"] if s.startswith("my.")]
            e["my_ex"] = r.get("ex", [])
        if r.get("sit"):
            e["src"].append("sit")
            e["sit"] = [s.split(".", 1)[1] for s in r["src"] if s.startswith("sit.")]
    skip_z = LEVEL_SKIP.get(level)
    rows = []
    for key, e in pool.items():
        sr = e["sr"]
        if key in have or norm(sr) in have or not sr.isalpha() or len(sr) < 2 and e["how"] == "self":
            continue
        if e.get("hr") and "my" not in e["src"] and "sit" not in e["src"]:
            continue
        if lex.variant(sr):
            continue
        s, extra = sig.score(key, sr, e.get("pos", ""))
        if skip_z and extra["zipf"] >= skip_z and "my" not in e["src"]:
            continue
        rows.append((s, key, e, extra))
    rows.sort(key=lambda x: (-x[0], x[2]["sr"]))
    # every word of the person's own texts and situations goes in (up to n), the rest of the round is
    # filled from the top of spoken frequency
    own = [r for r in rows if "my" in r[2]["src"] or "sit" in r[2]["src"]][:n]
    rest = [r for r in rows if not ("my" in r[2]["src"] or "sit" in r[2]["src"])][: max(0, n - len(own))]
    rows = sorted(own + rest, key=lambda x: (-x[0], x[2]["sr"]))
    det = details([r[2]["sr"] for r in rows], lex=lex, lang=lang)
    lines, tat = _examples_index(root)
    draft = []
    for s, key, e, extra in rows:
        sr = e["sr"]
        d = det.get(sr, {})
        forms = set(lex.forms_of(key)) | {norm(sr)}
        entry = {"sr": sr, "tr": d.get("tr", "")}
        if key != norm(sr):
            entry["lemma"] = key
        for k in ("pos", "gender", "forms", "accent", "asp", "note"):
            if d.get(k):
                entry[k] = d[k]
        if d.get("pair_sr"):
            entry["pair_sr"] = d["pair_sr"]
        entry["src"] = sorted(set(e["src"]))
        if e.get("sit"):
            entry["sit"] = e["sit"]
        if e.get("my"):
            entry["my"] = e["my"]
        ex = [{"sr": x["sr"], "tr": "", "about": "my", "from": x["from"]} for x in e.get("my_ex", [])[:1]]
        for sr_line, tr_line, src in lines:
            if len(ex) >= 2:
                break
            if forms & {norm(t) for t in tokens(sr_line)}:
                ex.append({"sr": sr_line, "tr": tr_line, "about": "sit", "from": src})
        if len(ex) < 2:
            for a, b in tat:
                if forms & {norm(t) for t in tokens(a)}:
                    ex.append({"sr": a, "tr": b, "about": "general", "from": "tatoeba"})
                    break
        if ex:
            entry["ex"] = ex
        flags = [f for f in (e["how"] if e["how"] in ("self", "stem", "fold") else None,) if f]
        if flags:
            entry["flags"] = flags
        entry["score"] = s
        entry["zipf"] = extra["zipf"]
        draft.append(entry)
    rnd = int(deck.get("rounds", 0)) + 1
    out = out or root / "prep" / f"round-{rnd}.yaml"
    write_yaml(out, draft)
    by = {k: sum(1 for x in draft if k in x["src"]) for k in ("base", "my", "sit")}
    todo = sum(1 for x in draft if not x["tr"]) + sum(1 for x in draft for y in x.get("ex", []) if not y["tr"])
    print(f"round {rnd}: {len(draft)} candidates (spoken {by['base']}, own texts {by['my']}, situations {by['sit']}) · "
          f"to translate: {todo} · flagged: {sum(1 for x in draft if x.get('flags'))}")
    print(f"DRAFT {out}")
    return 0


# ---------- adding ----------
def _clean_ex(ex: list, warn: list, sr: str) -> list:
    out = []
    for x in ex or []:
        if not str(x.get("tr", "")).strip() or not str(x.get("sr", "")).strip():
            warn.append(sr)
            continue
        y = {"sr": to_latin(str(x["sr"]).strip()), "tr": str(x["tr"]).strip()}
        if x.get("about") in ("my", "sit", "general"):
            y["about"] = x["about"]
        if x.get("from"):
            y["from"] = str(x["from"])
        out.append(y)
    return out[:4]


def add(root: Path, draft_p: Path, kind: str, rnd: int | None, score: bool = True) -> int:
    from forms import details
    from sr_lemma import load
    lang = profile(root).get("explain", "ru")
    deck = load_deck(root, lang)
    items = read_yaml(draft_p, [])
    if isinstance(items, dict):
        items = items.get(kind) or items.get("words") or []
    if not isinstance(items, list):
        raise Fail(f"! {draft_p}: expected a list of cards")
    gs = int(deck.get("group_size", 50))
    if rnd is None:
        rnd = int(deck.get("rounds", 0)) + 1 if kind == "words" else max(1, int(deck.get("rounds", 0)))
    missing = [str(x.get("sr")) for x in items if not str(x.get("tr", "")).strip()]
    if missing:
        raise Fail(f"! {len(missing)} entries without a translation (tr): {', '.join(missing[:12])}… — translate or delete them")
    warn: list[str] = []
    added = dup = 0
    if kind == "words":
        lex = load()
        det = details([to_latin(str(x["sr"]).strip()) for x in items], lex=lex, lang=lang)
        ids = {w["id"]: w for w in deck["words"]}
        seen = {(norm(w["sr"]), w.get("pos", "")) for w in deck["words"]}
        nxt = max((w["rank"] for w in deck["words"]), default=0)
        pending_pairs = []
        for x in items:
            sr = to_latin(str(x["sr"]).strip())
            d = det.get(sr, {})
            pos = x.get("pos") or d.get("pos") or ("phrase" if " " in sr else "")
            if (norm(sr), pos) in seen:
                dup += 1
                continue
            cid = "w:" + slug(sr)
            if cid in ids:
                cid = f"{cid}-{pos or 'x'}"
            if cid in ids:
                dup += 1
                continue
            nxt += 1
            w = {"id": cid, "sr": sr, "tr": str(x["tr"]).strip(), "rank": nxt, "grp": (nxt - 1) // gs + 1}
            key = x.get("lemma") or lex.lemma(sr)[0]
            if key != norm(sr):
                w["lemma"] = key
            if pos:
                w["pos"] = pos
            for k in ("gender", "forms", "accent", "asp"):
                v = x.get(k) or d.get(k)
                if v:
                    w[k] = v
            note = " ".join(t for t in (d.get("note") if d.get("note") and d.get("note") not in str(x.get("note", "")) else "", x.get("note", "")) if t)
            if note:
                w["note"] = note.strip()
            src = [s for s in (x.get("src") or ["manual"]) if s in ("base", "my", "sit", "manual")]
            w["src"] = src or ["manual"]
            for k in ("sit", "my"):
                if x.get(k):
                    w[k] = [slug(s) if k == "sit" else str(s) for s in x[k]]
            ex = _clean_ex(x.get("ex"), warn, sr)
            if ex:
                w["ex"] = ex
            w["round"] = rnd
            if x.get("pair_sr") or d.get("pair_sr"):
                pending_pairs.append((w, x.get("pair_sr") or d.get("pair_sr")))
            deck["words"].append(w)
            ids[cid] = w
            seen.add((norm(sr), pos))
            added += 1
        by_sr = {norm(w["sr"]): w["id"] for w in deck["words"]}
        for w, p in pending_pairs:   # the partner may come in a later round: linked as soon as it exists
            if norm(p) in by_sr:
                w["pair"] = by_sr[norm(p)]
                other = next(o for o in deck["words"] if o["id"] == by_sr[norm(p)])
                other.setdefault("pair", w["id"])
        for w in deck["words"]:   # older cards whose partner just arrived
            if not w.get("pair"):
                p = (det.get(w["sr"]) or {}).get("pair_sr")
                if p and norm(p) in by_sr:
                    w["pair"] = by_sr[norm(p)]
        deck["rounds"] = max(int(deck.get("rounds", 0)), rnd)
    elif kind == "phrases":
        have = {p["id"] for p in deck["phrases"]}
        by_sr = {norm(w["sr"]): w["id"] for w in deck["words"]}
        from sr_lemma import load as _load
        lex = _load()
        for x in items:
            sr = to_latin(str(x["sr"]).strip())
            pid = "p:" + slug(sr)[:60].strip("-")
            if pid in have:
                dup += 1
                continue
            p = {"id": pid, "sr": sr, "tr": str(x["tr"]).strip()}
            if x.get("sit"):
                p["sit"] = [slug(s) for s in x["sit"]]
            ws = []
            for t in tokens(sr):
                k = lex.lemma(t)[0]
                wid = by_sr.get(norm(lex.word(k))) or by_sr.get(norm(t))
                if wid and wid not in ws:
                    ws.append(wid)
            if ws:
                p["words"] = ws
            for k in ("note", "from"):
                if x.get(k):
                    p[k] = str(x[k])
            p["round"] = rnd
            deck["phrases"].append(p)
            have.add(pid)
            added += 1
    elif kind == "cloze":
        have = {c["id"] for c in deck["cloze"]}
        by_sr = {norm(w["sr"]): w["id"] for w in deck["words"]}
        ids = {w["id"] for w in deck["words"]}
        for x in items:
            sr = to_latin(str(x["sr"]).strip())
            if "{" not in sr:
                raise Fail(f"! cloze without {{form}}: {sr}")
            wid = x.get("word") if x.get("word") in ids else by_sr.get(norm(str(x.get("word", ""))))
            if not wid:
                raise Fail(f"! cloze {sr}: the word {x.get('word')} is not in the deck")
            cid = "c:" + slug(sr.replace("{", "").replace("}", ""))[:60].strip("-")
            if cid in have:
                dup += 1
                continue
            c = {"id": cid, "sr": sr, "tr": str(x["tr"]).strip(), "word": wid, "round": rnd}
            for k in ("case", "hint"):
                if x.get(k):
                    c[k] = x[k]
            if x.get("opts"):
                c["opts"] = [to_latin(str(o)) for o in x["opts"]]
            deck["cloze"].append(c)
            have.add(cid)
            added += 1
    else:
        raise Fail(f"! unknown kind {kind}")
    deck["built"] = dt.date.today().isoformat()
    write_yaml(deck_path(root), deck, SCHEMA)
    if score:
        from score_words import rescore
        rescore(root, quiet=True)
    print(f"{kind}: +{added} (round {rnd}), duplicates skipped: {dup}" +
          (f" · examples without translation dropped: {len(warn)} ({', '.join(sorted(set(warn))[:6])})" if warn else ""))
    rebuild(root)
    return 0


# ---------- rounds ----------
def round_summary(root: Path) -> int:
    deck = load_deck(root)
    if not deck["words"]:
        print("no cards yet")
        return 0
    rnd = max((w.get("round", 1) for w in deck["words"]), default=1)
    ws = [w for w in deck["words"] if w.get("round", 1) == rnd and not w.get("retired")]
    known, checked = known_ids(root)
    c = [w for w in ws if w["id"] in checked]
    k = [w for w in c if w["id"] in known]
    share = len(k) / len(c) if c else 0.0
    res = {"round": rnd, "cards": len(ws), "checked": len(c), "known": len(k), "share": round(share, 3)}
    if len(c) < len(ws):
        res["next"] = "check"
        msg = f"round {rnd}: checked {len(c)} of {len(ws)} — finish the check on the Vocabulary tab"
    elif share >= 0.8:
        res["next"] = "deeper"
        msg = f"round {rnd}: you know {share:.0%} — go deeper: next round ≈400 words further down the list"
    elif share >= 0.5:
        res["next"] = "smaller"
        msg = f"round {rnd}: you know {share:.0%} — one more, smaller round ≈200"
    else:
        res["next"] = "learn"
        msg = f"round {rnd}: you know {share:.0%} — the boundary is found: learn these, no more rounds for now"
    print(msg)
    print("ROUND " + json.dumps(res))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--n", type=int, default=None)
    c.add_argument("--out", default=None)
    a = sub.add_parser("add")
    a.add_argument("draft")
    a.add_argument("--kind", default="words", choices=["words", "phrases", "cloze"])
    a.add_argument("--round", type=int, default=None)
    a.add_argument("--no-score", action="store_true")
    sub.add_parser("round")
    k = sub.add_parser("known")
    k.add_argument("--json", action="store_true")
    sub.add_parser("seen")
    r = sub.add_parser("retire")
    r.add_argument("ids", nargs="+")
    st = sub.add_parser("set")
    st.add_argument("id")
    st.add_argument("pairs", nargs="+")
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    if args.cmd == "candidates":
        return candidates(root, args.n, Path(args.out) if args.out else None)
    if args.cmd == "add":
        return add(root, Path(args.draft), args.kind, args.round, not args.no_score)
    if args.cmd == "round":
        return round_summary(root)
    if args.cmd == "known":
        ks = known_lemmas(root)
        print(json.dumps(ks, ensure_ascii=False) if args.json else "\n".join(x["sr"] for x in ks))
        return 0
    if args.cmd == "seen":
        print("\n".join(w["sr"] for w in load_deck(root)["words"]))
        return 0
    deck = load_deck(root)
    if args.cmd == "set":
        from prepio import apply, parse_pairs
        pairs = parse_pairs(args.pairs)
        bad = [k for k in pairs if k in ("id", "rank", "grp", "round")]
        if bad:
            raise Fail(f"! {', '.join(bad)} cannot be set by hand")
        card = next((c for c in deck["words"] + deck["phrases"] + deck["cloze"] if c["id"] == args.id), None)
        if not card:
            raise Fail(f"! no card {args.id}")
        apply(card, pairs)
        write_yaml(deck_path(root), deck, SCHEMA)
        print(f"{args.id}: " + ", ".join(pairs))
        rebuild(root)
        return 0
    n = 0
    for w in deck["words"] + deck["phrases"] + deck["cloze"]:
        if w["id"] in args.ids:
            w["retired"] = True
            n += 1
    write_yaml(deck_path(root), deck, SCHEMA)
    print(f"retired {n}")
    rebuild(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
