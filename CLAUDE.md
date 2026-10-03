# Polako plugin (polako-serbian) — instructions for the agent

A Claude plugin that builds a personal Serbian vocabulary and trains it. The person should not have to
do anything by hand: you install and run everything.

## If the person asks to install or try the plugin

1. Run `bash install.sh` in this folder: it adds the `polako` marketplace, installs
   `polako-serbian@polako`, prepares the Python environment and downloads the corpora.
2. By exit code: `0` + `POLAKO_INSTALLED root=…` — done; `5` — no `claude` CLI (offer to install it,
   https://code.claude.com/docs/en/setup); `3` — no Python (offer uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`);
   `4` — dependencies failed (show the tail, offer a retry).
3. Do not ask for a restart: read `skills/polako-start/SKILL.md` and start the hub, with the root from
   `POLAKO_INSTALLED root=…` for `${CLAUDE_PLUGIN_ROOT}`.

## If the person is editing the plugin itself

- After changes: `bash tools/check_all.sh` (rules, FSRS parity JS = Python, Serbian tests, the whole
  pipeline on a copy of `examples/sample`, the page in jsdom, the local server).
- A new data operation = a new script subcommand + a row in the "data is written only by scripts" table
  in `skills/polako-start/SKILL.md`. Never "write it into the YAML".
- Page strings go to `templates/portal/i18n.json`; the look lives only in `templates/portal/`.
- Linguistic data: `data/core_lexicon.yaml` (ekavian, Latin; YAML booleans: quote `on`, `no`, `yes`),
  `data/variants.yaml`, `data/false_friends.yaml`. After editing the lexicon the lemma index rebuilds
  itself; if a change moves ranks, regenerate the sample deck (check_all compares it).
- FSRS changes go to both `templates/portal/fsrs.js` and `tools/fsrs.py`; `tests/test_fsrs.py` must pass.
- Every release: a CHANGELOG.yaml entry with the version of `.claude-plugin/plugin.json`; a data format
  change bumps `DATA_VERSION` and adds a step in `tools/migrate.py`. Card ids never change.
- `claude plugin validate .` checks the manifests; `bash tools/release.sh patch` makes the zip.
- The public site (https://firstpilotpirx.github.io/polako/) is built from `templates/` by `tools/site.py`;
  after a change in `templates/` or `data/packs/` publish it with `bash tools/publish_site.sh` (branch gh-pages).
  Personal data never goes into this repository: it lives in each person's private data repository.
