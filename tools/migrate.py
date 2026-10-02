#!/usr/bin/env python3
"""Data-format versions and migrations — updates never lose progress.

    run migrate.py --dir . --init          # a new folder: record plugin and data versions in prep/session.yaml
    run migrate.py --dir . --check         # JSON: {plugin_folder, plugin_now, data_folder, data_now, needs}
    run migrate.py --dir .                 # backup → step-by-step migrations → validation; rollback on failure

DATA_VERSION grows when the format of prep/ changes; each step below upgrades by one. A step never
renames a card id: progress is tied to ids. After migrating, the deck is validated against its schema
and the number of cards with progress is compared; a mismatch rolls the folder back from the backup.

Steps:
  1 → 2  (reserved for the first format change; v0.1.0 writes data version 1)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import REPO, Fail, read_yaml, validate, write_yaml  # noqa: E402

DATA_VERSION = 1
STEPS: dict[int, callable] = {}   # {from_version: function(root)}


def plugin_version() -> str:
    return json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())["version"]


def session(root: Path) -> dict:
    return read_yaml(root / "prep" / "session.yaml", {}) or {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    s = session(root)
    if a.init:
        s.setdefault("workspace", str(root))
        s["plugin_version"], s["data_version"] = plugin_version(), DATA_VERSION
        write_yaml(root / "prep" / "session.yaml", s)
        print(f"init: plugin {s['plugin_version']}, data {DATA_VERSION}")
        return 0
    have = int(s.get("data_version", DATA_VERSION))
    info = {"plugin_folder": s.get("plugin_version"), "plugin_now": plugin_version(), "data_folder": have, "data_now": DATA_VERSION,
            "needs": have < DATA_VERSION or s.get("plugin_version") != plugin_version()}
    if a.check:
        print(json.dumps(info))
        return 0
    from backup import make
    from state import counts
    before = counts(root)
    bk = make(root, f"before-{plugin_version()}")
    try:
        v = have
        while v < DATA_VERSION:
            if v not in STEPS:
                raise Fail(f"! no migration step from data version {v}")
            STEPS[v](root)
            v += 1
        deck = read_yaml(root / "prep" / "words.yaml", None)
        if deck:
            validate(deck, "words.schema.json", "prep/words.yaml")
        after = counts(root)
        if after["cards"] < before["cards"] or after["log"] < before["log"]:
            raise Fail(f"! progress shrank during migration: {before} → {after}")
    except SystemExit as e:
        for p in bk.glob("*"):
            if p.is_file():
                shutil.copy2(p, root / "prep" / p.name)
        print(f"ROLLBACK from {bk.name}: {e}")
        return 1
    s = session(root)
    s["plugin_version"], s["data_version"] = plugin_version(), DATA_VERSION
    write_yaml(root / "prep" / "session.yaml", s)
    print(f"MIGRATED data {have} → {DATA_VERSION}, plugin {info['plugin_folder']} → {plugin_version()} (backup {bk.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
