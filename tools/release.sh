#!/usr/bin/env bash
# Release script: bump version -> checks -> build zip -> git commit + tag -> push.
#
#   bash tools/release.sh patch|minor|major|X.Y.Z [--no-push]
#   bash tools/release.sh github     # (re)publish the GitHub release for the current version
#
# CHANGELOG.yaml: if there is no entry for the new version, the script writes one from the
# commit subjects since the previous tag. Write it yourself first if you want better notes.
# Output: dist/polako-serbian.zip (upload it in Customize -> Plugins).
set -euo pipefail
cd "$(dirname "$0")/.."

# GitHub release: title "Polako X.Y.Z", notes from CHANGELOG.yaml (en), zip attached. Needs the gh CLI.
gh_release(){
  local V="$1" NOTES
  NOTES=$(python3 - "$V" <<'PY'
import re,sys
v=sys.argv[1]; t=open("CHANGELOG.yaml",encoding="utf8").read()
m=re.search(r'^- version: "'+re.escape(v)+r'"\n(.*?)(?=^- version:|\Z)', t, re.S|re.M)
body=m.group(1) if m else ""
en=re.search(r'^    en:\n((?:      - .*\n?)+)', body, re.M)
lines=[re.sub(r'^      - "?(.*?)"?$', r'- \1', l) for l in (en.group(1).splitlines() if en else [])]
print("\n".join(lines) or "Polako "+v)
print("\nInstall: `claude plugin marketplace add firstpilotpirx/polako-serbian` then `claude plugin install polako-serbian@polako`, or upload the attached zip in Claude: Customize -> Plugins.")
PY
)
  if ! command -v gh >/dev/null; then
    echo "• gh CLI not found — install it (brew install gh && gh auth login), then: bash tools/release.sh github"; return 0
  fi
  if gh release view "v$V" >/dev/null 2>&1; then
    gh release upload "v$V" dist/polako-serbian.zip --clobber && gh release edit "v$V" --notes "$NOTES" >/dev/null
  else
    gh release create "v$V" dist/polako-serbian.zip --title "Polako $V" --notes "$NOTES"
  fi && echo "• GitHub release v$V published"
}

if [ "${1:-}" = "github" ]; then
  V=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")
  [ -f dist/polako-serbian.zip ] || zip -qr dist/polako-serbian.zip . -x ".git/*" "dist/*" "_to_delete/*" "*/__pycache__/*" ".DS_Store"
  gh_release "$V"; exit 0
fi
BUMP="${1:-}"; PUSH=1
[ "${2:-}" = "--no-push" ] && PUSH=0
[ -n "$BUMP" ] || { echo "usage: bash tools/release.sh patch|minor|major|X.Y.Z [--no-push]"; exit 1; }

CUR=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")
NEW=$(python3 - "$CUR" "$BUMP" <<'PY'
import sys
cur,b=sys.argv[1],sys.argv[2]
p=[int(x) for x in cur.split(".")]
if b=="patch": p[2]+=1
elif b=="minor": p[1]+=1; p[2]=0
elif b=="major": p[0]+=1; p[1]=p[2]=0
else:
    p=[int(x) for x in b.split(".")]
print(".".join(map(str,p)))
PY
)
echo "• version: $CUR -> $NEW"

TOP=$(grep -m1 -E '^- version:' CHANGELOG.yaml | sed -E 's/.*"([^"]+)".*/\1/')
# an entry for a newer, unreleased version is already on top: release exactly that one, never write a second entry below it
NEWER=$(python3 -c "import sys;v=lambda s:tuple(int(x) for x in s.split('.'));print(int(v(sys.argv[1])>v(sys.argv[2])))" "$TOP" "$CUR")
if [ "$NEWER" = 1 ] && [ "$TOP" != "$NEW" ]; then
  echo "✗ CHANGELOG.yaml already describes $TOP (not released yet). Release that one: bash tools/release.sh $TOP"; exit 1
fi
if [ "$TOP" != "$NEW" ]; then
  # no entry yet: write one from the commit subjects since the previous tag (edit it later if you like)
  python3 - "$CUR" "$NEW" <<'PY'
import re,subprocess,sys,datetime
cur,new=sys.argv[1:3]
def git(*a):
    try: return subprocess.run(["git",*a],capture_output=True,text=True).stdout
    except Exception: return ""
rng=f"v{cur}..HEAD" if git("tag","-l",f"v{cur}").strip() else "HEAD~20..HEAD"
subs=[s.strip() for s in git("log","--format=%s",rng).splitlines()]
subs=[s for s in subs if s and not s.startswith("Polako ")]
if git("status","--porcelain").strip(): subs.append("Small fixes and improvements")
subs=list(dict.fromkeys(subs))[:4] or ["Small fixes and improvements"]
t=open("CHANGELOG.yaml",encoding="utf8").read()
dv=re.search(r'^  data_version: (\d+)',t,re.M).group(1)
q=lambda s:'"'+s.replace('"',"'")+'"'
lines="\n".join("      - "+q(s) for s in subs)
entry=(f'- version: "{new}"\n  date: {datetime.date.today()}\n  data_version: {dv}\n'
       f'  notes:\n    ru:\n{lines}\n    en:\n{lines}\n  actions: []\n\n')
i=t.index("- version:")
open("CHANGELOG.yaml","w",encoding="utf8").write(t[:i]+entry+t[i:])
print("• CHANGELOG.yaml: added an entry for "+new+":"); print(lines)
PY
fi

setver(){ python3 - "$1" "$2" <<'PY'
import re,sys
cur,new=sys.argv[1:3]
for p in (".claude-plugin/plugin.json",".claude-plugin/marketplace.json"):
    try: t=open(p,encoding="utf8").read()
    except FileNotFoundError: continue
    t=re.sub(r'("version":\s*")'+re.escape(cur)+'"', r'\g<1>'+new+'"', t)
    open(p,"w",encoding="utf8").write(t)
PY
}
setver "$CUR" "$NEW"
# if anything below fails, put the old version back so the next run starts clean
trap 'echo "• rolled the version back to $CUR"; setver "$NEW" "$CUR"' ERR

echo "• checks…"
bash tools/check_all.sh >/tmp/polako-check.log 2>&1 || { tail -20 /tmp/polako-check.log; echo "✗ checks failed (full log: /tmp/polako-check.log)"; setver "$NEW" "$CUR"; echo "• rolled the version back to $CUR"; exit 1; }

echo "• building zip…"
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
mkdir -p dist; rm -f dist/polako-serbian.zip
git ls-files -co --exclude-standard | zip -q dist/polako-serbian.zip -@   # working tree minus .gitignore: no build output or caches
echo "  dist/polako-serbian.zip ($(du -h dist/polako-serbian.zip | cut -f1))"

trap - ERR
if [ -d .git ]; then
  git add -A
  git commit -m "Polako $NEW" >/dev/null && echo "• committed"
  git tag -f "v$NEW" >/dev/null && echo "• tag v$NEW"
  if [ "$PUSH" = 1 ]; then
    git push origin HEAD && git push -f origin "v$NEW" && echo "• pushed" && gh_release "$NEW"
  else
    echo "• push skipped (--no-push): git push origin HEAD && git push origin v$NEW"
  fi
else
  echo "• no .git here — commit and push from your terminal"
fi
echo "Done: Polako $NEW. Upload dist/polako-serbian.zip in Customize -> Plugins, or update the plugin from GitHub."
