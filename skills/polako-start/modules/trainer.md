<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: how the trainer works (to explain it), hard words (leeches), settings. The trainer itself is the page. -->

# module `trainer` — practising

The trainer is the page (tab «Тренажёр»); the agent does not quiz in the chat unless asked. Mechanics:
[../references/trainer-format.md](../references/trainer-format.md). In short, to explain when asked:

- One big button «Учить по важности»: reviews that are due first, then new words from the top of the
  list, up to the daily goal. Decks of 50 by importance, phrases, cases and aspect, dialogs.
- A new word: recognise first (choose the meaning, hear it and choose, choose the Serbian word); from the
  next day also recall (say the meaning, say it in Serbian). Choices grade themselves (fast and right →
  "remember", slow → "hard", wrong → "forgot"); recall is graded with four buttons that show the next interval.
- Intervals are computed by FSRS for each side separately; "target recall" 90% by default (85% fewer
  reviews, 95% before an important appointment).
- Modes: «Только на слух» for the road, «Только вспоминать» for speaking practice; a situation's
  «Тренировать» before going there.
- Voice: the browser's own voices — Serbian if present, otherwise Croatian or Bosnian (the page says
  which). No voice → no listening cards.

## Hard words (menu "Разобрать трудные слова", or the person asks)

A side forgotten 6+ times is a leech: it leaves the rounds (the Statistics tab lists them). The page
sends their ids to the inbox; the agent:

1. reads them: `run stats.py --dir <folder> --json` (`leeches`) and the inbox record (type `hard`);
2. for each — why it does not stick (similar to another word, a false friend, abstract), and a fix: a
   vivid association in the person's language, a personal example sentence (from their texts or
   situations), splitting a multi-meaning card;
3. writes the fix as a better `note` and an extra example: retire the old card and add the improved one
   (`words.py retire <id>`, then `words.py add`), or for a simple improvement add a cloze/phrase card
   that uses the word in context;
4. rebuilds; the new card starts fresh, without the leech's history.

Mark the inbox record as done by running `run unknown_in.py --dir <folder> --inbox` only for texts; for
`hard` records the analysis above is enough (they are informational).
