#!/usr/bin/env python3
"""Life situations of the person — prep/situations.yaml. No manual editing.

    run situations.py --dir ~/polako catalog                 # the bundled catalog (ids, titles, default priority)
    run situations.py --dir ~/polako add draft.yaml          # add situations / dialogs from a draft
    run situations.py --dir ~/polako list                    # what is there: dialogs, lines, cards linked
    run situations.py --dir ~/polako set mup pri=1 title="МУП"

Draft for `add` — a YAML list of situations (or {situations: [...]}):

  - id: pekara                     # catalog id or a new slug
    title: Пекарня                 # optional when the id is in the catalog
    pri: 1
    dialogs:
      - id: pekara-1
        title: Покупаю бурек
        lines:
          - {who: they, sr: "Dobar dan, izvolite.", tr: "Добрый день, слушаю вас."}
          - {who: me,   sr: "Jedan burek sa sirom, molim.", tr: "Один бурек с сыром, пожалуйста."}

A situation that exists is merged: new dialogs are appended, a dialog with the same id is kept as is
(--replace overwrites it). Lines are short and real: what a cashier, a clerk or a neighbour actually says.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import BUNDLED, Fail, apply, parse_pairs, read_yaml, rebuild, write_yaml  # noqa: E402
from translit import slug, to_latin  # noqa: E402

SCHEMA = "situations.schema.json"


def catalog() -> dict:
    cat = read_yaml(BUNDLED / "situations_catalog.yaml", {}) or {}
    return {it["id"]: {**it, "group": g["id"]} for g in cat.get("groups", []) for it in g.get("items", [])}


def path(root: Path) -> Path:
    return root / "prep" / "situations.yaml"


def load_sit(root: Path) -> dict:
    return read_yaml(path(root), {"version": 1, "situations": []}) or {"version": 1, "situations": []}


def add(root: Path, draft: Path, replace: bool) -> int:
    data = load_sit(root)
    items = read_yaml(draft, [])
    if isinstance(items, dict):
        items = items.get("situations", [])
    cat = catalog()
    by_id = {s["id"]: s for s in data["situations"]}
    added = dialogs = 0
    for it in items:
        sid = slug(it.get("id") or it.get("title", ""))
        if not sid:
            raise Fail(f"! a situation without id: {it}")
        c = cat.get(sid, {})
        cur = by_id.get(sid)
        if cur is None:
            cur = {"id": sid, "title": it.get("title") or c.get("title") or sid, "pri": int(it.get("pri") or c.get("pri") or 2)}
            if it.get("title_sr") or c.get("title_sr"):
                cur["title_sr"] = it.get("title_sr") or c.get("title_sr")
            if it.get("desc"):
                cur["desc"] = it["desc"]
            data["situations"].append(cur)
            by_id[sid] = cur
            added += 1
        dl = cur.setdefault("dialogs", [])
        have = {d["id"]: i for i, d in enumerate(dl)}
        for n, d in enumerate(it.get("dialogs") or [], 1):
            did = slug(d.get("id") or f"{sid}-{len(dl) + 1}")
            lines = [{"who": ln["who"], "sr": to_latin(str(ln["sr"]).strip()), "tr": str(ln["tr"]).strip()} for ln in d.get("lines", [])]
            nd = {"id": did, **({"title": d["title"]} if d.get("title") else {}), "lines": lines}
            if did in have:
                if replace:
                    dl[have[did]] = nd
                    dialogs += 1
                continue
            dl.append(nd)
            dialogs += 1
        if not dl:
            cur.pop("dialogs", None)
    data["situations"].sort(key=lambda s: (s["pri"], s["id"]))
    write_yaml(path(root), data, SCHEMA)
    print(f"situations: +{added} new, +{dialogs} dialogs · total {len(data['situations'])}")
    rebuild(root)
    return 0


def list_(root: Path) -> int:
    data = load_sit(root)
    deck = read_yaml(root / "prep" / "words.yaml", {}) or {}
    for s in data["situations"]:
        nw = sum(1 for w in deck.get("words", []) if s["id"] in (w.get("sit") or []))
        nph = sum(1 for p in deck.get("phrases", []) if s["id"] in (p.get("sit") or []))
        lines = sum(len(d["lines"]) for d in s.get("dialogs", []))
        print(f"{s['id']:<12} pri={s['pri']} {s['title']:<28} dialogs={len(s.get('dialogs', []))} lines={lines} words={nw} phrases={nph}")
    if not data["situations"]:
        print("no situations yet")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalog")
    a = sub.add_parser("add")
    a.add_argument("draft")
    a.add_argument("--replace", action="store_true")
    sub.add_parser("list")
    s = sub.add_parser("set")
    s.add_argument("id")
    s.add_argument("pairs", nargs="+")
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    if args.cmd == "catalog":
        for sid, it in catalog().items():
            print(f"{sid:<12} pri={it['pri']} {it['group']:<7} {it['title']} · {it.get('title_sr', '')}")
        return 0
    if args.cmd == "add":
        return add(root, Path(args.draft), args.replace)
    if args.cmd == "list":
        return list_(root)
    data = load_sit(root)
    for sit in data["situations"]:
        if sit["id"] == args.id:
            apply(sit, parse_pairs(args.pairs))
            write_yaml(path(root), data, SCHEMA)
            rebuild(root)
            print(f"{args.id}: updated")
            return 0
    raise Fail(f"! no situation {args.id}")


if __name__ == "__main__":
    sys.exit(main())
