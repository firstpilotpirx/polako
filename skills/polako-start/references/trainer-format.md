# Trainer format

Implemented in `templates/portal/` (`trainer.js`, `trainer_ui.js`, `fsrs.js`, `tts.js`); the deck
comes from `prep/words.yaml` through `tools/build_page.py`. Do not hand-write a trainer page.

## Items and sides

| Item | Sides (each its own FSRS card, key `<id>|<side>`) |
|---|---|
| word | stage 1: `pick-tr` (sr → meaning of 6) · `listen` (hear → meaning of 6; needs a sr/hr/bs voice) · `pick-sr` (meaning → sr of 6)<br>stage 2, from the next day once stage 1 is answered (each stage-1 side stable ≥ 1 day): `say-tr` · `say-sr` · `type` (only if typing is on) |
| phrase | `listen-ph` (or `read-ph` without a voice) → `say-ph` (+ `type-ph`) |
| cloze | `cloze` — choose the form among the word's other forms (or `opts`) |
| pair | `aspect` — "купить / покупать" → name both aspects; built from `pair` |
| dialog | `reply` — the other person's line (spoken) → choose your answer among 4 |

Distractors: same part of speech, near in rank; translations are deduplicated.

## Scheduling — FSRS-5

```
R(t, S) = (1 + 19/81 · t/S)^-0.5          retrievability after t days at stability S
interval(S) = S · 81/19 · (r^-2 − 1)      = S at r = 0.9
first answer:   S = w[g−1], D = w4 − e^(w5·(g−1)) + 1
success:        S' = S·(1 + e^w8 · (11 − D) · S^−w9 · (e^(w10·(1−R)) − 1) · hard/easy factor)
lapse:          S' = min(S, w11 · D^−w12 · ((S+1)^w13 − 1) · e^(w14·(1−R)))
same day:       S' = S · e^(w17·(g − 3 + w18))
```

The same formulas in Python: `tools/fsrs.py` (`run fsrs.py 3 3 1 3 --gap 3 8 1` shows a card's
life; `tests/test_fsrs.py` checks both give identical numbers). Default FSRS-5 weights; `tools/fsrs_fit.py` may write personal w0–w3 to `prep/fsrs-params.json`.
Grades: 1 Again (back to the end of the round, due in 10 minutes), 2 Hard, 3 Good, 4 Easy.
Choice sides grade themselves: right within 6 s (phrases 10 s) → Good, right but slower → Hard, wrong →
Again. Typing: exact → Good, only diacritics or one letter off → Hard. Recall sides: four buttons, each
showing its next interval. Target recall `retention` 0.85 / 0.9 / 0.95 (settings).

State per side: `{s, d, due, last, reps, lapses, f (first shown), g (last grade)}`.
Item status: min S over its sides — learned ≥ 21 days, firm ≥ 7, learning, not started.
A side with 6+ lapses makes the item a **leech**: out of the rounds, listed on Statistics.

## Rounds

- «Учить по важности»: due items by rank, then new: words up to `goal − new today`, phrases up to
  max(3, goal/4), cloze/pairs only for words already started, ≤ 5 other new items; size 10/20/30/50 sides.
  Goal met and nothing due → an explicit "extra round" without the cap.
- Decks: words by 50 (by rank, known words removed), phrases, cases & aspect, dialogs; a situation's
  «Тренировать»; «Только на слух», «Только вспоминать».
- Sides of one item never come twice in a row; recognition before recall.

## Coverage

A word is *understood* when marked known or its recognition side (say-tr, pick-tr or listen) has S ≥ 7
days. Spoken coverage = Σ subtitle-token share of understood lemmas; own texts = their token share.
A snapshot per day goes to `T.hist` for the coverage-over-time chart.

## Voice

Web Speech API. Serbian voice chain: `sr` → `hr` → `bs` (the page names the voice; a Croatian voice
reads Serbian Latin well, accents may differ); explanation language with its own voice. Auto-play of
the question and the answer, ✓/✗ sounds, auto-advance with two pauses, speed 0.7–1.15× (0.85 default).

## Storage

| Mode | Cards | Log | "I know" |
|---|---|---|---|
| local server | `prep/trainer-state.json` | `prep/review-log.json` (append) | `prep/vocab-state.json` |
| artifact db | doc `trainer/state` | collection `log`, one doc per day `{day, items}` | collection `vocab` |
| neither | localStorage `pl.fallback` (the page says so) | | |

Log entry: `[ts, key, grade, ms, elapsed days, stability before]`. The server merges a stale tab's
state with the newer one instead of overwriting (except an explicit reset).
