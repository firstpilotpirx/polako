#!/usr/bin/env python3
"""Plugin self-checks — run by tools/check_all.sh after any change.

    python3 tools/check_rules.py

1. every `run <script>` in skills exists in tools/, and every tools/*.py (except libraries) is mentioned
   in the skills — an undocumented script is a script the agent will never call;
2. relative links in skills resolve;
3. every UI string the page uses (L('key') in templates/portal/*.js) exists in i18n.json (ru);
4. the top CHANGELOG version equals .claude-plugin/plugin.json; the marketplace lists this plugin;
5. data files parse (core lexicon, variants, false friends, situation catalog).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIBS = {"prepio.py", "check_rules.py"}
errors: list[str] = []


def err(msg):
    errors.append(msg)


skills = list((ROOT / "skills").rglob("*.md"))
text = "\n".join(p.read_text(encoding="utf-8") for p in skills)
for name in sorted(set(re.findall(r"\brun ([a-z_]+\.py)", text))):
    if not (ROOT / "tools" / name).exists():
        err(f"skills call a missing script: {name}")
for p in sorted((ROOT / "tools").glob("*.py")):
    if p.name not in LIBS and p.name not in text:
        err(f"tools/{p.name} is not mentioned in any skill")
for p in skills:
    for link in re.findall(r"\]\(([^)#:]+)(?:#[^)]*)?\)", p.read_text(encoding="utf-8")):
        if not (p.parent / link).exists():
            err(f"{p.relative_to(ROOT)}: broken link {link}")

ui = json.loads((ROOT / "templates/portal/i18n.json").read_text(encoding="utf-8"))["ru"]
js = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "templates/portal").glob("*.js"))
for key in sorted(set(re.findall(r"\bL\('([A-Za-z0-9_]+)'\)", js)) | set(re.findall(r"nWord\([^,]+, '([A-Za-z0-9]+)'\)", js))):
    if key not in ui:
        err(f"UI string missing in i18n.json: {key}")
for key in re.findall(r"\['(tab[A-Z][a-z]+)'\]|'(tab[A-Z][a-z]+)'\]", js):
    k = key[0] or key[1]
    if k not in ui:
        err(f"UI string missing in i18n.json: {k}")

plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
log = yaml.safe_load((ROOT / "CHANGELOG.yaml").read_text(encoding="utf-8"))
if not log or str(log[0]["version"]) != plugin["version"]:
    err(f"CHANGELOG top version {log[0]['version'] if log else None} != plugin.json {plugin['version']}")
if plugin["name"] not in [p["name"] for p in market["plugins"]]:
    err("marketplace.json does not list the plugin")
for f in ("core_lexicon.yaml", "variants.yaml", "false_friends.yaml", "situations_catalog.yaml"):
    try:
        d = yaml.safe_load((ROOT / "data" / f).read_text(encoding="utf-8"))
        if f == "core_lexicon.yaml":
            for sec in ("function", "verbs", "nouns", "adjectives"):
                for e in d[sec]:
                    if not isinstance(e.get("l"), str) or not isinstance(e.get("ru", ""), str):
                        err(f"core_lexicon {sec}: bad entry {e}")
    except Exception as e:  # noqa: BLE001
        err(f"data/{f}: {e}")

for pk in (ROOT / "data" / "packs").glob("*.yaml"):
    d = yaml.safe_load(pk.read_text(encoding="utf-8"))
    for w in d.get("words", []):
        if not isinstance(w.get("sr"), str) or not isinstance(w.get("tr"), str):
            err(f"{pk.name}: bad word {w}")
    for s in d.get("situations", []):
        for dl in s.get("dialogs", []):
            for ln in dl["lines"]:
                if not all(isinstance(ln.get(k), str) for k in ("sr", "tr")) or ln.get("who") not in ("me", "they"):
                    err(f"{pk.name}: bad line {ln}")

if errors:
    print("\n".join("✗ " + e for e in errors))
    sys.exit(1)
print(f"rules: ok ({len(skills)} skill files, {len(list((ROOT / 'tools').glob('*.py')))} scripts)")
