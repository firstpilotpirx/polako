---
name: polako-update
description: Updates the person's Polako (Serbian trainer) folder to a new plugin version — what's new, a backup, data migration without losing progress, rebuilding the page; also rolls back. Use when the person says "update Polako", "обнови", "what's new", "the plugin was updated", "верни как было", or the hub offered an update.
---

# /polako-update — updating without losing progress

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/polako-start/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/skills/polako-start/modules/upgrade.md`.
2. The folder comes from `prep/session.yaml`. Nothing there → nothing to update: offer `/polako-start`.
3. Run the `upgrade` module, then the hub menu.
