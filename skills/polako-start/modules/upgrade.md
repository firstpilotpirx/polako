<!-- Polako hub module. Called from skills/polako-start/SKILL.md and /polako-update; the person does not run it. -->
<!-- Purpose: move the learner's folder to a new plugin version without losing anything. -->

# module `upgrade` — a new version

1. `run migrate.py --dir <folder> --check` → versions. Nothing new → say so, back to the menu.
2. What's new: read the entries of `${CLAUDE_PLUGIN_ROOT}/CHANGELOG.yaml` newer than `plugin_folder`,
   tell the person 2–4 lines in their language.
3. Sync with the page first (hub step 2) — the files must hold the latest progress.
4. `run migrate.py --dir <folder>` — it makes a backup (`prep/backups/…`), applies the format steps,
   validates and compares progress counts; on any mismatch it rolls back by itself (`ROLLBACK …`).
5. Run the `actions` of the new CHANGELOG entries (rebuild, new cards for a new feature, …).
6. `run build_page.py --dir <folder>`; artifact mode — republish to the same artifact and, if the
   CHANGELOG says the db format changed, write back `run state.py page export` with ArtifactData.

"Put it back as it was" → `run backup.py --dir <folder> list` → buttons with the latest backups →
`run backup.py --dir <folder> restore <name>` → rebuild.
