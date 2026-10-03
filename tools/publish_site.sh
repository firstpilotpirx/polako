#!/usr/bin/env bash
# Builds the public site (tools/site.py) and publishes it to the gh-pages branch of this repository.
# GitHub Pages serves it at https://<owner>.github.io/<repo>/ (Settings → Pages → Branch: gh-pages, / (root)).
#
#   bash tools/publish_site.sh            # build + commit + push gh-pages
#   bash tools/publish_site.sh --no-push  # build + commit only
set -euo pipefail
cd "$(dirname "$0")/.."
PUSH=1; [ "${1:-}" = "--no-push" ] && PUSH=0
OUT=$(mktemp -d)
bash tools/run site.py --out "$OUT"
REMOTE=$(git remote get-url origin)
cd "$OUT"
git init -q -b gh-pages
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-Polako}" -c user.email="${GIT_AUTHOR_EMAIL:-polako@users.noreply.github.com}" commit -qm "Site $(date +%Y-%m-%d\ %H:%M)"
if [ "$PUSH" = 1 ]; then
  git push -q -f "$REMOTE" gh-pages && echo "• gh-pages pushed"
else
  echo "• built in $OUT (not pushed)"
fi
