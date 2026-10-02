---
name: polako-next
description: Shows the next step of the person's Serbian learning (Polako) with buttons — what matters most now and what else can be done. Use when the person returns to Serbian and says "what's next", "let's continue", "where did we stop", "dalje", or asks what to practise today.
---

# /polako-next — what's next

A short entry into the Polako hub; all the logic is in [../polako-start/SKILL.md](../polako-start/SKILL.md).

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/polako-start/SKILL.md`.
2. Start at hub step 2 (sync with the page), then step 3 — the menu with buttons.
3. The folder comes from `prep/session.yaml` (`~/polako` by default). No folder yet → act as `/polako-start` from step 1.
4. Then the usual loop: action → one-line summary → menu.

No greetings or recaps: one status line and the buttons.
