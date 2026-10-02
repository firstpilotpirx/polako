#!/usr/bin/env python3
"""Backups of the learner's folder — before every update and on request.

    run backup.py --dir . make [--label before-0.2.0]     # → prep/backups/<time>-<label>/
    run backup.py --dir . list
    run backup.py --dir . restore <name>                  # puts the files back (the current state is backed up first)

What is copied: prep/*.yaml, prep/*.json (deck, situations, profile, progress, review log, vocab
check, inbox), my/ (own texts). Not copied: dist/ (rebuilt), the data cache (downloadable).
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import Fail  # noqa: E402


def make(root: Path, label: str = "") -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = root / "prep" / "backups" / (stamp + (f"-{label}" if label else ""))
    dest.mkdir(parents=True, exist_ok=True)
    for p in (root / "prep").glob("*"):
        if p.is_file() and p.suffix in (".yaml", ".json", ".txt"):
            shutil.copy2(p, dest / p.name)
    if (root / "my").is_dir():
        shutil.copytree(root / "my", dest / "my", dirs_exist_ok=True)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--label", default="")
    sub.add_parser("list")
    r = sub.add_parser("restore")
    r.add_argument("name")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    bdir = root / "prep" / "backups"
    if a.cmd == "make":
        print(f"BACKUP {make(root, a.label)}")
    elif a.cmd == "list":
        for p in sorted(bdir.glob("*")) if bdir.exists() else []:
            print(p.name)
    else:
        src = bdir / a.name
        if not src.is_dir():
            raise Fail(f"! no backup {a.name}")
        safety = make(root, "before-restore")
        for p in src.glob("*"):
            if p.is_file():
                shutil.copy2(p, root / "prep" / p.name)
        if (src / "my").is_dir():
            shutil.copytree(src / "my", root / "my", dirs_exist_ok=True)
        print(f"restored {a.name} (the state before is in {safety.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
