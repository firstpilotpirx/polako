#!/usr/bin/env python3
"""Step 2 of the vocabulary method: frequency of the person's OWN material — their texts and situations.

    run text_freq.py --dir ~/polako                     # → prep/my-freq.yaml
    run text_freq.py --dir ~/polako --top 30            # + print the top 30
    run text_freq.py --dir ~/polako extra.txt           # + more files, counted as "my" texts

Sources (all optional — an empty folder gives an empty list):
  my/*.txt, my/*.md           texts the person actually gets: Viber messages, the landlord's letter, a
                              rental contract, a menu, a notice in the building. Front matter is allowed:
                                ---
                                title: Сообщение от хозяйки
                                from: viber
                                ---
  prep/situations.yaml        dialogs and phrases of the person's situations (bakery, bank, MUP…)

Per lemma: n (all), my (in own texts), sit (in situations), src (source ids where it occurs),
how (lemmatizer route), ex — up to 2 short sentences from the person's own texts that contain it
(the best possible examples: they are about the person's life). Code, URLs and e-mails are skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import read_yaml, write_yaml  # noqa: E402
from sr_lemma import load  # noqa: E402
from translit import sentences, slug, tokens  # noqa: E402

FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def read_text_file(p: Path) -> tuple[dict, str]:
    raw = p.read_text(encoding="utf-8", errors="replace")
    meta = {}
    m = FRONT.match(raw)
    if m:
        try:
            import yaml
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            meta = {}
        raw = raw[m.end():]
    if not meta.get("title"):
        first = raw.strip().splitlines()[0] if raw.strip() else p.stem
        meta["title"] = first.lstrip("# ").strip()[:60] if first.startswith("#") else p.stem
    return meta, raw


def read_corpus(root: Path, extra: list[str] | None = None) -> list[dict]:
    """Every text of the person: [{id, kind: my|sit, title, text}]."""
    out = []
    my = root / "my"
    if my.is_dir():
        for p in sorted(list(my.glob("*.txt")) + list(my.glob("*.md"))):
            meta, text = read_text_file(p)
            out.append({"id": "my." + slug(p.stem), "kind": "my", "title": str(meta.get("title")), "text": text,
                        "file": str(p.relative_to(root)), "from": meta.get("from", "")})
    for x in extra or []:
        p = Path(x).expanduser()
        if p.exists():
            meta, text = read_text_file(p)
            out.append({"id": "my." + slug(p.stem), "kind": "my", "title": str(meta.get("title")), "text": text, "file": str(p)})
    sit = read_yaml(root / "prep" / "situations.yaml", {}) or {}
    for s in sit.get("situations", []):
        lines = []
        for dlg in s.get("dialogs", []):
            lines += [ln.get("sr", "") for ln in dlg.get("lines", [])]
        lines += [ph.get("sr", "") if isinstance(ph, dict) else str(ph) for ph in s.get("phrases", [])]
        if lines:
            out.append({"id": "sit." + s["id"], "kind": "sit", "title": s.get("title", s["id"]), "text": "\n".join(lines)})
    return out


def analyze(root: Path, extra: list[str] | None = None) -> dict:
    lex = load()
    corpus = read_corpus(root, extra)
    agg: dict[str, dict] = {}
    sources = []
    for doc in corpus:
        toks = tokens(doc["text"])
        sources.append({"id": doc["id"], "kind": doc["kind"], "title": doc["title"], "tokens": len(toks),
                        **({"file": doc["file"]} if doc.get("file") else {})})
        sents = sentences(doc["text"])
        for t in toks:
            lem, how = lex.lemma(t)
            if len(lem) < 2 and how == "self":
                continue
            a = agg.setdefault(lem, {"n": 0, "my": 0, "sit": 0, "src": [], "how": how, "ex": []})
            a["n"] += 1
            a[doc["kind"]] += 1
            if doc["id"] not in a["src"]:
                a["src"].append(doc["id"])
            if how == "lex":
                a["how"] = "lex"
        if doc["kind"] == "my":   # examples come only from the person's own texts
            for s in sorted(sents, key=len):
                if len(s) > 140 or len(s) < 8:
                    continue
                for t in set(tokens(s)):
                    lem, _ = lex.lemma(t)
                    a = agg.get(lem)
                    if a is not None and len(a["ex"]) < 2 and all(e["sr"] != s for e in a["ex"]):
                        a["ex"].append({"sr": s, "from": doc["id"]})
    rows = []
    for lem, a in agg.items():
        info = lex.info(lem)
        row = {"l": lem, "sr": info.get("l", lex.word(lem)), "n": a["n"], "my": a["my"], "sit": a["sit"],
               "src": a["src"], "how": a["how"]}
        if info.get("pos"):
            row["pos"] = info["pos"]
        if a["ex"]:
            row["ex"] = a["ex"]
        rows.append(row)
    rows.sort(key=lambda r: (-r["my"] * 2 - r["sit"], r["sr"]))
    return {"version": 1, "built": dt.date.today().isoformat(), "sources": sources, "lemmas": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    res = analyze(root, args.files)
    out = Path(args.out) if args.out else root / "prep" / "my-freq.yaml"
    write_yaml(out, res)
    my_tok = sum(s["tokens"] for s in res["sources"] if s["kind"] == "my")
    sit_tok = sum(s["tokens"] for s in res["sources"] if s["kind"] == "sit")
    print(f"texts: {sum(1 for s in res['sources'] if s['kind'] == 'my')} ({my_tok} words) · "
          f"situations: {sum(1 for s in res['sources'] if s['kind'] == 'sit')} ({sit_tok} words) · lemmas: {len(res['lemmas'])}")
    for r in res["lemmas"][: args.top]:
        print(f"  {r['sr']:<16} my={r['my']:<3} sit={r['sit']:<3} {r['how']:<7} {', '.join(r['src'][:3])}")
    print(f"MYFREQ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
