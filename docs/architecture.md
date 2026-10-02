# Architecture

Polako takes the shape of Offerbook (skills decide, scripts do, one live page, progress apart from
content) and replaces the interview-specific parts with a language-learning core.

## Flow

```
open corpora (GitHub)          person                         agent (skills)
  UniMorph hbs ─┐                profile (wizard)  ─┐            translations, examples,
  subtitles sr ─┼─ sr_lemma ─ base_freq             │            dialogs, notes (drafts)
  subtitles hr ─┘      │                            │                   │
                       └──── text_freq ◄── my/*.txt, situations ◄──────┤
                                   │                                    │
                         words.py candidates ──► prep/round-N.yaml ─────┘
                                                        │
                                        words.py add / forms.py / score_words.py
                                                        │
                                                 prep/words.yaml ──► build_page.py ──► dist/index.html
                                                                                           │
                         stats.py · coverage.py · fsrs_fit.py ◄── review log ◄── page (FSRS, serve.py / artifact db)
```

## Decisions and why

| Decision | Why |
|---|---|
| Curated core lexicon before UniMorph | UniMorph (from Wiktionary) has no biti, imati, znati, moći, ići, ja, moj, ovaj — exactly the top of spoken frequency. With the core lexicon 98% of the running words of the top-1000 forms get a lemma. |
| No neural lemmatizer by default | CLASSLA/Stanza need torch and gigabytes; a dictionary + fallbacks is enough for ranking, and the agent fixes the rare `self`/`stem` lemmas while translating. |
| Ekavian only, variants folded | Belgrade speech. Croatian/ijekavian forms add to their Serbian lemma's count and never become cards. |
| Lemma zipf = max(written, spoken) | wordfreq counts only the infinitive of a verb (hteti ≈ 3.4) and misses everyday words (kirija); subtitles count all forms. |
| Own texts: a flat +1.5 | A word the landlord actually wrote must outrank common words nobody sent; logarithms keep a repeated word from dominating. |
| Every own/situation word goes into the round | The round is "what I need", topped up with spoken frequency. |
| Function words are learned at a0/a1 | Unlike an English learner, a Serbian beginner does not know da, je, sam, li, ga, mi. |
| FSRS instead of Leitner | Per-card difficulty, ~20–30% fewer reviews at the same recall, honest forecasts; same code in JS and Python, tested for identical numbers. |
| Recognition, then recall | Day 1: pick-tr, listen, pick-sr. Recall sides unlock the next day once recognition holds — the day-one load stays sane. |
| Listening is a first-class side | Living in Serbia means understanding speech; voice chain sr → hr → bs, the page says which voice. |
| Typing off by default | The person asked for it; diacritics on a phone are slow. Available in settings. |
| Coverage as the headline | "I understand 62% of ordinary conversation" answers "will I understand?" better than "312 words learned". |
| Log of every answer | All statistics, the personal FSRS fit and the forecasts come from one append-only log. |
| Card ids = slugs with distinct diacritics | kuća → w:kucja, kuca → w:kuca: no collisions; ids never change; `ids.lock.json` catches a lost id. |
| Server merges stale tabs | Two open tabs must not erase each other's progress. |

## Offerbook → Polako

Kept: the hub with buttons, `tools/run` + pinned venv, data written only by scripts, the quick check by
frequency band and batches of 50, the goal rings and streak, TTS with auto-advance, artifact/db or local
server storage, backups and migrations, check_all.

Replaced: Leitner → FSRS; 4 sides → 3 recognition + 2–3 recall sides; English-from-own-stories → three
signals (spoken frequency, situations, own texts); pymorphy/simplemma → Serbian lemmatizer; new tabs
(Situations, My texts, Statistics, Deck); the page split into modules (core, fsrs, tts, trainer, views, stats).
