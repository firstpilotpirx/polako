#!/usr/bin/env python3
"""Checks of the learner's data — run before publishing the page.

    run validate.py --dir ~/polako                  # errors → exit 1
    run validate.py --dir ~/polako --update-lock    # after a successful build: remember all card ids

Checks:
  · prep/words.yaml, prep/situations.yaml, prep/profile.yaml against their schemas;
  · card ids unique; every cloze points to an existing word; aspect pairs point both ways;
  · phrase and word situations exist in prep/situations.yaml;
  · NO CARD ID EVER DISAPPEARS: prep/ids.lock.json keeps every id ever published; a missing one means
    lost progress (retire a card instead of deleting it: words.py retire);
  · progress keys in prep/trainer-state.json that point to no card (reported, not an error).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import read_json, read_yaml, validate, write_json  # noqa: E402


def check(root: Path) -> tuple[list[str], list[str], set]:
    errs, warns = [], []
    prep = root / "prep"
    deck = read_yaml(prep / "words.yaml", None)
    sits = read_yaml(prep / "situations.yaml", None)
    prof = read_yaml(prep / "profile.yaml", None)
    for data, schema, name in ((deck, "words.schema.json", "words.yaml"), (sits, "situations.schema.json", "situations.yaml"), (prof, "profile.schema.json", "profile.yaml")):
        if data is not None:
            try:
                validate(data, schema, name)
            except SystemExit as e:
                errs.append(str(e))
    ids: set = set()
    if deck:
        allc = deck.get("words", []) + deck.get("phrases", []) + deck.get("cloze", [])
        for c in allc:
            if c["id"] in ids:
                errs.append(f"duplicate id {c['id']}")
            ids.add(c["id"])
        wids = {w["id"]: w for w in deck.get("words", [])}
        for c in deck.get("cloze", []):
            if c.get("word") not in wids:
                errs.append(f"{c['id']}: word {c.get('word')} not in the deck")
        for w in wids.values():
            p = w.get("pair")
            if p and p not in wids:
                errs.append(f"{w['id']}: aspect pair {p} not in the deck")
            elif p and wids[p].get("pair") != w["id"]:
                warns.append(f"{w['id']} ↔ {p}: the pair points one way only")
        sit_ids = {s["id"] for s in (sits or {}).get("situations", [])}
        for c in deck.get("words", []) + deck.get("phrases", []):
            for s in c.get("sit", []):
                if s not in sit_ids:
                    warns.append(f"{c['id']}: situation {s} is not in situations.yaml")
    lock = read_json(prep / "ids.lock.json", {}) or {}
    gone = sorted(set(lock.get("ids", [])) - ids)
    if gone:
        errs.append(f"{len(gone)} card ids disappeared (progress would be lost): {', '.join(gone[:8])} — retire cards instead of deleting")
    st = read_json(prep / "trainer-state.json", {}) or {}
    orphan = {k.split("|")[0] for k in (st.get("cards") or {})} - ids
    orphan = {o for o in orphan if not o.startswith(("v:", "d:"))}
    if orphan:
        warns.append(f"progress for {len(orphan)} ids not in the deck: {', '.join(sorted(orphan)[:6])}")
    return errs, warns, ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--update-lock", action="store_true")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    errs, warns, ids = check(root)
    for w in warns:
        print("warn:", w)
    for e in errs:
        print("ERROR:", e)
    if errs:
        return 1
    if a.update_lock:
        lp = root / "prep" / "ids.lock.json"
        lock = read_json(lp, {}) or {}
        write_json(lp, {"ids": sorted(set(lock.get("ids", [])) | ids)})
        print(f"lock: {len(ids)} ids")
    print(f"ok: {len(ids)} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
