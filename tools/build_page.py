#!/usr/bin/env python3
"""Build the Polako page from the person's files and templates/portal/.

    run build_page.py --dir ~/polako               # → dist/index.html (+ dist/artifact.html, dist/version.json)
    run build_page.py --dir examples/sample --out /tmp/polako.html

Reads (relative to --dir; everything is optional — an empty folder gives a page with placeholders):
  prep/profile.yaml       level, explanation language, goal, retention, listening, typing
  prep/words.yaml         the deck: words, phrases, cloze
  prep/situations.yaml    situations with dialogs
  my/*.txt                the person's own texts — shown with known / learning / new words highlighted
  prep/my-freq.yaml       (for coverage of own texts)
  <data cache>/base-freq.json   (for coverage of spoken Serbian)
  prep/i18n.<lang>.json   UI strings for an explanation language other than Russian

Embedded for the page: the deck (only the fields the page uses), situations, own texts as tokens linked
to card ids, coverage shares per card (spoken: the lemma's share of all subtitle words; own texts: its
count), and a form → card map for checking a pasted text right on the page. Progress is NOT in the
page: it lives in prep/trainer-state.json (local server), the artifact's db or the person's GitHub repository,
so a rebuild never loses it. A folder with polako.json is a data repository for the public site: the build
also writes deck.json there (the same data, read by https://<owner>.github.io/polako).
The template is never edited for one person: everything personal is data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import REPO, data_dir, read_json, read_yaml, write_json, write_text  # noqa: E402

PORTAL = REPO / "templates" / "portal"
JS_ORDER = ["core.js", "fsrs.js", "tts.js", "trainer.js", "trainer_ui.js", "views.js", "stats.js", "ghstore.js", "boot.js"]
WORD_FIELDS = ("id", "sr", "tr", "pos", "gender", "forms", "accent", "asp", "pair", "rank", "grp", "zipf", "band", "sit", "note", "ex", "retired", "round")
TOKEN = re.compile(r"([^\W\d_]+)|([\W\d_]+)", re.U)


def plugin_version() -> str:
    try:
        return json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())["version"]
    except Exception:
        return "0"


def ui_strings(root: Path, lang: str) -> dict:
    base = json.loads((PORTAL / "i18n.json").read_text(encoding="utf-8"))
    ui = dict(base.get("ru", {}))
    ui.update(base.get(lang, {}))
    extra = read_json(root / "prep" / f"i18n.{lang}.json", {}) or {}
    ui.update(extra)
    return ui


def build_data(root: Path) -> dict:
    prof = read_yaml(root / "prep" / "profile.yaml", {}) or {}
    deck = read_yaml(root / "prep" / "words.yaml", {}) or {}
    sits = read_yaml(root / "prep" / "situations.yaml", {}) or {}
    lang = prof.get("explain") or deck.get("explain") or "ru"
    words = [{k: w[k] for k in WORD_FIELDS if k in w} for w in deck.get("words", [])]
    data = {
        "title": "Polako",
        "profile": {k: prof[k] for k in ("explain", "level", "goal", "retention", "listening", "typing", "situations") if k in prof},
        "deck": {"words": words, "phrases": deck.get("phrases", []), "cloze": deck.get("cloze", []), "group_size": deck.get("group_size", 50)},
        "situations": [{k: s[k] for k in ("id", "title", "title_sr", "pri", "desc", "dialogs") if k in s} for s in sits.get("situations", [])],
        "texts": [], "forms": {}, "cov": {},
    }
    fp = read_json(root / "prep" / "fsrs-params.json", None)
    if isinstance(fp, dict) and isinstance(fp.get("w"), list) and len(fp["w"]) == 19:
        data["fsrs"] = {"w": fp["w"]}
    data["profile"].setdefault("explain", lang)
    if not words:
        return data
    try:
        from sr_lemma import load
        lex = load()
    except Exception as e:  # pragma: no cover - no data at all: the page still works, without highlights
        print(f"lexicon: {e}", file=sys.stderr)
        lex = None
    from translit import fold, norm, to_latin
    by_lemma: dict[str, str] = {}
    for w in deck.get("words", []):
        if w.get("retired"):
            continue
        by_lemma.setdefault(w.get("lemma", norm(w["sr"])), w["id"])
        by_lemma.setdefault(norm(w["sr"]), w["id"])

    def card_of(tok: str):
        if lex is None:
            return by_lemma.get(norm(tok))
        for lem in lex.candidates(tok):   # an ambiguous form goes to the lemma that is in the deck (stanu → stan, not stati)
            cid = by_lemma.get(lem) or by_lemma.get(lex.word(lem))
            if cid:
                return cid
        return None

    # form → card id, for checking a pasted text on the page
    forms: dict[str, str] = {}
    if lex is not None:
        for w in deck.get("words", []):
            if w.get("retired"):
                continue
            key = w.get("lemma", norm(w["sr"]))
            for f in [norm(w["sr"])] + lex.forms_of(key)[:40]:
                forms.setdefault(f, w["id"])
                forms.setdefault(fold(f), w["id"])
    data["forms"] = forms

    # own texts as tokens
    from text_freq import read_corpus
    my_counts: dict[str, int] = {}
    my_total = 0
    for doc in read_corpus(root):
        if doc["kind"] != "my":
            continue
        toks = []
        for m in TOKEN.finditer(to_latin(doc["text"].strip())):
            if m.group(1):
                word = m.group(1)
                cid = card_of(word)
                real = len(word) > 1 or word.lower() in ("i", "u", "a", "o", "s", "k")
                toks.append([word, cid, 1 if real else 0])
                if real:
                    my_total += 1
                    if cid:
                        my_counts[cid] = my_counts.get(cid, 0) + 1
            else:
                toks.append(m.group(2))
        data["texts"].append({"id": doc["id"], "title": doc["title"], "from": doc.get("from", ""), "tokens": toks})

    # coverage shares
    sp: dict[str, float] = {}
    bp = data_dir() / "base-freq.json"
    if bp.exists():
        base = json.loads(bp.read_text(encoding="utf-8"))
        tot = base.get("tokens") or 1
        n_of = {r["l"]: r["n"] for r in base["lemmas"]}
        for w in deck.get("words", []):
            n = n_of.get(w.get("lemma", norm(w["sr"])))
            if n:
                sp[w["id"]] = round(n / tot, 6)
    data["cov"] = {"sp": sp, "spCeil": round(sum(sp.values()), 4), "my": my_counts, "myTotal": my_total}
    return data


def app_js() -> str:
    js = "\n".join(f"/* ===== {f} ===== */\n" + (PORTAL / f).read_text(encoding="utf-8") for f in JS_ORDER)
    return js.replace("if (typeof module !== 'undefined' && module.exports) module.exports = FSRS;", "")


def render_page(payload: str, js: str, lang: str, title: str, head: str = "") -> str:
    page = (PORTAL / "template.html").read_text(encoding="utf-8")
    page = page.replace("{{TITLE}}", html.escape(title)).replace("{{CSS}}", (PORTAL / "page.css").read_text(encoding="utf-8"))
    page = page.replace("{{DATA}}", payload).replace("{{JS}}", js)
    return ("<!doctype html>\n<html lang=\"" + html.escape(lang) + "\">\n<head>\n<meta charset=\"utf-8\">\n" + head
            + page.replace("<header>", "</head>\n<body>\n<header>", 1) + "\n</body>\n</html>\n")


def deck_json(root: Path) -> dict:
    """The page data for the public site (deck.json in the person's data repository): no UI strings — the site has them."""
    data = build_data(root)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    data["build"] = {"id": hashlib.sha1(payload.encode()).hexdigest()[:12], "at": dt.datetime.now().isoformat(timespec="seconds"), "version": plugin_version()}
    return data


def build(root: Path, out: Path | None = None) -> Path:
    data = build_data(root)
    lang = data["profile"].get("explain", "ru")
    data["ui"] = ui_strings(root, lang)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    bid = hashlib.sha1((payload + "".join((PORTAL / f).read_text() for f in JS_ORDER + ["page.css", "template.html"])).encode()).hexdigest()[:12]
    data["build"] = {"id": bid, "at": dt.datetime.now().isoformat(timespec="seconds"), "version": plugin_version()}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = render_page(payload, app_js(), lang, data["title"])
    dist = root / "dist"
    target = out or dist / "index.html"
    write_text(target, page)
    if out is None and (root / "polako.json").exists():   # a data repository for the public site: refresh deck.json too
        write_text(root / "deck.json", json.dumps(deck_json(root), ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"DECK {root / 'deck.json'}")
    if out is None:
        write_text(dist / "artifact.html", page)
        write_json(dist / "version.json", data["build"])
        sess = root / "prep" / "session.yaml"
        if sess.exists():
            from prepio import write_yaml
            s = read_yaml(sess, {}) or {}
            s["built_at"] = int(dt.datetime.now().timestamp())
            write_yaml(sess, s)
    kb = len(page.encode()) // 1024
    print(f"PAGE {target} ({kb} KB) words={len(data['deck']['words'])} phrases={len(data['deck']['phrases'])} "
          f"situations={len(data['situations'])} texts={len(data['texts'])}")
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    build(Path(args.dir).expanduser().resolve(), Path(args.out) if args.out else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
