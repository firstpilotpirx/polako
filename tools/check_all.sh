#!/usr/bin/env bash
# Every check and build, on a fresh copy of examples/sample. Run after any change.
#   bash tools/check_all.sh
# Needs the corpora (tools/fetch_data.py); without them only the offline checks run.
# The page test runs when Node and the jsdom package are available (NODE_PATH or a global install).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
if python3 -c "import yaml, jsonschema, wordfreq" 2>/dev/null; then PY=python3; else
  PY="$(bash tools/run --check | tail -1 | sed 's/^ok: //')/bin/python"
fi
step(){ printf '\n── %s\n' "$1"; }
step "plugin rules";  "$PY" tools/check_rules.py
step "fsrs: page = python"; "$PY" tests/test_fsrs.py
step "serbian";       "$PY" tests/test_serbian.py
step "page on an empty folder"; mkdir -p "$OUT/empty" && "$PY" tools/build_page.py --dir "$OUT/empty" --out "$OUT/empty.html"
if ! "$PY" tools/fetch_data.py --status | grep -q '"ok": true'; then "$PY" tools/fetch_data.py || true; fi
if ! "$PY" -c "import sys; sys.path.insert(0,'tools'); from prepio import data_dir; sys.exit(0 if (data_dir()/'subs-sr-50k.txt').exists() else 1)"; then
  printf '\n(no corpora: skipped the data pipeline)\n'; exit 0
fi
S="$OUT/sample"; mkdir -p "$S/prep"
cp -r examples/sample/my "$S/my"; cp examples/sample/prep/profile.yaml "$S/prep/"
D=examples/sample/drafts
step "spoken frequency";  "$PY" tools/base_freq.py | tail -3
step "situations";        "$PY" tools/situations.py --dir "$S" add "$D/situations.yaml"
step "own texts";         "$PY" tools/text_freq.py --dir "$S" | sed -n '1,1p'
step "candidates";        "$PY" tools/words.py --dir "$S" candidates --n 130 | sed -n '1,1p'
step "cards";             "$PY" tools/words.py --dir "$S" add "$D/round-1.yaml" \
                       && "$PY" tools/words.py --dir "$S" add "$D/manual.yaml" --round 1 \
                       && "$PY" tools/words.py --dir "$S" add "$D/phrases.yaml" --kind phrases \
                       && "$PY" tools/words.py --dir "$S" add "$D/cloze.yaml" --kind cloze
"$PY" - "$S" <<'PY'
import sys, yaml
a = yaml.safe_load(open(sys.argv[1] + "/prep/words.yaml")); b = yaml.safe_load(open("examples/sample/prep/words.yaml"))
assert [w["id"] for w in a["words"]] == [w["id"] for w in b["words"]], "the rebuilt deck differs from examples/sample"
print("deck identical to the sample:", len(a["words"]), "words")
PY
step "phrases draft";     "$PY" tools/phrases.py --dir "$S" | sed -n '1,1p'
step "validate";          "$PY" tools/validate.py --dir "$S" --update-lock
step "coverage";          "$PY" tools/coverage.py --dir "$S" --deck | sed -n '1,2p'
step "a new text";        "$PY" tools/unknown_in.py --dir "$S" --text "Poštovani, sutra od 10 časova nema vode." --draft
step "state";             "$PY" tools/state.py --dir "$S" --no-build wizard finish && "$PY" tools/state.py --dir "$S" page counts
step "stats";             "$PY" tools/stats.py --dir "$S" | sed -n '1,2p'
step "versions";          "$PY" tools/migrate.py --dir "$S" --init && "$PY" tools/migrate.py --dir "$S" && "$PY" tools/backup.py --dir "$S" list | sed -n '1,1p'
step "hub menu";          "$PY" tools/next_steps.py --dir "$S"
step "pack";              mkdir -p "$OUT/pack" && "$PY" tools/pack.py --dir "$OUT/pack" install belgrade-basics | tail -1 \
                       && "$PY" tools/next_steps.py --dir "$OUT/pack" | sed -n '1,2p'
step "page";              "$PY" tools/build_page.py --dir "$S"
step "public site";       "$PY" tools/site.py --out "$OUT/site" && grep -q __polakoStart "$OUT/site/index.html" && test -s "$OUT/site/packs/belgrade-basics.json"
if command -v node >/dev/null && node -e "require('jsdom')" 2>/dev/null; then
  step "page in jsdom";   node tests/page_smoke.js "$S/dist/index.html"
else printf '\n(jsdom not installed: skipped the page test — npm i -g jsdom)\n'; fi
step "local server";      URL=$("$PY" tools/serve.py --dir "$S" --port 8899 | grep -o 'http://[^ ]*' | tail -1); echo "$URL"; POLAKO_TEST_URL="$URL" "$PY" - <<'PY'
import json, os, urllib.request
BASE = os.environ["POLAKO_TEST_URL"].rstrip("/").replace("localhost", "127.0.0.1")
r = lambda p, d=None: json.loads(urllib.request.urlopen(urllib.request.Request(BASE + p, data=json.dumps(d).encode() if d else None, headers={"Content-Type": "application/json"})).read())
import time
for _ in range(50):   # the server may need a moment to start listening
    try:
        r("/api/ping"); break
    except OSError:
        time.sleep(0.1)
assert r("/api/ping")["ok"]
r("/api/log", {"items": [[1, "w:a|pick-tr", 3, 1000, 0, 0]]}); assert r("/api/log", {"items": [[1, "w:a|pick-tr", 3, 1000, 0, 0]]})["added"] == 0
r("/api/trainer", {"cards": {"a|x": {"s": 3, "last": 2}, "b|x": {"s": 1, "last": 1}}})
r("/api/trainer", {"cards": {"a|x": {"s": 5, "last": 3}}})          # a stale tab: must not drop b|x
assert set(r("/api/trainer")["cards"]) == {"a|x", "b|x"} and r("/api/trainer")["cards"]["a|x"]["s"] == 5
print("server: log dedup and stale-tab merge ok")
PY
"$PY" tools/serve.py --dir "$S" --stop >/dev/null
"$PY" tools/serve.py --dir "$S" --stop >/dev/null
printf '\nAll checks passed. Work folder: %s\n' "$OUT"
