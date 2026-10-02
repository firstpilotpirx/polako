#!/usr/bin/env python3
"""Writing the learner's state — instead of editing YAML by hand.

    run state.py --dir . profile set level=a1 goal=15 'situations=["pekara","mup"]'
    run state.py --dir . profile get [key]
    run state.py --dir . wizard step level --answer level=a1        # wizard step done (+ answers into the profile)
    run state.py --dir . wizard skip interests
    run state.py --dir . wizard finish
    run state.py --dir . wizard status                               # done / skipped / next step (JSON)
    run state.py --dir . session set mode=local page_url=http://localhost:8790/ built_at=now
    run state.py --dir . session get [key]
    run state.py --dir . page import --trainer t.json --log l.json --vocab v.json --inbox i.json
    run state.py --dir . page export                                 # what to write back into the artifact's db
    run state.py --dir . page counts

Files: prep/profile.yaml (schema-checked), prep/session.yaml, and the page's progress:
prep/trainer-state.json, prep/review-log.json, prep/vocab-state.json, prep/inbox.json.

`page import` takes what the ArtifactData tool returned (a document — an object or {data: …}; a
collection — a list of {id, data} or an object {id: data}) and normalizes it. The log collection holds
one document per day ({day, items}); they are flattened and merged with the file (no duplicates).
Empty or broken input never overwrites progress; fewer cards than before is reported.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import Fail, apply, parse_pairs, read_json, read_yaml, rebuild, write_json, write_yaml  # noqa: E402

WIZARD = ["explain", "why", "level", "situations", "texts", "goal", "listening", "data", "first-round"]
PROFILE_KEYS = {"explain", "level", "goal", "retention", "listening", "typing", "situations", "interests", "why", "started"}


def load_profile(root: Path) -> dict:
    return read_yaml(root / "prep" / "profile.yaml", None) or {"version": 1, "explain": "ru", "goal": 15, "retention": 0.9,
                                                              "listening": True, "typing": False, "started": dt.date.today().isoformat()}


def save_profile(root: Path, prof: dict) -> None:
    write_yaml(root / "prep" / "profile.yaml", prof, "profile.schema.json")


def profile_cmd(root, a):
    prof = load_profile(root)
    if a.op == "get":
        print(json.dumps(prof.get(a.key) if a.key else prof, ensure_ascii=False, default=str))
        return
    pairs = parse_pairs(a.pairs)
    bad = [k for k in pairs if k not in PROFILE_KEYS]
    if bad:
        raise Fail(f"! unknown profile keys: {', '.join(bad)} (known: {', '.join(sorted(PROFILE_KEYS))})")
    save_profile(root, apply(prof, pairs))
    print("profile:", ", ".join(f"{k}={v}" for k, v in pairs.items()))
    if not a.no_build:
        rebuild(root)


def wizard_cmd(root, a):
    prof = load_profile(root)
    wz = prof.setdefault("wizard", {"done": [], "skipped": []})
    if a.op == "status":
        nxt = next((s for s in WIZARD if s not in wz["done"] and s not in wz.get("skipped", [])), None)
        print(json.dumps({"done": wz["done"], "skipped": wz.get("skipped", []), "next": nxt, "finished": bool(wz.get("finished"))}, ensure_ascii=False))
        return
    if a.op == "finish":
        wz["finished"] = True
    else:
        if a.step not in WIZARD:
            raise Fail(f"! unknown wizard step {a.step}; steps: {', '.join(WIZARD)}")
        lst = wz.setdefault("done" if a.op == "step" else "skipped", [])
        if a.step not in lst:
            lst.append(a.step)
        if a.answer:
            pairs = parse_pairs(a.answer)
            bad = [k for k in pairs if k not in PROFILE_KEYS]
            if bad:
                raise Fail(f"! unknown profile keys: {', '.join(bad)}")
            apply(prof, pairs)
    save_profile(root, prof)
    print(f"wizard: {a.op} {getattr(a, 'step', '') or ''}".strip())


def session_cmd(root, a):
    p = root / "prep" / "session.yaml"
    s = read_yaml(p, {}) or {}
    if a.op == "get":
        print(json.dumps(s.get(a.key) if a.key else s, ensure_ascii=False, default=str))
        return
    pairs = parse_pairs(a.pairs)
    if pairs.get("built_at") == "now":
        pairs["built_at"] = int(time.time())
    write_yaml(p, apply(s, pairs))
    print("session:", ", ".join(f"{k}={v}" for k, v in pairs.items()))


def _doc(x):
    if isinstance(x, dict) and set(x) <= {"data", "id", "exists"} and isinstance(x.get("data"), dict):
        return x["data"]
    return x


def _coll(x):
    if isinstance(x, list):
        out = {}
        for it in x:
            if isinstance(it, dict) and "id" in it:
                out[it["id"]] = it.get("data", {k: v for k, v in it.items() if k != "id"})
        return out
    if isinstance(x, dict):
        return {k: _doc(v) for k, v in x.items()}
    return {}


def counts(root: Path) -> dict:
    prep = root / "prep"
    t = read_json(prep / "trainer-state.json", {}) or {}
    v = read_json(prep / "vocab-state.json", {}) or {}
    log = read_json(prep / "review-log.json", []) or []
    checked = set()
    for rec in v.values():
        if isinstance(rec, dict) and not rec.get("reset"):
            checked |= set(rec.get("known", [])) | set(rec.get("unknown", []))
    return {"cards": len(t.get("cards") or {}), "log": len(log), "vocab_checked": len(checked)}


def page_cmd(root, a):
    prep = root / "prep"
    if a.op == "counts":
        print(json.dumps(counts(root), ensure_ascii=False))
        return
    if a.op == "export":
        log = read_json(prep / "review-log.json", []) or []
        by_day: dict[str, list] = {}
        for x in log:
            by_day.setdefault(dt.datetime.fromtimestamp(x[0] / 1000).strftime("%Y-%m-%d"), []).append(x)
        print(json.dumps({
            "doc trainer/state": read_json(prep / "trainer-state.json", {}),
            "collection vocab": read_json(prep / "vocab-state.json", {}),
            "collection log": {d: {"day": d, "items": items} for d, items in by_day.items()},
        }, ensure_ascii=False))
        return
    before = counts(root)
    if a.trainer:
        raw = read_json(Path(a.trainer), None)
        data = _doc(raw) if raw else None
        if isinstance(data, dict) and data.get("cards"):
            write_json(prep / "trainer-state.json", data)
            print("  trainer → prep/trainer-state.json")
        else:
            print("  trainer: empty — leaving the file untouched")
    if a.log:
        raw = read_json(Path(a.log), None)
        days = _coll(raw) if raw else {}
        items = [x for d in days.values() if isinstance(d, dict) for x in d.get("items", [])]
        if items:
            old = read_json(prep / "review-log.json", []) or []
            have = {(x[0], x[1]) for x in old}
            merged = sorted(old + [x for x in items if (x[0], x[1]) not in have], key=lambda x: x[0])
            write_json(prep / "review-log.json", merged, indent=None)
            print(f"  log → prep/review-log.json (+{len(merged) - len(old)})")
    if a.vocab:
        raw = read_json(Path(a.vocab), None)
        data = _coll(raw) if raw else {}
        if data:
            write_json(prep / "vocab-state.json", data)
            print("  vocab → prep/vocab-state.json")
    if a.inbox:
        raw = read_json(Path(a.inbox), None)
        data = list(_coll(raw).values()) if isinstance(raw, (list, dict)) and raw and (isinstance(raw, dict) or "data" in raw[0]) else (raw or [])
        if data:
            old = read_json(prep / "inbox.json", []) or []
            seen = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in old}
            old += [x for x in data if json.dumps(x, sort_keys=True, ensure_ascii=False) not in seen]
            write_json(prep / "inbox.json", old)
            print("  inbox → prep/inbox.json")
    after = counts(root)
    shrink = [k for k in before if after.get(k, 0) < before[k]]
    if shrink:
        print("! the page has less than the files had: " + ", ".join(f"{k} {before[k]}→{after[k]}" for k in shrink)
              + ". The previous state is in prep/backups; check that this is the right page.")
    print("counts:", json.dumps(after, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--no-build", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile")
    p.add_argument("op", choices=["set", "get"])
    p.add_argument("pairs", nargs="*")
    p.add_argument("--key", default=None)
    w = sub.add_parser("wizard")
    w.add_argument("op", choices=["step", "skip", "finish", "status"])
    w.add_argument("step", nargs="?")
    w.add_argument("--answer", nargs="*")
    s = sub.add_parser("session")
    s.add_argument("op", choices=["set", "get"])
    s.add_argument("pairs", nargs="*")
    s.add_argument("--key", default=None)
    g = sub.add_parser("page")
    g.add_argument("op", choices=["import", "export", "counts"])
    for k in ("trainer", "log", "vocab", "inbox"):
        g.add_argument(f"--{k}")
    a = ap.parse_args()
    a.no_build = getattr(a, "no_build", False)
    root = Path(a.dir).expanduser().resolve()
    if a.cmd in ("profile", "session") and a.op == "get" and a.pairs and not a.key:
        a.key = a.pairs[0]
    {"profile": profile_cmd, "wizard": wizard_cmd, "session": session_cmd, "page": page_cmd}[a.cmd](root, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
