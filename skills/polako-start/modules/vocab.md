<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: rounds of words — candidates from frequency + own texts + situations, translation and examples, cards, the "I know" check; grammar cards (cases, aspect). -->

# module `vocab` — building the person's deck

Goal: **every word this person needs, none they already know.** Learning thousands of words is
pointless: the tail of the frequency list pays less and less. Rounds go deeper until the person stops
knowing most of a round — that is their boundary, and from there they learn.

## Step 1. Candidates — one command

```bash
run text_freq.py --dir <folder>                  # own texts and situations are fresh
run words.py --dir <folder> candidates           # → prep/round-<N>.yaml; --n overrides the size (a0 300, a1 400, a2+ 500)
```

The draft already holds, per word: `sr` (dictionary form), `tr` from the core lexicon (Russian),
`pos`, `gender`, key `forms`, `accent`, aspect partner `pair_sr`, a false-friend `note`, `src`,
situations `sit`, own texts `my`, and examples — from own texts (`about: my`, translation empty), from
situation dialogs (`about: sit`, translated), from Tatoeba (`about: general`).
Every word of the person's texts and situations is in it; the rest of the round is the top of spoken frequency.

## Step 2. The agent checks and completes the draft (edit the DRAFT file, never prep/words.yaml)

1. **Delete** what must not be learned: names and brands from subtitles (Džek, Majkl, Kolakola),
   interjections without meaning (oh, uh), abbreviations, numerals written as digits.
2. **Fix entries marked `flags: [self]` or `[stem]`**: put the dictionary form in `sr` (privremenog →
   privremeni, radova → rad), drop `lemma` if you changed `sr`.
3. **Translate** every empty `tr` into the explanation language — the meaning the person will meet, 1–3
   variants, most common first: `zakazati: записаться, назначить (термин)`. For verbs add the aspect in
   the note when it matters: kupiti — купить (один раз), kupovati — покупать (вообще, регулярно).
4. **Translate** every example with an empty `tr`. Keep at most 3 examples; if a word has none, add one
   short everyday sentence (`about: general`), ekavian, Latin.
5. **Notes** (`note`) — only what prevents a mistake: false friends for Russian speakers (pozorište ≠
   позорище; kruška ≠ кружка), government (čekati koga/šta, sećati se čega), unexpected gender
   (stvar — ž.), the reflexive `se` (smejati se, nadati se).
6. Do not invent accents, gender or forms — the scripts fill them from dictionaries.

## Step 3. Cards

```bash
run words.py --dir <folder> add prep/round-<N>.yaml       # ids, rank, groups of 50, forms from the lexicons, re-ranking
run validate.py --dir <folder> --update-lock
run build_page.py --dir <folder>
```

`add` refuses entries without a translation and drops examples without one (it says which).
Ids are slugs of the Serbian word (`w:kucja` for kuća) and never change: progress is tied to them.

## Step 4. "What I already know" — on the page

Tell the person: "Open «Словарь»: first a quick check of 10 words per frequency band, then batches of 50.
Unmarked words go into the trainer." Then:

```bash
run words.py --dir <folder> round
```

| Known in the round | Next |
|---|---|
| ≥ 80% | next round — `candidates` again (it goes further down the list, never repeats a word) |
| 50–80% | one more, smaller round: `candidates --n 200` |
| < 50% | the boundary is found — no more rounds; learn (trainer) and add words from texts and situations |

## Grammar cards (menu "Падежи и вид глагола")

Serbian understanding is half about forms. Make cards from words already in the deck:

- **cloze** — a short real sentence with one form in braces and what to put: case of a noun after a
  preposition (`Idem u {prodavnicu}.` acc / `u {prodavnici}` loc), genitive after nema / koliko /
  numbers, past forms. Draft: `- {sr: "Nemam {vremena}.", tr: "У меня нет времени.", word: vreme, case: gen, hint: "vreme — чего нет?"}`.
  The page offers the word's other forms as options; give `opts` only when the forms are not in the card.
- **aspect** — for verb pairs both in the deck the page makes "name both aspects" cards itself (from
  `pair`). Add cloze cards with `case: aspect` that contrast them: one finished act vs. a habit/process.

```bash
run words.py --dir <folder> add draft-cloze.yaml --kind cloze
```

Priorities: accusative vs locative after u/na (kuda/gde), genitive after quantities and negation, the
instrumental with sa, then dative with pronouns (meni, tebi). 1 cloze card per ~15 words is enough.

## Updating the deck

Never delete or rename cards — progress is tied to ids.
- A wrong translation, a better note or example: `run words.py --dir <folder> set <id> tr="…" note="…"`
  (`'ex=[{"sr": "…", "tr": "…", "about": "general"}]'` replaces the examples).
- A card that should not be learned any more: `run words.py --dir <folder> retire <id>` — it stops being
  offered, its history stays.
