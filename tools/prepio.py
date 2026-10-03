"""Shared I/O for Polako files — so that all scripts write the same way.

- YAML in block style only, keys in original order, strings quoted where needed (yaml.safe_dump).
  The agent never hand-edits prep/ files: hand-written YAML caused silent errors in the past
  (split strings, yes/no as booleans), so every write goes through a script.
- Writes are atomic: to a temporary file alongside, then replace.
- Schema validation (schemas/*.json) if a schema exists: on error the file is not changed.
- Command-line values: `k=v`; v is parsed as JSON if it looks like JSON, otherwise a string. `k=` deletes the key.
- Shared paths: the plugin root, the schemas, and the data cache (downloaded corpora) in
  $POLAKO_DATA, by default ~/.local/share/polako/data — outside the plugin, survives updates.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCHEMAS = REPO / "schemas"
BUNDLED = REPO / "data"


def data_dir() -> Path:
    d = os.environ.get("POLAKO_DATA") or os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "polako", "data")
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


class Fail(SystemExit):
    pass


def read_yaml(p: Path, default=None):
    if not p.exists():
        return default
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return default if data is None else data


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Fail(f"! {p}: not JSON ({e})")


def _atomic(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, p)


def plain(o):
    """date → str etc., so that the schema and JSON see the same as the file."""
    return json.loads(json.dumps(o, default=str, ensure_ascii=False))


def validate(data, schema_name: str | None, where: str = "") -> None:
    if not schema_name:
        return
    sp = SCHEMAS / schema_name
    if not sp.exists():
        return
    import jsonschema
    schema = json.loads(sp.read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(plain(data)), key=lambda e: list(e.path))
    if errs:
        lines = [f"  {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errs[:10]]
        raise Fail(f"! {where or schema_name}: fails the schema, file not changed\n" + "\n".join(lines))


def write_yaml(p: Path, data, schema: str | None = None) -> None:
    validate(data, schema, str(p))
    _atomic(p, yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120, default_flow_style=False))


def write_json(p: Path, data, indent: int | None = 1) -> None:
    _atomic(p, json.dumps(data, ensure_ascii=False, indent=indent) + "\n")


def write_text(p: Path, text: str) -> None:
    _atomic(p, text)


def parse_value(v: str):
    v = v.strip()
    if v == "":
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?|true|false|null|\[.*\]|\{.*\}|\".*\"", v, re.S):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    return v


def parse_pairs(pairs: list[str]) -> dict:
    out = {}
    for p in pairs:
        if "=" not in p:
            raise Fail(f"! expected key=value: {p}")
        k, _, v = p.partition("=")
        out[k.strip()] = parse_value(v)
    return out


def apply(d: dict, pairs: dict) -> dict:
    for k, v in pairs.items():
        if v is None:
            d.pop(k, None)
        else:
            d[k] = v
    return d


def rebuild(root: Path) -> None:
    """Rebuild the page after writing (hub rule: after every step)."""
    import subprocess
    import sys
    subprocess.run([sys.executable, str(REPO / "tools" / "build_page.py"), "--dir", str(root)],
                   check=False, stdout=subprocess.DEVNULL)


def read_log(root: Path) -> list:
    """Every answer: prep/review-log.json (local server, artifact) plus prep/log/*.json (the public site writes one
    file per month into the person's repository); duplicates dropped, sorted by time."""
    prep = Path(root) / "prep"
    items = list(read_json(prep / "review-log.json", []) or [])
    for f in sorted((prep / "log").glob("*.json")) if (prep / "log").is_dir() else []:
        part = read_json(f, []) or []
        if isinstance(part, list):
            items += part
    seen, out = set(), []
    for x in items:
        k = (x[0], x[1])
        if k not in seen:
            seen.add(k)
            out.append(x)
    return sorted(out, key=lambda x: x[0])
