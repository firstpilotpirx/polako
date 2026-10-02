#!/usr/bin/env bash
# Installs the Polako plugin (polako-serbian) into Claude Code. Run by the agent; the person does nothing.
#
#   bash install.sh
#
# Steps (safe to re-run):
#   1. registers this folder as the `polako` marketplace (or updates it);
#   2. installs polako-serbian@polako for the user;
#   3. prepares the Python environment (tools/run --check) and downloads the corpora (tools/fetch_data.py).
#
# Exit codes: 5 — no `claude` CLI (POLAKO_NEEDS_CLAUDE_CLI) · 3 / 4 — from tools/run (no Python / deps failed).
# A failed corpus download is not fatal: the hub retries it later.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say(){ printf '• %s\n' "$*"; }
command -v claude >/dev/null 2>&1 || { echo "POLAKO_NEEDS_CLAUDE_CLI: claude not found in PATH" >&2; exit 5; }
if claude plugin marketplace list 2>/dev/null | grep -qw "polako"; then
  say "marketplace polako already exists — updating"; claude plugin marketplace update polako >/dev/null
else
  say "adding marketplace polako"; claude plugin marketplace add "$ROOT" >/dev/null
fi
if claude plugin list 2>/dev/null | grep -q "polako-serbian@polako"; then
  say "plugin polako-serbian is already installed"; claude plugin enable polako-serbian@polako >/dev/null 2>&1 || true
else
  say "installing plugin polako-serbian"; claude plugin install polako-serbian@polako >/dev/null
fi
say "preparing the Python environment"
bash "$ROOT/tools/run" --check >/dev/null
say "downloading the corpora (≈ 33 MB, once)"
bash "$ROOT/tools/run" fetch_data.py >/dev/null 2>&1 || say "corpora: no network now — the hub will retry"
say "done: /polako-start appears in a new session or after /reload-plugins"
echo "POLAKO_INSTALLED root=$ROOT"
